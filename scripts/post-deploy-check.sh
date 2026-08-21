#!/usr/bin/env bash
# post-deploy-check.sh -- Post-deployment maintenance tasks
#
# Run as deploy user:  bash ~/app/scripts/post-deploy-check.sh
#
# This script:
#   - Installs the backup cron job (daily at 2 AM) if not already set
#   - Installs the disk usage alert cron job (weekly Sunday 6 AM)
#   - Verifies Docker is enabled on boot
#   - Prunes unused Docker images
#   - Runs site and container health checks
#   - Fails deploy verification when required services are unhealthy
#   - Emits troubleshooting diagnostics for failing services
set -euo pipefail

APP_ROOT="${APP_ROOT:-$HOME/app}"
WEB_ROOT="${WEB_ROOT:-$APP_ROOT/web}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
APP_DOMAIN="${APP_DOMAIN:-letitglow.app}"
APP_ALIAS_DOMAIN="${APP_ALIAS_DOMAIN:-lp.csedesigns.com}"
APP_LEGACY_DOMAIN="${APP_LEGACY_DOMAIN:-glow.bits-acb.org}"
DEPLOY_STATUS_FILE="${DEPLOY_STATUS_FILE:-$APP_ROOT/instance/deploy-status.json}"
WCAG22AA_GATE="${WCAG22AA_GATE:-not-reported}"
WCAG22AAA_GATE="${WCAG22AAA_GATE:-not-configured}"
LOG_DIR="${LOG_DIR:-$HOME/deploy-logs}"
TS="$(date -u +%Y%m%d-%H%M%S)"
LOG_FILE="${LOG_DIR}/post-deploy-check-${TS}.log"
LATEST_LOG_FILE="${LOG_DIR}/post-deploy-check-latest.log"

mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

finalize_log() {
    cp "$LOG_FILE" "$LATEST_LOG_FILE" 2>/dev/null || true
    echo "Latest log pointer: $LATEST_LOG_FILE"
}

trap finalize_log EXIT

set_deploy_status() {
    local phase="$1"
    local state="$2"
    local detail="${3:-}"
    local aa="${4:-$WCAG22AA_GATE}"
    local aaa="${5:-$WCAG22AAA_GATE}"
    local container_status_file="/app/instance/deploy-status.json"
    mkdir -p "$(dirname "$DEPLOY_STATUS_FILE")"
    python3 - "$DEPLOY_STATUS_FILE" "$phase" "$state" "$detail" "$aa" "$aaa" <<'PYEOF' || true
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
phase = sys.argv[2]
state = sys.argv[3]
detail = sys.argv[4]
aa = sys.argv[5]
aaa = sys.argv[6]

payload = {}
if path.exists():
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        payload = {}

existing = payload.get("gates") if isinstance(payload.get("gates"), dict) else {}
payload.update({
    "phase": phase,
    "state": state,
    "detail": detail,
    "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    "gates": {
        "wcag22aa": str(aa or existing.get("wcag22aa", "unknown")),
        "wcag22aaa": str(aaa or existing.get("wcag22aaa", "unknown")),
    },
})
path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PYEOF

    # Also write to the in-container instance path consumed by /health.
    if [[ -f "$WEB_ROOT/$COMPOSE_FILE" ]]; then
        local web_cid
        web_cid="$(docker compose -f "$WEB_ROOT/$COMPOSE_FILE" ps -q web 2>/dev/null | head -n1)"
        if [[ -n "$web_cid" ]]; then
            docker compose -f "$WEB_ROOT/$COMPOSE_FILE" exec -T web python3 - "$container_status_file" "$phase" "$state" "$detail" "$aa" "$aaa" <<'PYEOF' || true
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
phase = sys.argv[2]
state = sys.argv[3]
detail = sys.argv[4]
aa = sys.argv[5]
aaa = sys.argv[6]

payload = {}
if path.exists():
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        payload = {}

existing = payload.get("gates") if isinstance(payload.get("gates"), dict) else {}
payload.update({
    "phase": phase,
    "state": state,
    "detail": detail,
    "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    "gates": {
        "wcag22aa": str(aa or existing.get("wcag22aa", "unknown")),
        "wcag22aaa": str(aaa or existing.get("wcag22aaa", "unknown")),
    },
})
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PYEOF
        fi
    fi
}

