#!/usr/bin/env bash
# deploy-app.sh -- Build and deploy the ACB Large Print web application
#
# Run as deploy user:  bash ~/app/scripts/deploy-app.sh
#
# This script:
#   - Validates that required files exist
#   - Optionally pulls latest code from Git (if .git directory exists)
#   - Creates a pre-deploy feedback DB backup (optional)
#   - Enables maintenance mode (users see "Under Maintenance" page)
#   - Builds and starts Docker containers
#   - Waits for health check with per-attempt container diagnostics
#   - Probes /health JSON and prints full readiness breakdown on pass AND fail
#   - Disables maintenance mode on success (site goes live)
#   - Rolls back to the previous Git revision on failed health check (when available)
#   - Dumps tail logs from every service on health check failure
#   - Shows status and URLs to test
#   - Writes full deploy log to ~/deploy-logs/deploy-YYYYMMDD-HHMMSS.log
set -euo pipefail

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------
LOG_DIR="${LOG_DIR:-$HOME/deploy-logs}"
DEPLOY_TS="$(date -u +%Y%m%d-%H%M%S)"
LOG_FILE="${LOG_DIR}/deploy-${DEPLOY_TS}.log"
LATEST_LOG_FILE="${LOG_DIR}/deploy-latest.log"

mkdir -p "$LOG_DIR"
# Tee all stdout+stderr to the log file for the entire script run
exec > >(tee -a "$LOG_FILE") 2>&1

# Emit timestamped lines so every event is traceable in the log
log_ts() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"
}

finalize_log() {
    cp "$LOG_FILE" "$LATEST_LOG_FILE" 2>/dev/null || true
    log_ts "Full deploy log: $LOG_FILE"
    log_ts "Latest log link: $LATEST_LOG_FILE"
}
trap finalize_log EXIT

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
APP_ROOT="${APP_ROOT:-$HOME/app}"
WEB_ROOT="${WEB_ROOT:-$APP_ROOT/web}"
COMPOSE_FILE="docker-compose.prod.yml"
APP_DOMAIN="${APP_DOMAIN:-letitglow.app}"
APP_ALIAS_DOMAIN="${APP_ALIAS_DOMAIN:-}"
MAIN_DOMAIN="${MAIN_DOMAIN:-csedesigns.com}"
ENABLE_PREDEPLOY_BACKUP="${ENABLE_PREDEPLOY_BACKUP:-1}"
HEALTH_MAX_ATTEMPTS="${HEALTH_MAX_ATTEMPTS:-40}"
HEALTH_SLEEP="${HEALTH_SLEEP:-3}"
COMPOSE_REMOVE_ORPHANS="${COMPOSE_REMOVE_ORPHANS:-1}"
CLEANUP_ON_SUCCESS="${CLEANUP_ON_SUCCESS:-1}"
CLEANUP_ON_ROLLBACK="${CLEANUP_ON_ROLLBACK:-0}"
CLEANUP_IMAGE_PRUNE="${CLEANUP_IMAGE_PRUNE:-1}"
CLEANUP_BUILDER_PRUNE="${CLEANUP_BUILDER_PRUNE:-0}"
CLEANUP_BUILDER_KEEP_STORAGE="${CLEANUP_BUILDER_KEEP_STORAGE:-4GB}"
DEPLOY_STATUS_FILE="${DEPLOY_STATUS_FILE:-$APP_ROOT/instance/deploy-status.json}"
WCAG22AA_GATE="${WCAG22AA_GATE:-not-reported}"
WCAG22AAA_GATE="${WCAG22AAA_GATE:-not-configured}"
GGG_SYNC_ENABLED="${GGG_SYNC_ENABLED:-1}"
GGG_SYNC_SOURCE="${GGG_SYNC_SOURCE:-$HOME/ggg}"
GGG_SYNC_DEST="${GGG_SYNC_DEST:-$APP_ROOT/ggg}"
GGG_REGENERATE_FEED="${GGG_REGENERATE_FEED:-1}"


PRE_DEPLOY_COMMIT=""
ROLLED_BACK=0
MAINTENANCE_ENABLED=0

