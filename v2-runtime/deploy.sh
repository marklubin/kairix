#!/bin/bash
# =============================================================================
# Deploy Script
# =============================================================================
# Deploys agent-server to a remote host via SSH.
#
# Usage:
#   ./deploy.sh                      # uses DEPLOY_TARGET env var
#   ./deploy.sh salinas              # deploy to 'salinas'
#   ./deploy.sh user@host.example    # deploy to specific user@host
#
# Environment variables:
#   DEPLOY_TARGET   - Default SSH target (e.g., "salinas" or "user@host")
#   DEPLOY_PATH     - Remote path (default: ~/agent-server)
#   GITHUB_REPO     - Repository URL (default: from local git remote)

set -e

# =============================================================================
# Configuration
# =============================================================================

# Target: CLI arg > env var > error
TARGET="${1:-${DEPLOY_TARGET:-}}"
if [ -z "$TARGET" ]; then
    echo "Error: No deploy target specified."
    echo "Usage: ./deploy.sh <target>"
    echo "   or: DEPLOY_TARGET=<target> ./deploy.sh"
    exit 1
fi

# Remote path
REMOTE_PATH="${DEPLOY_PATH:-~/agent-server}"

# GitHub repo: env var > detect from local git
if [ -z "$GITHUB_REPO" ]; then
    GITHUB_REPO=$(git remote get-url origin 2>/dev/null || echo "")
fi

if [ -z "$GITHUB_REPO" ]; then
    echo "Error: Could not detect GitHub repo. Set GITHUB_REPO env var."
    exit 1
fi

# =============================================================================
# Deploy
# =============================================================================

echo "=== Deploying to ${TARGET} ==="
echo "Repository: ${GITHUB_REPO}"
echo "Remote path: ${REMOTE_PATH}"
echo

# Build the remote commands
read -r -d '' REMOTE_SCRIPT << 'EOF' || true
set -e

REMOTE_PATH="__REMOTE_PATH__"
GITHUB_REPO="__GITHUB_REPO__"

# Expand ~ to $HOME (tilde doesn't expand inside quotes)
REMOTE_PATH="${REMOTE_PATH/#\~/$HOME}"

# Clone if not present
if [ ! -d "$REMOTE_PATH" ]; then
    echo ">>> Cloning repository..."
    git clone "$GITHUB_REPO" "$REMOTE_PATH"
    cd "$REMOTE_PATH"
else
    echo ">>> Pulling latest changes..."
    cd "$REMOTE_PATH"
    git fetch origin
    git reset --hard origin/main  # or origin/master if that's your branch
fi

# Show current commit
echo ">>> Current commit:"
git log -1 --oneline

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

# Compose files for production
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"

# Project name for network naming
PROJECT_NAME=$(basename "$REMOTE_PATH")

# Pull latest dependency images
echo ">>> Pulling dependency images..."
$COMPOSE -f docker-compose.yml pull

# Build application images (while old containers still running)
echo ">>> Building application images..."
$COMPOSE $COMPOSE_FILES build

# =============================================================================
# Clean environment flip - stop everything, then bring up fresh
# =============================================================================

echo ">>> Stopping all services..."
$COMPOSE $COMPOSE_FILES down --remove-orphans 2>/dev/null || true

# Start just postgres and redis first (need postgres for migrations)
echo ">>> Starting databases..."
$COMPOSE $COMPOSE_FILES up -d postgres redis

# Wait for postgres to be healthy
echo ">>> Waiting for postgres to be healthy..."
for i in {1..30}; do
    if $COMPOSE $COMPOSE_FILES exec -T postgres pg_isready -U kairix &> /dev/null; then
        echo "    Postgres is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "Error: Postgres failed to become healthy"
        exit 1
    fi
    echo "    Waiting... ($i/30)"
    sleep 2
done

# Run database migrations
echo ">>> Running database migrations..."
if command -v podman &> /dev/null; then
    # Use podman directly - more reliable than podman-compose run
    # Network name is prefixed with project name by podman-compose
    podman run --rm --network "${PROJECT_NAME}_kairix-net" \
        -e DATABASE_URL="postgresql+asyncpg://kairix:${POSTGRES_PASSWORD:-kairix}@kairix-postgres:5432/kairix" \
        kairix-server:latest python -m alembic upgrade head
else
    # Docker compose run works fine
    $COMPOSE $COMPOSE_FILES run --rm --no-deps \
        -e DATABASE_URL="postgresql+asyncpg://kairix:${POSTGRES_PASSWORD:-kairix}@kairix-postgres:5432/kairix" \
        kairix-server python -m alembic upgrade head
fi
if [ $? -ne 0 ]; then
    echo "Error: Database migrations failed!"
    exit 1
fi
echo ">>> Migrations completed successfully"

# Bring up all services fresh
echo ">>> Starting all services..."
$COMPOSE $COMPOSE_FILES up -d

# Wait a moment for services to initialize
sleep 5

# Show status
echo ">>> Container status:"
if command -v podman &> /dev/null; then
    podman ps --format "table {{.Names}}\t{{.Status}}" | grep -E "kairix|letta|redis|postgres|dozzle|metamcp" || true
else
    $COMPOSE $COMPOSE_FILES ps
fi

echo
echo "=== Deploy complete ==="
EOF

# Substitute variables into the script
REMOTE_SCRIPT="${REMOTE_SCRIPT//__REMOTE_PATH__/$REMOTE_PATH}"
REMOTE_SCRIPT="${REMOTE_SCRIPT//__GITHUB_REPO__/$GITHUB_REPO}"

# Execute on remote
echo ">>> Connecting to ${TARGET}..."
ssh "$TARGET" "$REMOTE_SCRIPT"

echo
echo "Done! Deployed to ${TARGET}:${REMOTE_PATH}"
