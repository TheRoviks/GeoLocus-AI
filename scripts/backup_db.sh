#!/usr/bin/env bash
# Dumps the postgres database from the running compose stack to ./backups/<timestamp>.sql.gz
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p backups
TS=$(date +%Y%m%d-%H%M%S)
OUT="backups/reminders-${TS}.sql.gz"

docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-postgres}" "${POSTGRES_DB:-reminders}" | gzip > "${OUT}"
echo "Backup written to ${OUT}"