compose() {
    docker compose -f "$WEB_ROOT/$COMPOSE_FILE" "$@"
}

compose_has_service() {
    local service="$1"
    compose config --services 2>/dev/null | grep -Fxq "$service"
}

service_cid() {
    local service="$1"
    compose ps -q "$service" | head -n 1
}

dump_service_diagnostics() {
    local service="$1"
    local cid
    cid="$(service_cid "$service")"

    echo "--- Diagnostics: $service ---"
    if [[ -z "$cid" ]]; then
        echo "  Container not found for service '$service'."
        return
    fi

    echo "  Container ID: $cid"
    docker inspect --format '  State={{.State.Status}} Health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$cid" || true
    echo "  Recent health log entries:"
    docker inspect --format '{{if .State.Health}}{{range .State.Health.Log}}  - {{.Start}} exit={{.ExitCode}} output={{printf "%q" .Output}}{{println}}{{end}}{{else}}  - none{{end}}' "$cid" || true
    echo "  Last 120 service log lines:"
    compose logs --tail 120 "$service" || true

    if [[ "$service" == "ollama" ]]; then
        echo "  Ollama probe from inside container (ollama list):"
        compose exec -T ollama ollama list || true
    fi
}

wait_for_service_healthy() {
    local service="$1"
    local timeout_seconds="$2"
    local interval_seconds="${3:-5}"
    local max_attempts=$((timeout_seconds / interval_seconds))
    local attempt=1

    if (( max_attempts < 1 )); then
        max_attempts=1
    fi

    echo "--- Waiting for service health: $service (timeout ${timeout_seconds}s) ---"
    while (( attempt <= max_attempts )); do
        local cid state health
        cid="$(service_cid "$service")"
        if [[ -z "$cid" ]]; then
            echo "  $service: container missing (attempt $attempt/$max_attempts)"
        else
            state="$(docker inspect --format '{{.State.Status}}' "$cid" 2>/dev/null || echo unknown)"
            health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$cid" 2>/dev/null || echo unknown)"
            echo "  $service: state=$state health=$health (attempt $attempt/$max_attempts)"
            if [[ "$state" == "running" && "$health" == "healthy" ]]; then
                return 0
            fi
        fi
        sleep "$interval_seconds"
        attempt=$((attempt + 1))
    done
    return 1
}

# --- Pre-flight checks ---
if [[ "$(whoami)" == "root" ]]; then
    echo "ERROR: Run this as the deploy user, not root."
    exit 1
fi

echo "=== Post-Deploy Maintenance ==="
echo "Log file: $LOG_FILE"
set_deploy_status "post_deploy_checks" "in_progress" "Running post-deploy verification"
echo ""

# --- 1. Backup cron job ---
BACKUP_CRON="0 2 * * * /home/deploy/app/scripts/backup-feedback.sh >> /home/deploy/backups/backup.log 2>&1"
DISK_CRON="0 6 * * 0 df -h / | awk 'NR==2 && int(\$5)>80' >> /home/deploy/disk-alerts.log 2>&1"

echo "--- Checking cron jobs ---"

CURRENT_CRON=$(crontab -l 2>/dev/null || true)

CHANGED=false

if echo "$CURRENT_CRON" | grep -qF "backup-feedback.sh"; then
    echo "  Backup cron job: already installed"
else
    CURRENT_CRON=$(printf '%s\n%s\n' "$CURRENT_CRON" "# Daily feedback DB backup at 2 AM")
    CURRENT_CRON=$(printf '%s\n%s\n' "$CURRENT_CRON" "$BACKUP_CRON")
    CHANGED=true
    echo "  Backup cron job: ADDED (daily at 2 AM)"
fi

if echo "$CURRENT_CRON" | grep -qF "disk-alerts.log"; then
    echo "  Disk alert cron job: already installed"
else
    CURRENT_CRON=$(printf '%s\n%s\n' "$CURRENT_CRON" "# Weekly disk usage warning (Sunday 6 AM)")
    CURRENT_CRON=$(printf '%s\n%s\n' "$CURRENT_CRON" "$DISK_CRON")
    CHANGED=true
    echo "  Disk alert cron job: ADDED (Sunday 6 AM)"