set_deploy_status() {
    local phase="$1"
    local state="$2"
    local detail="${3:-}"
    local container_status_file="/app/instance/deploy-status.json"
    mkdir -p "$(dirname "$DEPLOY_STATUS_FILE")"
    python3 - "$DEPLOY_STATUS_FILE" "$phase" "$state" "$detail" "$WCAG22AA_GATE" "$WCAG22AAA_GATE" <<'PYEOF' || true
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
phase = sys.argv[2]
state = sys.argv[3]
detail = sys.argv[4]
aa_default = sys.argv[5]
aaa_default = sys.argv[6]

payload = {}
if path.exists():
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        payload = {}

gates = payload.get("gates") if isinstance(payload.get("gates"), dict) else {}
payload.update({
    "phase": phase,
    "state": state,
    "detail": detail,
    "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    "gates": {
        "wcag22aa": str(gates.get("wcag22aa", aa_default)),
        "wcag22aaa": str(gates.get("wcag22aaa", aaa_default)),
    },
})
path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PYEOF

    # Keep the runtime status file in sync with what the web app actually reads
    # from inside the container (/app/instance/deploy-status.json).
    if [[ -f "$WEB_ROOT/$COMPOSE_FILE" ]]; then
        local web_cid
        web_cid="$(docker compose -f "$WEB_ROOT/$COMPOSE_FILE" ps -q web 2>/dev/null | head -n1)"
        if [[ -n "$web_cid" ]]; then
            docker compose -f "$WEB_ROOT/$COMPOSE_FILE" exec -T web python3 - "$container_status_file" "$phase" "$state" "$detail" "$WCAG22AA_GATE" "$WCAG22AAA_GATE" <<'PYEOF' || true
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
phase = sys.argv[2]
state = sys.argv[3]
detail = sys.argv[4]
aa_default = sys.argv[5]
aaa_default = sys.argv[6]

payload = {}
if path.exists():
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        payload = {}

gates = payload.get("gates") if isinstance(payload.get("gates"), dict) else {}
payload.update({
    "phase": phase,
    "state": state,
    "detail": detail,
    "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    "gates": {
        "wcag22aa": str(gates.get("wcag22aa", aa_default)),
        "wcag22aaa": str(gates.get("wcag22aaa", aaa_default)),
    },
})
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PYEOF
        fi
    fi
}

# ---------------------------------------------------------------------------
# Helper: container state + health one-liner
# ---------------------------------------------------------------------------
container_state() {
    local service="$1"
    local cid
    cid="$(docker compose -f "$COMPOSE_FILE" ps -q "$service" 2>/dev/null | head -n1)"
    if [[ -z "$cid" ]]; then
        echo "state=<no container>"
        return
    fi
    local state health last_log
    state="$(docker inspect --format '{{.State.Status}}' "$cid" 2>/dev/null || echo unknown)"
    health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$cid" 2>/dev/null || echo unknown)"
    last_log="$(docker logs --tail 1 "$cid" 2>&1 | tr '\n' ' ' | cut -c1-120)"
    echo "state=${state} health=${health} last_log=\"${last_log}\""
}

# ---------------------------------------------------------------------------
# Helper: dump service log tail on failure
# ---------------------------------------------------------------------------
dump_service_logs() {
    local service="$1"
    local lines="${2:-40}"
    log_ts "--- Log tail: $service (last $lines lines) ---"
    docker compose -f "$COMPOSE_FILE" logs --tail "$lines" "$service" 2>&1 || true
}

# ---------------------------------------------------------------------------
# Helper: optional cleanup of stale Docker artifacts
# ---------------------------------------------------------------------------
run_optional_cleanup() {
    local phase="${1:-deploy}"

    log_ts "--- Cleanup phase ($phase): begin ---"

    if [[ "$CLEANUP_IMAGE_PRUNE" == "1" ]]; then
        log_ts "    Pruning dangling/unused images (docker image prune -f)"
        docker image prune -f || true
    else
        log_ts "    Skipping image prune (CLEANUP_IMAGE_PRUNE=$CLEANUP_IMAGE_PRUNE)"
    fi

    if [[ "$CLEANUP_BUILDER_PRUNE" == "1" ]]; then
        log_ts "    Pruning builder cache with keep-storage=$CLEANUP_BUILDER_KEEP_STORAGE"
        docker builder prune -f --keep-storage "$CLEANUP_BUILDER_KEEP_STORAGE" || true
    else
        log_ts "    Skipping builder prune (CLEANUP_BUILDER_PRUNE=$CLEANUP_BUILDER_PRUNE)"
    fi

    log_ts "--- Cleanup phase ($phase): complete ---"
}

# ---------------------------------------------------------------------------
# Helper: probe /health inside the web container and print full JSON
# ---------------------------------------------------------------------------
probe_health_json() {
    local label="${1:-health}"
    log_ts "--- $label: probing /health JSON ---"
    docker compose -f "$COMPOSE_FILE" exec -T web python -c "
import urllib.request, json, sys
try:
    with urllib.request.urlopen('http://localhost:8000/health', timeout=5) as r:
        body = r.read().decode()
        payload = json.loads(body)
        print(json.dumps(payload, indent=2))
        services_ok = all(v.get('status') == 'ok' for v in payload.get('services', {}).values())
        # budget uses 'ok'/'exhausted'; chat/vision/whisperer use 'ready'/'not-ready'/'not-configured'
        readiness = payload.get('readiness', {})
        features_ok = all(
            v.get('status') in ('ready', 'ok', 'not-configured')
            for v in readiness.values()
        )
        sys.exit(0 if services_ok and features_ok else 1)
except Exception as exc:
    print(f'PROBE ERROR: {exc}', file=sys.stderr)
    sys.exit(1)
" 2>&1 || true
}

