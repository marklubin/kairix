#!/usr/bin/env bash
# Deploy KP3 to oxnard
set -euo pipefail

HOST="oxnard"
REMOTE_DIR="~/kairix"

echo "=== Deploying KP3 to $HOST ==="

# Check if .env exists locally with required keys
if [[ ! -f "$(dirname "$0")/.env" ]]; then
    echo "ERROR: kp3/.env file not found"
    echo "Create it with: KP3_OPENAI_API_KEY=sk-..."
    exit 1
fi

if ! grep -q "KP3_OPENAI_API_KEY" "$(dirname "$0")/.env"; then
    echo "ERROR: KP3_OPENAI_API_KEY not found in .env"
    exit 1
fi

# Ensure remote directory exists and clone/update repo
echo ">>> Setting up remote repository..."
ssh "$HOST" "mkdir -p ~/kairix"

# Check if repo exists
if ssh "$HOST" "test -d $REMOTE_DIR/.git"; then
    echo ">>> Pulling latest changes..."
    ssh "$HOST" "cd $REMOTE_DIR && git fetch origin && git reset --hard origin/main"
else
    echo ">>> Cloning repository..."
    ssh "$HOST" "git clone https://github.com/kairix-ai/kairix.git $REMOTE_DIR"
fi

# Copy .env file
echo ">>> Copying .env file..."
scp "$(dirname "$0")/.env" "$HOST:$REMOTE_DIR/kp3/.env"

# Build and deploy
echo ">>> Building and starting services..."
ssh "$HOST" "cd $REMOTE_DIR/kp3 && docker compose -f compose.standalone.yml down || true"
ssh "$HOST" "cd $REMOTE_DIR/kp3 && docker compose -f compose.standalone.yml build"
ssh "$HOST" "cd $REMOTE_DIR/kp3 && docker compose -f compose.standalone.yml up -d"

# Wait for postgres to be ready
echo ">>> Waiting for postgres..."
ssh "$HOST" "cd $REMOTE_DIR/kp3 && docker compose -f compose.standalone.yml exec -T postgres pg_isready -U kp3 -d kp3" || sleep 5

# Run migrations
echo ">>> Running migrations..."
ssh "$HOST" "cd $REMOTE_DIR/kp3 && docker compose -f compose.standalone.yml exec -T kp3-service uv run alembic upgrade head"

# Health check
echo ">>> Checking service health..."
sleep 3
ssh "$HOST" "curl -sf http://localhost:8080/health" && echo " OK" || echo " FAILED"

echo ""
echo "=== Deployment complete ==="
echo "KP3 API: http://$HOST:8080"
echo "Health:  http://$HOST:8080/health"
echo "Search:  curl -H 'X-Agent-ID: test' 'http://$HOST:8080/passages/search?query=hello'"
