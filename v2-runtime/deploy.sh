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

echo ">>> Stopping existing services..."
./kx down

echo ">>> Building images..."
./kx build

echo ">>> Starting infrastructure..."
./kx dev

echo ">>> Waiting for postgres..."
sleep 10

echo ">>> Running migrations..."
./kx migrate

echo ">>> Starting app services..."
./kx up

REMOTE

echo
echo "=== Deployed to ${TARGET} ==="