# ---------------------------------------------------------------------------
# Helper: wait for health, with per-attempt diagnostics
# ---------------------------------------------------------------------------
wait_for_health() {
    local phase="${1:-deploy}"  # "deploy" or "rollback"
    local attempts=0
    local healthy=0

    # All log output goes to stderr so callers can capture stdout safely:
    #   HEALTHY="$(wait_for_health "deploy")"
    # captures only the final "0" or "1", not the log lines.
    log_ts "--- Waiting for /health (max ${HEALTH_MAX_ATTEMPTS} attempts, ${HEALTH_SLEEP}s interval) ---" >&2

    while [[ "$attempts" -lt "$HEALTH_MAX_ATTEMPTS" ]]; do
        attempts=$((attempts + 1))
        log_ts "  Attempt $attempts/${HEALTH_MAX_ATTEMPTS} [$phase]" >&2

        # Per-service container state
        for svc in pipeline web; do
            log_ts "    $svc: $(container_state "$svc")" >&2
        done
        if docker compose -f "$COMPOSE_FILE" config --services 2>/dev/null | grep -Fxq mcp; then
            log_ts "    mcp: $(container_state "mcp")" >&2
        fi

        if docker compose -f "$COMPOSE_FILE" exec -T web python -c \
            "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=4)" 2>/dev/null; then
            healthy=1
            break
        fi

        log_ts "  /health not ready yet -- waiting ${HEALTH_SLEEP}s" >&2
        sleep "$HEALTH_SLEEP"
    done

    echo "$healthy"
}

# ---------------------------------------------------------------------------
# Helper: optional GGG server-local content sync
# ---------------------------------------------------------------------------
sync_optional_ggg_content() {
    if [[ "$GGG_SYNC_ENABLED" != "1" ]]; then
        log_ts "--- GGG sync: disabled (GGG_SYNC_ENABLED=$GGG_SYNC_ENABLED) ---"
        return
    fi

    if [[ ! -d "$GGG_SYNC_SOURCE" ]]; then
        log_ts "--- GGG sync: source not found ($GGG_SYNC_SOURCE); skipping ---"
        return
    fi

    log_ts "--- GGG sync: source=$GGG_SYNC_SOURCE dest=$GGG_SYNC_DEST ---"
    mkdir -p "$GGG_SYNC_DEST"
    rsync -av --delete --exclude '.git/' "$GGG_SYNC_SOURCE/" "$GGG_SYNC_DEST/"

    if [[ "$GGG_REGENERATE_FEED" == "1" ]] && [[ -f "$GGG_SYNC_DEST/generator/generate-site.js" ]] && [[ -f "$GGG_SYNC_DEST/generator/validate-feed.js" ]]; then
        if command -v node >/dev/null 2>&1; then
            log_ts "--- GGG sync: regenerating and validating feed ---"
            (cd "$GGG_SYNC_DEST" && node generator/generate-site.js && node generator/validate-feed.js)
        else
            log_ts "--- GGG sync: Node.js not found; skipping feed generation ---"
        fi
    else
        log_ts "--- GGG sync: generator files not found or regeneration disabled; skipping feed generation ---"
    fi
}



# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
log_ts "=== ACB Large Print Toolkit -- Deploy (script started) ==="
log_ts "Log file: $LOG_FILE"
set_deploy_status "preflight" "in_progress" "deploy-app.sh preflight checks"
echo ""

if [[ "$(whoami)" == "root" ]]; then
    log_ts "ERROR: Do not run this script as root. Run as the deploy user."
    exit 1
fi

if ! command -v docker &>/dev/null; then
    log_ts "ERROR: Docker is not installed. Run bootstrap-server.sh first."
    exit 1
fi

if ! docker info &>/dev/null 2>&1; then
    log_ts "ERROR: Cannot connect to Docker daemon."
    log_ts "       Ensure your user is in the docker group: sudo usermod -aG docker $(whoami)"
    log_ts "       Then log out and back in."
    exit 1
fi

log_ts "App root:     $APP_ROOT"
log_ts "Web root:     $WEB_ROOT"
log_ts "Compose file: $COMPOSE_FILE"
log_ts "Domain:       $APP_DOMAIN"
echo ""

read_env_value() {
    local file="$1"
    local key="$2"
    python3 - "$file" "$key" <<'PYEOF'
from pathlib import Path
import sys

path = Path(sys.argv[1])
key = sys.argv[2]
if not path.exists():
    print("")
    raise SystemExit(0)
for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
    if line.startswith(key + "="):
        print(line.split("=", 1)[1].strip())
        break
else:
    print("")
PYEOF
}