fi

if [[ "$CHANGED" == "true" ]]; then
    echo "$CURRENT_CRON" | crontab -
    echo "  Crontab updated."
else
    echo "  No cron changes needed."
fi

echo ""

# --- 2. Docker enabled on boot ---
echo "--- Checking Docker boot status ---"
if systemctl is-enabled docker >/dev/null 2>&1; then
    echo "  Docker: enabled on boot"
else
    echo "  Docker: NOT enabled -- enabling now..."
    sudo systemctl enable docker
    echo "  Docker: enabled"
fi
echo ""

# --- 3. Prune unused Docker images ---
echo "--- Pruning unused Docker images ---"
RECLAIMED=$(docker image prune -f 2>&1)
echo "  $RECLAIMED" | tail -1
echo ""

# --- 4. Site health checks ---
echo "--- Running health checks ---"

check_url() {
    local label="$1"
    local url="$2"
    local required="${3:-false}"
    local allow_redirect="${4:-false}"
    local code
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$url" 2>/dev/null || echo "000")
    local ok=0
    if [[ "$code" == "200" ]]; then
        ok=1
    elif [[ "$allow_redirect" == "true" && "$code" =~ ^3[0-9][0-9]$ ]]; then
        ok=1
    fi

    if [[ "$ok" -eq 1 ]]; then
        echo "  $label: OK ($code)"
        return 0
    else
        echo "  $label: PROBLEM ($code)"
        if [[ "$required" == "true" ]]; then
            return 1
        fi
        return 0
    fi
}

check_header_contains() {
    local label="$1"
    local url="$2"
    local header_name="$3"
    local expected_fragment="$4"
    local required="${5:-false}"
    local headers
    headers=$(curl -s -I --max-time 15 "$url" 2>/dev/null || true)

    if echo "$headers" | grep -Fi "$header_name:" | grep -Fqi "$expected_fragment"; then
        echo "  $label: OK ($header_name contains '$expected_fragment')"
        return 0
    fi

    echo "  $label: PROBLEM ($header_name missing '$expected_fragment')"
    if [[ "$required" == "true" ]]; then
        return 1
    fi
    return 0
}

# NOTE: External URL checks are informational only (000 is common when the server
# cannot curl its own domain due to DNS loopback). Container health gates below
# are the authoritative liveness check.
URL_FAIL=0
check_url "${APP_DOMAIN}/health" "https://${APP_DOMAIN}/health" false || true
check_url "${APP_DOMAIN}/" "https://${APP_DOMAIN}/" false true || true
if compose_has_service "mcp"; then
    check_url "${APP_DOMAIN}/mcp/health" "https://${APP_DOMAIN}/mcp/health" true || URL_FAIL=1
fi
# The consent gate redirects an anonymous visitor, so a 3xx here is the
# correct answer rather than a problem.
check_url "${APP_DOMAIN}/speech/" "https://${APP_DOMAIN}/speech/" false true || true
check_url "${APP_DOMAIN}/ggg/" "https://${APP_DOMAIN}/ggg/" false || true
check_header_contains "${APP_DOMAIN} CSP media-src" "https://${APP_DOMAIN}/static/let-it-glow.mp3" "Content-Security-Policy" "media-src 'self'" true || URL_FAIL=1
if [[ -n "$APP_ALIAS_DOMAIN" ]]; then
    check_url "${APP_ALIAS_DOMAIN}/health" "https://${APP_ALIAS_DOMAIN}/health" false true || true
    check_url "${APP_ALIAS_DOMAIN}/" "https://${APP_ALIAS_DOMAIN}/" false true true || true
    # Alias domains redirect to the canonical host by design.
    check_url "${APP_ALIAS_DOMAIN}/ggg/" "https://${APP_ALIAS_DOMAIN}/ggg/" false true || true
