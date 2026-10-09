#!/usr/bin/env bash
# update-csp.sh -- Add script-src 'self' to the Caddyfile CSP and reload
#
# Run as deploy user:  bash ~/app/scripts/update-csp.sh
#
# This is a one-time script for the guidelines JS fix (commit 22cecb5).
# It adds "script-src 'self'" to the Content-Security-Policy header in the
# live Caddyfile, then reloads Caddy and restarts the web container.
set -euo pipefail

APP_ROOT="${APP_ROOT:-$HOME/app}"
WEB_ROOT="${WEB_ROOT:-$APP_ROOT/web}"
CADDYFILE="${CADDYFILE:-$WEB_ROOT/caddy/Caddyfile}"
COMPOSE_FILE="docker-compose.prod.yml"

# --- Pre-flight checks ---
if [[ "$(whoami)" == "root" ]]; then
    echo "ERROR: Do not run this script as root. Run as the deploy user."
    exit 1
fi

if [[ ! -f "$CADDYFILE" ]]; then
    echo "ERROR: Caddyfile not found at $CADDYFILE"
    echo "       Set CADDYFILE=/path/to/Caddyfile and re-run."
    exit 1
fi

echo "=== Update CSP: Add script-src 'self' ==="
echo ""
echo "Caddyfile: $CADDYFILE"
echo ""

# --- Check if already updated ---
if grep -q "script-src 'self'" "$CADDYFILE"; then
    echo "CSP already contains script-src 'self'. No changes needed."
else
    # --- Back up current Caddyfile ---
    BACKUP="${CADDYFILE}.bak.$(date +%Y%m%d%H%M%S)"
    cp "$CADDYFILE" "$BACKUP"
    echo "Backup saved: $BACKUP"

    # --- Insert script-src 'self' after default-src 'none'; ---
    sed -i "s|default-src 'none';|default-src 'none'; script-src 'self';|" "$CADDYFILE"

    if grep -q "script-src 'self'" "$CADDYFILE"; then
        echo "CSP updated successfully."
    else
        echo "ERROR: sed replacement failed. Restoring backup."
        cp "$BACKUP" "$CADDYFILE"
        exit 1
    fi

    echo ""
    echo "Updated CSP line:"
    grep "Content-Security-Policy" "$CADDYFILE" || true
fi

echo ""

# --- Reload Caddy ---
echo "--- Reloading Caddy ---"
if command -v caddy &>/dev/null; then
    caddy reload --config "$CADDYFILE" --adapter caddyfile
    echo "Caddy reloaded."
elif sudo caddy reload --config "$CADDYFILE" --adapter caddyfile 2>/dev/null; then
    echo "Caddy reloaded (via sudo)."
else
    echo "WARNING: Could not reload Caddy automatically."
    echo "         Run manually: caddy reload --config $CADDYFILE --adapter caddyfile"
fi

echo ""

# --- Restart web container ---
echo "--- Restarting web container ---"
cd "$WEB_ROOT"
docker compose -f "$COMPOSE_FILE" restart web
echo "Web container restarted."

echo ""
echo "=== Done ==="
echo ""
echo "Verify with: curl -sI https://lp.csedesigns.com/ | grep -i content-security"
