#!/usr/bin/env bash
# backup-feedback.sh -- Back up the feedback SQLite database
#
# Run as deploy user:  bash ~/app/scripts/backup-feedback.sh
#
# Schedule via cron (daily at 2 AM):
#   0 2 * * * /home/deploy/app/scripts/backup-feedback.sh >> /home/deploy/backups/backup.log 2>&1
#
# This script:
#   - Copies the feedback database out of the Docker volume
#   - Saves it with a timestamp in the backups directory
#   - Removes backups older than KEEP_DAYS
set -euo pipefail

# --- Configuration ---
WEB_ROOT="${WEB_ROOT:-$HOME/app/web}"
BACKUP_ROOT="${BACKUP_ROOT:-$HOME/backups}"
COMPOSE_FILE="docker-compose.prod.yml"
KEEP_DAYS=30

# --- Pre-flight checks ---
if [[ "$(whoami)" == "root" ]]; then
    echo "$(date -Iseconds) ERROR: Do not run this script as root."
    exit 1
fi

mkdir -p "$BACKUP_ROOT"

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="$BACKUP_ROOT/feedback-$TIMESTAMP.db"

# Check if the compose file exists
if [[ ! -f "$WEB_ROOT/$COMPOSE_FILE" ]]; then
    echo "$(date -Iseconds) ERROR: Compose file not found: $WEB_ROOT/$COMPOSE_FILE"
    exit 1
fi

# --- Create backup ---
echo "$(date -Iseconds) Backing up feedback database..."
docker compose -f "$WEB_ROOT/$COMPOSE_FILE" cp web:/app/instance/feedback.db "$BACKUP_FILE"

# docker compose cp preserves the SOURCE file's mtime. feedback.db inside the
# container is months old, so without this touch the copy lands on disk already
# older than KEEP_DAYS and the rotation step below deletes it on the same run.
touch "$BACKUP_FILE"

if [[ -f "$BACKUP_FILE" ]]; then
    SIZE=$(stat --format='%s' "$BACKUP_FILE" 2>/dev/null || stat -f'%z' "$BACKUP_FILE" 2>/dev/null || echo "unknown")
    echo "$(date -Iseconds) Backup created: $BACKUP_FILE ($SIZE bytes)"
else
    echo "$(date -Iseconds) ERROR: Backup file was not created."
    exit 1
fi

# --- Rotate old backups ---
find "$BACKUP_ROOT" -name "feedback-*.db" -type f -mtime "+$KEEP_DAYS" -print -delete | while read -r OLD; do
    echo "$(date -Iseconds) Deleted old backup: $OLD"
done

# --- Summary ---
TOTAL=$(find "$BACKUP_ROOT" -name "feedback-*.db" -type f | wc -l)
echo "$(date -Iseconds) Total backups on disk: $TOTAL"
