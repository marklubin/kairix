#!/bin/bash
# =============================================================================
# Deploy Script - Deploys kairix to remote host
# =============================================================================
# Usage:
#   ./deploy.sh salinas              # deploy to 'salinas'
#   ./deploy.sh user@host.example    # deploy to specific user@host
#   DEPLOY_TARGET=salinas ./deploy.sh

set -euo pipefail

TARGET="${1:-${DEPLOY_TARGET:-}}"
if [[ -z "$TARGET" ]]; then
    echo "Usage: $0 <target>"
    echo "   or: DEPLOY_TARGET=<target> $0"
    exit 1
fi

echo "=== Deploying to ${TARGET} ==="

ssh "$TARGET" << 'REMOTE'
set -e
cd ~/kairix/v2-runtime

echo ">>> Pulling latest..."
git fetch origin && git reset --hard origin/main

echo ">>> Ensuring COMPOSE_PROFILES=app in .env..."
if grep -q '^COMPOSE_PROFILES=' .env 2>/dev/null; then
    sed -i 's/^COMPOSE_PROFILES=.*/COMPOSE_PROFILES=app/' .env
else
    echo 'COMPOSE_PROFILES=app' >> .env
fi

# Detect compose command
if command -v podman-compose &> /dev/null; then
    COMPOSE="podman-compose"
elif command -v docker &> /dev/null && docker compose version &> /dev/null; then
    COMPOSE="docker compose"
else
    echo "Error: Neither podman-compose nor docker compose found"
    exit 1
fi
echo ">>> Using: $COMPOSE"

echo ">>> Building images..."
$COMPOSE build

echo ">>> Running migrations..."
$COMPOSE run --rm migrate

echo ">>> Restarting services..."
$COMPOSE down --remove-orphans
$COMPOSE up -d

echo ">>> Status:"
$COMPOSE ps
REMOTE

echo
echo "=== Deployed to ${TARGET} ==="
