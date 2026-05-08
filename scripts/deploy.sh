#!/usr/bin/env bash
# Pulls latest code and restarts the compose stack.
set -euo pipefail

cd "$(dirname "$0")/.."

git pull --ff-only
docker compose pull
docker compose build
docker compose up -d
docker compose ps