upsert_env_value() {
    local file="$1"
    local key="$2"
    local value="$3"
    python3 - "$file" "$key" "$value" <<'PYEOF'
from pathlib import Path
import sys

path = Path(sys.argv[1])
key = sys.argv[2]
value = sys.argv[3]
lines = []
if path.exists():
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()

updated = False
for idx, line in enumerate(lines):
    if line.startswith(key + "="):
        lines[idx] = f"{key}={value}"
        updated = True
        break

if not updated:
    if lines and lines[-1] != "":
        lines.append("")
    lines.append(f"{key}={value}")

path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PYEOF
}

# Check required files
MISSING=0
for F in "$WEB_ROOT/$COMPOSE_FILE" "$WEB_ROOT/Caddyfile" "$WEB_ROOT/Dockerfile"; do
    if [[ ! -f "$F" ]]; then
        log_ts "ERROR: Required file missing: $F"
        MISSING=1
    else
        log_ts "OK: $F exists"
    fi
done

if [[ ! -f "$WEB_ROOT/.env" ]]; then
    if [[ -f "$WEB_ROOT/.env.example" ]]; then
        log_ts "WARNING: $WEB_ROOT/.env missing -- seeding from .env.example"
        cp "$WEB_ROOT/.env.example" "$WEB_ROOT/.env"
        GENERATED_SECRET="$(python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
)"
        python3 - "$WEB_ROOT/.env" "$GENERATED_SECRET" <<'PYEOF'
from pathlib import Path
import sys

path = Path(sys.argv[1])
secret = sys.argv[2]
text = path.read_text(encoding="utf-8")
text = text.replace("SECRET_KEY=PASTE_GENERATED_KEY_HERE", f"SECRET_KEY={secret}")
path.write_text(text, encoding="utf-8")
PYEOF
        chmod 600 "$WEB_ROOT/.env"
        log_ts "WARNING: Review $WEB_ROOT/.env and replace placeholder values before enabling optional features."
    else
        log_ts "ERROR: Required file missing: $WEB_ROOT/.env"
        MISSING=1
    fi
else
    log_ts "OK: $WEB_ROOT/.env exists"
fi

KEYCLOAK_BASE_URL_VALUE="$(read_env_value "$WEB_ROOT/.env" "KEYCLOAK_BASE_URL")"
if [[ -z "$KEYCLOAK_BASE_URL_VALUE" || "$KEYCLOAK_BASE_URL_VALUE" == "PASTE_GENERATED_KEY_HERE" ]]; then
    KEYCLOAK_BASE_URL_VALUE="https://${APP_DOMAIN}/auth"
fi
KEYCLOAK_REALM_VALUE="$(read_env_value "$WEB_ROOT/.env" "KEYCLOAK_REALM")"
if [[ -z "$KEYCLOAK_REALM_VALUE" || "$KEYCLOAK_REALM_VALUE" == "PASTE_GENERATED_KEY_HERE" ]]; then
    KEYCLOAK_REALM_VALUE="glow"
fi
KEYCLOAK_CLIENT_ID_VALUE="$(read_env_value "$WEB_ROOT/.env" "KEYCLOAK_CLIENT_ID")"
if [[ -z "$KEYCLOAK_CLIENT_ID_VALUE" || "$KEYCLOAK_CLIENT_ID_VALUE" == "PASTE_GENERATED_KEY_HERE" ]]; then
    KEYCLOAK_CLIENT_ID_VALUE="glow-web"
fi
KEYCLOAK_REDIRECT_URI_VALUE="$(read_env_value "$WEB_ROOT/.env" "KEYCLOAK_REDIRECT_URI")"
if [[ -z "$KEYCLOAK_REDIRECT_URI_VALUE" || "$KEYCLOAK_REDIRECT_URI_VALUE" == "PASTE_GENERATED_KEY_HERE" ]]; then
    KEYCLOAK_REDIRECT_URI_VALUE="https://${APP_DOMAIN}/authorize"
fi
KEYCLOAK_HOSTNAME_VALUE="$(read_env_value "$WEB_ROOT/.env" "KEYCLOAK_HOSTNAME")"
if [[ -z "$KEYCLOAK_HOSTNAME_VALUE" || "$KEYCLOAK_HOSTNAME_VALUE" == "PASTE_GENERATED_KEY_HERE" ]]; then
    KEYCLOAK_HOSTNAME_VALUE="$APP_DOMAIN"
fi
KEYCLOAK_CLIENT_SECRET_VALUE="$(read_env_value "$WEB_ROOT/.env" "KEYCLOAK_CLIENT_SECRET")"
if [[ -z "$KEYCLOAK_CLIENT_SECRET_VALUE" || "$KEYCLOAK_CLIENT_SECRET_VALUE" == "PASTE_GENERATED_KEY_HERE" ]]; then
    KEYCLOAK_CLIENT_SECRET_VALUE="$(python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
)"
    upsert_env_value "$WEB_ROOT/.env" "KEYCLOAK_CLIENT_SECRET" "$KEYCLOAK_CLIENT_SECRET_VALUE"