fi
if [[ -n "$APP_LEGACY_DOMAIN" ]]; then
    check_url "${APP_LEGACY_DOMAIN}/health" "https://${APP_LEGACY_DOMAIN}/health" false true || true
    check_url "${APP_LEGACY_DOMAIN}/" "https://${APP_LEGACY_DOMAIN}/" false true true || true
    check_url "${APP_LEGACY_DOMAIN}/ggg/" "https://${APP_LEGACY_DOMAIN}/ggg/" false true || true
fi
check_url "csedesigns.com/" "https://csedesigns.com/" false true || true

echo ""
echo "--- Container status ---"
compose ps --format "table {{.Name}}\t{{.Status}}"

echo ""
echo "--- Required service health gates ---"
SERVICE_FAIL=0
REQUIRED_SERVICES=(pipeline web)
if compose_has_service "mcp"; then
    REQUIRED_SERVICES+=(mcp)
else
    echo "  mcp: skipped (service not defined in $COMPOSE_FILE)"
fi
if compose_has_service "ollama"; then
    REQUIRED_SERVICES+=(ollama)
else
    echo "  ollama: skipped (service not defined in $COMPOSE_FILE)"
fi

for svc in "${REQUIRED_SERVICES[@]}"; do
    if ! wait_for_service_healthy "$svc" 180 5; then
        echo "  $svc: FAILED health gate"
        SERVICE_FAIL=1
        dump_service_diagnostics "$svc"
    else
        echo "  $svc: passed health gate"
    fi
done

echo ""
echo "--- Model readiness check via /health ---"
READINESS_FAIL=0
# Probe /health internally via the web container to avoid external DNS loopback issues
HEALTH_JSON="$(compose exec -T web python -c \
    "import urllib.request, json; r=urllib.request.urlopen('http://localhost:8000/health',timeout=5); print(r.read().decode())" \
    2>/dev/null || echo '{}')"
if command -v python3 &>/dev/null; then
    # The script itself arrives on stdin from the heredoc, so the JSON has to
    # travel in the environment. Reading stdin here always saw an empty
    # string, which is why every deploy reported "could not parse".
    HEALTH_JSON="$HEALTH_JSON" python3 - <<'PYEOF'
import json, sys, os
raw = os.environ.get("HEALTH_JSON", "")
try:
    data = json.loads(raw)
except Exception:
    preview = raw.strip()[:120] or "(empty response)"
    print(f"  WARN: could not parse /health response: {preview}")
    sys.exit(0)
readiness = data.get("readiness", {})
models    = data.get("models", {})
fail      = False
labels = {
    "chat":      "Ollama llama3 (chat)",
    "vision":    "Ollama llava (vision)",
    "whisperer": "Whisper model",
}
for key, label in labels.items():
    r = readiness.get(key, {})
    status        = r.get("status", "unknown")
    present       = r.get("model_present", r.get("dependency_present", None))
    warm          = r.get("model_warm", None)
    parts = [f"status={status}"]
    if present is not None:
        parts.append(f"present={present}")
    if warm is not None:
        parts.append(f"warm={warm}")
    detail = ", ".join(parts)
    if status in ("ready", "not-configured"):
        print(f"  {label}: OK ({detail})")
    else:
        print(f"  {label}: NOT READY ({detail})")
        fail = True
running = models.get("ollama_running", [])
if running:
    print(f"  Ollama models loaded in memory: {', '.join(running)}")
else:
    print("  Ollama models loaded in memory: none")
sys.exit(1 if fail else 0)
PYEOF
    READINESS_FAIL=$?
else
    echo "  WARN: python3 not available -- skipping readiness JSON parse"
fi <<< "$HEALTH_JSON"

echo ""
if [[ "$URL_FAIL" -ne 0 || "$SERVICE_FAIL" -ne 0 || "$READINESS_FAIL" -ne 0 ]]; then
    echo "=== Post-deploy verification FAILED ==="
    set_deploy_status "post_deploy_checks" "failed" "Post-deploy verification failed" "$WCAG22AA_GATE" "$WCAG22AAA_GATE"
    echo "See log file: $LOG_FILE"
    exit 1
fi

echo "=== Post-deploy verification PASSED ==="
set_deploy_status "post_deploy_complete" "completed" "Post-deploy verification passed" "$WCAG22AA_GATE" "$WCAG22AAA_GATE"
echo "Log saved: $LOG_FILE"
