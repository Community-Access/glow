#!/usr/bin/env bash
# maintenance-mode.sh -- Toggle maintenance mode for operational needs
#
# Usage:
#   bash ~/app/scripts/maintenance-mode.sh on       # Enable maintenance page
#   bash ~/app/scripts/maintenance-mode.sh off      # Disable (bring site live)
#   bash ~/app/scripts/maintenance-mode.sh status   # Check current status
#
# This script allows operators to show/hide the maintenance page WITHOUT
# redeploying code. Useful for:
#   - Database migrations, backups, or manual updates
#   - Security patches applied without code change
#   - Emergency maintenance windows
#   - Testing maintenance page appearance
#
# The /health endpoint always responds (no matter the mode) so monitoring
# systems, load balancers, and health checks always work.

set -euo pipefail

# --- Configuration ---
APP_ROOT="${APP_ROOT:-$HOME/app}"
WEB_ROOT="${WEB_ROOT:-$APP_ROOT/web}"
COMPOSE_FILE="docker-compose.prod.yml"

# --- Arguments ---
if [[ $# -lt 1 ]]; then
    echo "Usage: $0 {on|off|status}"
    echo ""
    echo "  on       -- Enable maintenance mode (show 'Under Maintenance' page)"
    echo "  off      -- Disable maintenance mode (bring site live)"
    echo "  status   -- Show current maintenance mode status"
    exit 1
fi

ACTION="$1"

# --- Pre-flight checks ---
if ! command -v docker &>/dev/null; then
    echo "ERROR: Docker is not installed."
    exit 1
fi

if ! docker info &>/dev/null 2>&1; then
    echo "ERROR: Cannot connect to Docker. Is your user in the docker group?"
    exit 1
fi

if [[ ! -f "$WEB_ROOT/$COMPOSE_FILE" ]]; then
    echo "ERROR: Docker Compose file not found: $WEB_ROOT/$COMPOSE_FILE"
    exit 1
fi

cd "$WEB_ROOT"

# --- Actions ---
case "$ACTION" in
    on)
        echo "--- Enabling maintenance mode ---"
        export MAINTENANCE_MODE=1
        docker compose -f "$COMPOSE_FILE" up -d
        echo "--- Maintenance mode: ENABLED ---"
        echo "    Users will see 'Under Maintenance' page"
        echo "    /health endpoint: still available"
        echo ""
        echo "Verify:"
        echo "  curl -I https://letitglow.app/        # Should see 503 Service Unavailable"
        echo "  curl -I https://letitglow.app/health   # Should see 200 OK"
        ;;
    off)
        echo "--- Disabling maintenance mode ---"
        export MAINTENANCE_MODE=0
        docker compose -f "$COMPOSE_FILE" up -d
        echo "--- Maintenance mode: DISABLED ---"
        echo "    Site is now live"
        echo ""
        echo "Verify:"
        echo "  curl -I https://letitglow.app/        # Should see 200 OK (home page)"
        echo "  curl -I https://letitglow.app/health   # Should see 200 OK"
        ;;
    status)
        echo "--- Checking maintenance mode status ---"
        RESULT=$(docker compose -f "$COMPOSE_FILE" exec -T web python -c \
            "import os; print('ON' if os.environ.get('MAINTENANCE_MODE', '0') == '1' else 'OFF')" 2>/dev/null || echo "UNKNOWN")
        if [[ "$RESULT" == "ON" ]]; then
            echo "Maintenance mode: ENABLED (site shows 'Under Maintenance' page)"
        elif [[ "$RESULT" == "OFF" ]]; then
            echo "Maintenance mode: DISABLED (site is live)"
        else
            echo "Status: UNKNOWN (could not connect to container)"
            echo "Containers running?"
            docker compose -f "$COMPOSE_FILE" ps
        fi
        ;;
    *)
        echo "ERROR: Unknown action '$ACTION'"
        echo "Usage: $0 {on|off|status}"
        exit 1
        ;;
esac

echo ""
echo "Container status:"
docker compose -f "$COMPOSE_FILE" ps
