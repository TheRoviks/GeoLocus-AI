#!/usr/bin/env bash
# Dumps postgres DB, validates result, rotates old backups, alerts Telegram on failure.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${SCRIPT_DIR}/.."

BACKUP_DIR="backups"
RETENTION_DAYS=7
mkdir -p "${BACKUP_DIR}"

TS=$(date +%Y%m%d-%H%M%S)
OUT="${BACKUP_DIR}/reminders-${TS}.sql.gz"

_alert_telegram() {
    local msg="$1"
    [[ -z "${BOT_TOKEN:-}" || -z "${ALERT_CHAT_ID:-}" ]] && return 0
    curl -sS --max-time 10 -o /dev/null \
        -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${ALERT_CHAT_ID}" \
        --data-urlencode "text=${msg}" || true
}

_on_error() {
    echo "ERROR: backup failed at line $1" >&2
    _alert_telegram "❌ DB backup FAILED on $(hostname) at $(date '+%Y-%m-%d %H:%M:%S')"
}
trap '_on_error ${LINENO}' ERR

# Dump
docker compose exec -T postgres pg_dump \
    -U "${POSTGRES_USER:-postgres}" \
    "${POSTGRES_DB:-reminders}" | gzip > "${OUT}"

# Validate: file must exist and be non-empty
if [[ ! -s "${OUT}" ]]; then
    rm -f "${OUT}"
    echo "ERROR: backup file is empty" >&2
    exit 1
fi

SIZE=$(du -h "${OUT}" | cut -f1)
echo "Backup written: ${OUT} (${SIZE})"

# Retention: delete backups older than RETENTION_DAYS
find "${BACKUP_DIR}" -name "reminders-*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete

KEPT=$(find "${BACKUP_DIR}" -name "reminders-*.sql.gz" | wc -l)
echo "Retention: kept ${KEPT} backup(s) (max ${RETENTION_DAYS} days)"