fi
KEYCLOAK_ADMIN_PASSWORD_VALUE="$(read_env_value "$WEB_ROOT/.env" "KEYCLOAK_ADMIN_PASSWORD")"
if [[ -z "$KEYCLOAK_ADMIN_PASSWORD_VALUE" || "$KEYCLOAK_ADMIN_PASSWORD_VALUE" == "PASTE_GENERATED_KEY_HERE" ]]; then
    KEYCLOAK_ADMIN_PASSWORD_VALUE="$(python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
)"
    upsert_env_value "$WEB_ROOT/.env" "KEYCLOAK_ADMIN_PASSWORD" "$KEYCLOAK_ADMIN_PASSWORD_VALUE"
fi
upsert_env_value "$WEB_ROOT/.env" "KEYCLOAK_BASE_URL" "$KEYCLOAK_BASE_URL_VALUE"
upsert_env_value "$WEB_ROOT/.env" "KEYCLOAK_REALM" "$KEYCLOAK_REALM_VALUE"
upsert_env_value "$WEB_ROOT/.env" "KEYCLOAK_CLIENT_ID" "$KEYCLOAK_CLIENT_ID_VALUE"
upsert_env_value "$WEB_ROOT/.env" "KEYCLOAK_REDIRECT_URI" "$KEYCLOAK_REDIRECT_URI_VALUE"
upsert_env_value "$WEB_ROOT/.env" "KEYCLOAK_HOSTNAME" "$KEYCLOAK_HOSTNAME_VALUE"
upsert_env_value "$WEB_ROOT/.env" "OIDC_SCOPES" "openid email profile"

