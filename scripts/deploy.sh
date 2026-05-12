#!/usr/bin/env bash
# Deploys the compose stack with automatic rollback on healthcheck failure.
# Usage: ./scripts/deploy.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${SCRIPT_DIR}/.."

BOT_IMAGE="smart-reminder-bot"
ROLLBACK_TAG="${BOT_IMAGE}:rollback"
LATEST_TAG="${BOT_IMAGE}:latest"
DEPLOY_LOG="logs/deploys.log"
HEALTHCHECK_TIMEOUT=90
HEALTHCHECK_INTERVAL=5

mkdir -p logs

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "${DEPLOY_LOG}"; }

_alert_telegram() {
    local msg="$1"
    [[ -z "${BOT_TOKEN:-}" || -z "${ALERT_CHAT_ID:-}" ]] && return 0
    curl -sS --max-time 10 -o /dev/null \
        -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${ALERT_CHAT_ID}" \
        --data-urlencode "text=${msg}" || true
}

_get_bot_container() {
    docker compose ps -q bot 2>/dev/null | head -1
}

_wait_healthy() {
    local elapsed=0
    while [[ ${elapsed} -lt ${HEALTHCHECK_TIMEOUT} ]]; do
        local container
        container=$(_get_bot_container)
        if [[ -n "${container}" ]]; then
            local status
            status=$(docker inspect --format '{{.State.Health.Status}}' "${container}" 2>/dev/null || echo "none")
            if [[ "${status}" == "healthy" ]]; then
                return 0
            fi
        fi
        sleep "${HEALTHCHECK_INTERVAL}"
        elapsed=$((elapsed + HEALTHCHECK_INTERVAL))
    done
    return 1
}

COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
log "=== Deploy start: commit=${COMMIT} ==="

# Save current image for rollback before rebuilding
if docker image inspect "${LATEST_TAG}" &>/dev/null 2>&1; then
    docker tag "${LATEST_TAG}" "${ROLLBACK_TAG}"
    log "Saved rollback image: ${ROLLBACK_TAG}"
else
    log "No previous image to save for rollback"
fi

git pull --ff-only
log "Pulled latest code"

docker compose build --no-cache
# Tag the freshly built image so rollback can reference it later
BUILT_ID=$(docker compose images -q bot 2>/dev/null | head -1 || true)
[[ -n "${BUILT_ID}" ]] && docker tag "${BUILT_ID}" "${LATEST_TAG}" || true

log "Starting containers..."
docker compose up -d

log "Waiting for healthcheck (timeout=${HEALTHCHECK_TIMEOUT}s)..."
if _wait_healthy; then
    log "Healthcheck OK ✅  commit=${COMMIT}"
    _alert_telegram "✅ Deploy OK — commit=${COMMIT}"
    docker compose ps
else
    log "Healthcheck FAILED ⚠️  Rolling back..."
    docker compose down

    if docker image inspect "${ROLLBACK_TAG}" &>/dev/null 2>&1; then
        docker tag "${ROLLBACK_TAG}" "${LATEST_TAG}"
        docker compose up -d
        log "Rolled back to previous image"
        _alert_telegram "⚠️ Deploy FAILED (commit=${COMMIT}) — rolled back to previous build"
    else
        log "No rollback image available — stack is down!"
        _alert_telegram "🔴 Deploy FAILED (commit=${COMMIT}) — NO rollback available, stack is DOWN"
    fi
    exit 1
fi
