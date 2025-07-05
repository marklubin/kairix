#!/bin/bash

# Deploy script for Kairix multi-tenant instances
# Usage: ./deploy-user.sh <user_id> [openai_api_key]

set -e

# Check if user ID is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <user_id> [openai_api_key]"
    echo "Example: $0 alice sk-..."
    exit 1
fi

USER_ID=$1
OPENAI_API_KEY=${2:-$OPENAI_API_KEY}

# Check if OpenAI API key is available
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: OpenAI API key not provided and OPENAI_API_KEY environment variable not set"
    exit 1
fi

# Generate secure random keys
USER_API_KEY=$(openssl rand -hex 32)
NEO4J_PASSWORD=$(openssl rand -hex 16)

# Create user environment file
ENV_FILE=".env.${USER_ID}"
cat > $ENV_FILE <<EOF
USER_ID=${USER_ID}
USER_API_KEY=${USER_API_KEY}
NEO4J_PASSWORD=${NEO4J_PASSWORD}
OPENAI_API_KEY=${OPENAI_API_KEY}
EOF

echo "Created environment file: $ENV_FILE"

# Create network if it doesn't exist
docker network create kairix-network 2>/dev/null || true

# Deploy the user stack
echo "Deploying Kairix instance for user: ${USER_ID}"
docker compose -f docker-compose.user.yml \
  --project-name "kairix-${USER_ID}" \
  --env-file "$ENV_FILE" \
  up -d

# Wait for services to be healthy
echo "Waiting for services to start..."
sleep 10

# Check service status
echo ""
echo "Checking service status..."
docker compose -p "kairix-${USER_ID}" ps

# Display access information
echo ""
echo "=========================================="
echo "Kairix instance deployed successfully!"
echo "=========================================="
echo "User ID: ${USER_ID}"
echo "URL: http://${USER_ID}.localhost"
echo "API URL: http://${USER_ID}.localhost/api"
echo "API Key: ${USER_API_KEY}"
echo "Neo4j Password: ${NEO4J_PASSWORD}"
echo ""
echo "Environment file saved to: $ENV_FILE"
echo "=========================================="

# Save deployment info
DEPLOYMENTS_DIR="deployments"
mkdir -p $DEPLOYMENTS_DIR
cat > "$DEPLOYMENTS_DIR/${USER_ID}.json" <<EOF
{
  "user_id": "${USER_ID}",
  "url": "http://${USER_ID}.localhost",
  "api_url": "http://${USER_ID}.localhost/api",
  "api_key": "${USER_API_KEY}",
  "deployed_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF

echo "Deployment info saved to: $DEPLOYMENTS_DIR/${USER_ID}.json"