KEYCLOAK_TEMPLATE="$WEB_ROOT/keycloak/realm.template.json"
KEYCLOAK_IMPORT_DIR="$WEB_ROOT/keycloak/import"
KEYCLOAK_REALM_FILE="$KEYCLOAK_IMPORT_DIR/glow-realm.json"
if [[ -f "$KEYCLOAK_TEMPLATE" ]]; then
    mkdir -p "$KEYCLOAK_IMPORT_DIR"
    rm -f "$KEYCLOAK_IMPORT_DIR"/*
    python3 - "$KEYCLOAK_TEMPLATE" "$KEYCLOAK_REALM_FILE" "$KEYCLOAK_REALM_VALUE" "$KEYCLOAK_CLIENT_ID_VALUE" "$KEYCLOAK_CLIENT_SECRET_VALUE" "$KEYCLOAK_BASE_URL_VALUE" "$KEYCLOAK_REDIRECT_URI_VALUE" <<'PYEOF'
from pathlib import Path
import sys

template = Path(sys.argv[1]).read_text(encoding="utf-8")
output = Path(sys.argv[2])
realm = sys.argv[3]
client_id = sys.argv[4]
client_secret = sys.argv[5]
base_url = sys.argv[6]
redirect_uri = sys.argv[7]

rendered = (
    template.replace("__KEYCLOAK_REALM__", realm)
    .replace("__KEYCLOAK_CLIENT_ID__", client_id)
    .replace("__KEYCLOAK_CLIENT_SECRET__", client_secret)
    .replace("__KEYCLOAK_BASE_URL__", base_url)
    .replace("__KEYCLOAK_REDIRECT_URI__", redirect_uri)
)
output.write_text(rendered, encoding="utf-8")
PYEOF
    chmod 600 "$WEB_ROOT/.env"
    log_ts "Keycloak realm import materialized at $KEYCLOAK_REALM_FILE"
else
    log_ts "WARNING: Keycloak realm template missing at $KEYCLOAK_TEMPLATE"
fi

if [[ ! -d "$APP_ROOT/desktop/src/acb_large_print" ]]; then
    log_ts "ERROR: desktop/src/acb_large_print/ directory missing (needed for Docker build)."
    MISSING=1
fi

if [[ "$MISSING" -eq 1 ]]; then
    echo ""
    log_ts "Fix the missing files and re-run this script."
    exit 1
fi

# ---------------------------------------------------------------------------
# Optional: pull latest from Git
# ---------------------------------------------------------------------------
if [[ -d "$APP_ROOT/.git" ]]; then
    PRE_DEPLOY_COMMIT=$(cd "$APP_ROOT" && git rev-parse HEAD)
    log_ts "--- Git: pre-deploy commit = $PRE_DEPLOY_COMMIT ---"
    log_ts "--- Git: pulling latest code from origin/main ---"
    cd "$APP_ROOT"
    git pull origin main
    POST_PULL_COMMIT=$(git rev-parse HEAD)
    log_ts "--- Git: post-pull commit  = $POST_PULL_COMMIT ---"
    if [[ "$PRE_DEPLOY_COMMIT" == "$POST_PULL_COMMIT" ]]; then
        log_ts "--- Git: no new commits (already up to date) ---"
    else
        log_ts "--- Git: $(git log --oneline "$PRE_DEPLOY_COMMIT".."$POST_PULL_COMMIT") ---"
    fi
fi

# ---------------------------------------------------------------------------
# Optional: pre-deploy feedback DB backup
# ---------------------------------------------------------------------------
if [[ "$ENABLE_PREDEPLOY_BACKUP" == "1" ]]; then
    if [[ -x "$APP_ROOT/scripts/backup-feedback.sh" ]]; then
        log_ts "--- Creating pre-deploy feedback backup ---"
        bash "$APP_ROOT/scripts/backup-feedback.sh"
        log_ts "--- Backup complete ---"
    else
        log_ts "--- Skipping pre-deploy backup (backup-feedback.sh not executable) ---"
    fi
fi

# ---------------------------------------------------------------------------
# Optional: sync GGG server-local content before compose rollout
# ---------------------------------------------------------------------------
sync_optional_ggg_content

# ---------------------------------------------------------------------------
# Enable maintenance mode
# ---------------------------------------------------------------------------
log_ts "--- Enabling maintenance mode (MAINTENANCE_MODE=1) ---"
export MAINTENANCE_MODE=1
MAINTENANCE_ENABLED=1
set_deploy_status "maintenance_on" "in_progress" "Maintenance mode enabled"

# ---------------------------------------------------------------------------
# Build and start containers
# ---------------------------------------------------------------------------
cd "$WEB_ROOT"

log_ts "--- Building and starting containers (docker compose up -d --build) ---"
log_ts "    Build output follows:"
set_deploy_status "compose_up" "in_progress" "Building and starting containers"
if [[ "$COMPOSE_REMOVE_ORPHANS" == "1" ]]; then
    docker compose -f "$COMPOSE_FILE" up -d --build --remove-orphans
else
    docker compose -f "$COMPOSE_FILE" up -d --build
fi
log_ts "--- docker compose up complete ---"

# Show initial container state immediately after launch
log_ts "--- Initial container state after launch ---"
docker compose -f "$COMPOSE_FILE" ps
echo ""

# ---------------------------------------------------------------------------
# Wait for health check
# ---------------------------------------------------------------------------
HEALTHY="$(wait_for_health "deploy")"
set_deploy_status "health_wait" "in_progress" "Waiting for /health readiness"
echo ""

if [[ "$HEALTHY" -eq 1 ]]; then
    log_ts "--- Health check: PASSED ---"
    probe_health_json "Full health readiness on success"

    log_ts "--- Disabling maintenance mode (site is now live) ---"
    export MAINTENANCE_MODE=0
    MAINTENANCE_ENABLED=0
    set_deploy_status "maintenance_off" "in_progress" "Maintenance mode disabled"
    if [[ "$COMPOSE_REMOVE_ORPHANS" == "1" ]]; then
        docker compose -f "$COMPOSE_FILE" up -d --build --remove-orphans
    else
        docker compose -f "$COMPOSE_FILE" up -d --build
    fi
    log_ts "--- Maintenance mode disabled successfully ---"

    # Force the proxy to pick up bind-mounted Caddyfile changes. A plain
    # `docker compose up -d --build` can leave the long-lived Caddy container
    # running with stale config even though the file on disk has changed.
    log_ts "--- Validating Caddy configuration ---"
    docker run --rm \
        -v "$WEB_ROOT/Caddyfile:/etc/caddy/Caddyfile:ro" \
        caddy:2-alpine \
        caddy validate --config /etc/caddy/Caddyfile

    log_ts "--- Recreating Caddy container to apply updated proxy configuration ---"
    docker compose -f "$COMPOSE_FILE" up -d --no-deps --force-recreate caddy

    log_ts "--- Caddy container state after recreation ---"
    docker compose -f "$COMPOSE_FILE" ps caddy

    # ---------------------------------------------------------------------------
    # Ensure Kokoro speech model files are present in the speech-models volume.
    # The Dockerfile attempts to pre-download them at build time, but that step
    # is a best-effort (network may be unavailable in the build environment).
    # This post-deploy step guarantees the files exist in the running container.
    # It is a no-op if the files are already there, so it is safe to run every
    # deployment.
    # ---------------------------------------------------------------------------
    log_ts "--- Ensuring Kokoro speech model files are present ---"
    docker compose -f "$COMPOSE_FILE" exec -T web python -c "
import os, sys
from pathlib import Path
model_dir = Path(os.environ.get('GLOW_SPEECH_MODEL_DIR', '/app/instance/speech_models'))
onnx_file = model_dir / 'kokoro-v1.0.onnx'
voices_file = model_dir / 'voices-v1.0.bin'
if onnx_file.exists() and voices_file.exists():
    print(f'Kokoro models already present in {model_dir} -- skipping download.')
    sys.exit(0)
print(f'Kokoro models not found in {model_dir} -- downloading from kokoro-onnx release assets...')
try:
    import urllib.request
    model_dir.mkdir(parents=True, exist_ok=True)
    base = 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0'
    urllib.request.urlretrieve(f'{base}/kokoro-v1.0.onnx', onnx_file)
    urllib.request.urlretrieve(f'{base}/voices-v1.0.bin', voices_file)
    print('Kokoro models downloaded successfully.')
except Exception as exc:
    print(f'WARNING: Kokoro model download failed: {exc}')
    print('Speech Studio will show Not Ready until models are added manually.')
    print('Manual install: docker compose exec web python -c \"from pathlib import Path; import urllib.request; d=Path(\\\"/app/instance/speech_models\\\"); d.mkdir(parents=True, exist_ok=True); base=\\\"https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0\\\"; urllib.request.urlretrieve(f\\\"{base}/kokoro-v1.0.onnx\\\", d/\\\"kokoro-v1.0.onnx\\\"); urllib.request.urlretrieve(f\\\"{base}/voices-v1.0.bin\\\", d/\\\"voices-v1.0.bin\\\")\"')
" 2>&1 || log_ts "WARNING: Could not exec into web container to check speech models."
    log_ts "--- Speech model check complete ---"

    # ---------------------------------------------------------------------------
    # Ensure curated Piper voices are present in the speech-models volume.
    # The named Docker volume hides any build-time model files, so seed the
    # runtime volume as part of deployment too.
    # ---------------------------------------------------------------------------
    log_ts "--- Ensuring curated Piper voice model files are present ---"
    docker compose -f "$COMPOSE_FILE" exec -T web python -c "
import os, sys
from pathlib import Path
model_dir = Path(os.environ.get('GLOW_SPEECH_MODEL_DIR', '/app/instance/speech_models')) / 'piper'
voices = [
    ('en_US-lessac-medium', 'en/en_US/lessac/medium/en_US-lessac-medium'),
    ('en_US-amy-medium', 'en/en_US/amy/medium/en_US-amy-medium'),
    ('en_US-ryan-high', 'en/en_US/ryan/high/en_US-ryan-high'),
    ('en_US-hfc_female-medium', 'en/en_US/hfc_female/medium/en_US-hfc_female-medium'),
    ('en_GB-alan-medium', 'en/en_GB/alan/medium/en_GB-alan-medium'),
    ('en_GB-southern_english_female-low', 'en/en_GB/southern_english_female/low/en_GB-southern_english_female-low'),
]
print(f'Ensuring {len(voices)} curated Piper voices in {model_dir}...')
try:
    import urllib.request
    model_dir.mkdir(parents=True, exist_ok=True)
    base = 'https://huggingface.co/rhasspy/piper-voices/resolve/main'
    downloaded = 0
    skipped = 0
    failed = 0
    for voice_id, rel in voices:
        model_file = model_dir / f'{voice_id}.onnx'
        config_file = model_dir / f'{voice_id}.onnx.json'
        if model_file.exists() and config_file.exists():
            skipped += 1
            continue
        try:
            urllib.request.urlretrieve(f'{base}/{rel}.onnx', model_file)
            urllib.request.urlretrieve(f'{base}/{rel}.onnx.json', config_file)
            downloaded += 1
        except Exception as voice_exc:
            failed += 1
            print(f'WARNING: Failed to download {voice_id}: {voice_exc}')
    print(f'Piper voice seeding complete. downloaded={downloaded} skipped={skipped} failed={failed}')
except Exception as exc:
    print(f'WARNING: Piper voice download failed: {exc}')
    print('Piper voices will show Not Ready until model files are added manually.')
" 2>&1 || log_ts "WARNING: Could not exec into web container to check Piper voice models."
    log_ts "--- Piper voice model check complete ---"

    # If Kokoro models are now present, ensure GLOW_ENABLE_SPEECH=true in feature_flags.json
    SPEECH_FLAG_FILE="$APP_ROOT/instance/feature_flags.json"
    if docker compose -f "$COMPOSE_FILE" exec -T web python -c "
import os
from pathlib import Path
d = Path(os.environ.get('GLOW_SPEECH_MODEL_DIR', '/app/instance/speech_models'))
exit(0 if (d / 'kokoro-v1.0.onnx').exists() and (d / 'voices-v1.0.bin').exists() else 1)
" 2>/dev/null; then
        if [[ -f "$SPEECH_FLAG_FILE" ]]; then
            if ! python3 -c "import json; d=json.load(open('$SPEECH_FLAG_FILE')); exit(0 if d.get('GLOW_ENABLE_SPEECH') else 1)" 2>/dev/null; then
                log_ts "--- Enabling GLOW_ENABLE_SPEECH in feature_flags.json (models present) ---"
                python3 -c "
import json
p = '$SPEECH_FLAG_FILE'
d = json.load(open(p))
d['GLOW_ENABLE_SPEECH'] = True
open(p,'w').write(json.dumps(d, indent=2) + '\n')
print('GLOW_ENABLE_SPEECH enabled.')
"
            else
                log_ts "--- GLOW_ENABLE_SPEECH already enabled in feature_flags.json ---"
            fi
        fi
    fi

    if [[ "$CLEANUP_ON_SUCCESS" == "1" ]]; then
        run_optional_cleanup "success"
    else
        log_ts "--- Skipping cleanup on success (CLEANUP_ON_SUCCESS=$CLEANUP_ON_SUCCESS) ---"
    fi

    set_deploy_status "complete" "completed" "Deploy app script completed successfully"

else
    log_ts "--- Health check: FAILED after ${HEALTH_MAX_ATTEMPTS} attempts ---"
    set_deploy_status "health_failed" "failed" "Health check failed before maintenance-off"
    probe_health_json "Partial health state on failure"

    log_ts "--- Dumping recent container logs for all services ---"
    dump_service_logs pipeline 60
    dump_service_logs web 80
    dump_service_logs caddy 20

    log_ts "--- Docker container inspect (web) ---"
    WEB_CID="$(docker compose -f "$COMPOSE_FILE" ps -q web 2>/dev/null | head -n1)"
    if [[ -n "$WEB_CID" ]]; then
        docker inspect --format '
Container: {{.Name}}
  State:   {{.State.Status}}
  Started: {{.State.StartedAt}}
  Error:   {{.State.Error}}
  Health:  {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}
' "$WEB_CID" || true
    fi

    log_ts "--- Disabling maintenance mode before rollback ---"
    export MAINTENANCE_MODE=0
    MAINTENANCE_ENABLED=0

    if [[ -n "$PRE_DEPLOY_COMMIT" && -d "$APP_ROOT/.git" ]]; then
        log_ts "--- Attempting rollback to previous commit: $PRE_DEPLOY_COMMIT ---"
        cd "$APP_ROOT"
        git checkout -f "$PRE_DEPLOY_COMMIT"
        log_ts "--- Rollback checkout complete; rebuilding containers ---"

        cd "$WEB_ROOT"
        if [[ "$COMPOSE_REMOVE_ORPHANS" == "1" ]]; then
            docker compose -f "$COMPOSE_FILE" up -d --build --remove-orphans
        else
            docker compose -f "$COMPOSE_FILE" up -d --build
        fi
        log_ts "--- Rollback containers started ---"

        ROLLBACK_HEALTHY="$(wait_for_health "rollback")"
        echo ""

        if [[ "$ROLLBACK_HEALTHY" -eq 1 ]]; then
            ROLLED_BACK=1
            set_deploy_status "rollback_complete" "degraded" "Deploy failed; rollback succeeded"
            log_ts "--- Rollback health check: PASSED ---"
            probe_health_json "Rollback health readiness"

            if [[ "$CLEANUP_ON_ROLLBACK" == "1" ]]; then
                run_optional_cleanup "rollback"
            else
                log_ts "--- Skipping cleanup after rollback (CLEANUP_ON_ROLLBACK=$CLEANUP_ON_ROLLBACK) ---"
            fi
        else
            log_ts "--- Rollback health check: FAILED ---"
            set_deploy_status "rollback_failed" "failed" "Deploy failed and rollback failed"
            dump_service_logs web 60
            log_ts "    Manual intervention required."
            exit 1
        fi
    else
        log_ts "--- Rollback unavailable (no Git commit baseline or no .git directory). ---"
        set_deploy_status "rollback_unavailable" "failed" "Deploy failed and rollback unavailable"
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# Final status
# ---------------------------------------------------------------------------
echo ""
log_ts "--- Final container status ---"
docker compose -f "$COMPOSE_FILE" ps

echo ""
log_ts "=== Deployment complete ==="
echo ""
if [[ "$ROLLED_BACK" -eq 1 ]]; then
    log_ts "NOTE: Deploy failed and was rolled back to $PRE_DEPLOY_COMMIT."
    log_ts "      Investigate the failed revision before retrying deployment."
    echo ""
fi
echo "Test these URLs:"
echo "  https://${APP_DOMAIN}/"
echo "  https://${APP_DOMAIN}/health"
if [[ -n "$APP_ALIAS_DOMAIN" ]]; then
    echo "  https://${APP_ALIAS_DOMAIN}/"
    echo "  https://${APP_ALIAS_DOMAIN}/health"
fi
echo "  https://${MAIN_DOMAIN}/"
echo ""
echo "Live log tail:"
echo "  cd $WEB_ROOT && docker compose -f $COMPOSE_FILE logs --tail 50 -f"
echo ""
echo "Deploy log:"
echo "  cat $LOG_FILE"
echo "  cat $LATEST_LOG_FILE   # always points to the most recent deploy"
