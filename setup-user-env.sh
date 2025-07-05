#!/bin/bash

# Kairix User Environment Setup Script
# Creates isolated user environments with symlinked source code

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Base directories
KAIRIX_ROOT=$(cd "$(dirname "$0")" && pwd)
KAIRIX_ENV_BASE="/kairix-env"

echo -e "${BLUE}=== Kairix User Environment Setup ===${NC}"

# Get user input - use -r to prevent backslash interpretation
read -r -p "Enter username: " USERNAME
read -r -p "Enter port number: " PORT

# For API keys, use different approach to handle special characters
echo -n "Enter API key: "
read -r API_KEY

echo -n "Enter OpenAI API key (press enter to skip): "
read -r OPENAI_API_KEY

read -r -p "Enter assistant name (default: Kairix Assistant): " ASSISTANT_NAME
ASSISTANT_NAME=${ASSISTANT_NAME:-"Kairix Assistant"}

read -r -p "Enter inference provider (default: openai): " INFERENCE_PROVIDER
INFERENCE_PROVIDER=${INFERENCE_PROVIDER:-"openai"}

# Create user environment directory
USER_ENV_DIR="${KAIRIX_ENV_BASE}/${USERNAME}"
USER_KAIRIX_DIR="${USER_ENV_DIR}/kairix"

echo -e "\n${BLUE}Creating environment for user: ${USERNAME}${NC}"
echo -e "Environment directory: ${USER_ENV_DIR}"

# Create directory structure
mkdir -p "${USER_ENV_DIR}"
mkdir -p "${USER_KAIRIX_DIR}"

# Create symlinks to source directories
echo -e "\n${BLUE}Creating symlinks to source code...${NC}"

# Symlink all kairix-* directories
for dir in "${KAIRIX_ROOT}"/kairix-*; do
    if [ -d "$dir" ]; then
        basename=$(basename "$dir")
        ln -sfn "$dir" "${USER_KAIRIX_DIR}/${basename}"
        echo -e "  Linked: ${basename}"
    fi
done

# Symlink other necessary files
ln -sfn "${KAIRIX_ROOT}/mypy.ini" "${USER_KAIRIX_DIR}/mypy.ini"
ln -sfn "${KAIRIX_ROOT}/Justfile" "${USER_KAIRIX_DIR}/Justfile"

# Create user-specific directories (not symlinked)
mkdir -p "${USER_ENV_DIR}/data"
mkdir -p "${USER_ENV_DIR}/logs"
mkdir -p "${USER_ENV_DIR}/cache"

# Generate .env file
ENV_FILE="${USER_ENV_DIR}/.env"
echo -e "\n${BLUE}Generating environment configuration...${NC}"

cat > "${ENV_FILE}" << EOF
# Kairix User Environment Configuration
# Generated on: $(date)
# User: ${USERNAME}

# Basic Configuration
USERNAME=${USERNAME}
PORT=${PORT}
API_KEY=${API_KEY}
USER_ENV_DIR=${USER_ENV_DIR}

# Service URLs
BASE_URL=http://localhost:${PORT}
API_URL=http://localhost:${PORT}/api

# Assistant Configuration
ASSISTANT_NAME="${ASSISTANT_NAME}"
INFERENCE_PROVIDER=${INFERENCE_PROVIDER}

# API Keys
OPENAI_API_KEY=${OPENAI_API_KEY}

# Neo4j Configuration (temporary until removed)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Directory Paths
DATA_DIR=${USER_ENV_DIR}/data
LOG_DIR=${USER_ENV_DIR}/logs
CACHE_DIR=${USER_ENV_DIR}/cache

# Python Environment
SENTENCE_TRANSFORMERS_HOME=${USER_ENV_DIR}/cache
UV_CACHE_DIR=${USER_ENV_DIR}/cache/uv

# Service State
SERVICE_STATE=Created
EOF

echo -e "  Created: ${ENV_FILE}"

# Create state file
STATE_FILE="${USER_ENV_DIR}/.state"
echo "Created" > "${STATE_FILE}"

# Create run script for this user
RUN_SCRIPT="${USER_ENV_DIR}/run.sh"
cat > "${RUN_SCRIPT}" << 'EOF'
#!/bin/bash

# Load environment
set -a
source "$(dirname "$0")/.env"
set +a

cd "${USER_ENV_DIR}/kairix"

case "$1" in
    start)
        echo "Starting services for ${USERNAME}..."
        echo "InProgress" > "${USER_ENV_DIR}/.state"
        
        # Start the API server
        cd kairix-apps
        uv run uvicorn kairix_apps.server:app --host 0.0.0.0 --port ${PORT} &
        echo $! > "${USER_ENV_DIR}/api.pid"
        
        echo "Completed" > "${USER_ENV_DIR}/.state"
        echo "Services started on port ${PORT}"
        ;;
        
    stop)
        echo "Stopping services for ${USERNAME}..."
        if [ -f "${USER_ENV_DIR}/api.pid" ]; then
            kill $(cat "${USER_ENV_DIR}/api.pid") 2>/dev/null
            rm "${USER_ENV_DIR}/api.pid"
        fi
        echo "Created" > "${USER_ENV_DIR}/.state"
        ;;
        
    status)
        STATE=$(cat "${USER_ENV_DIR}/.state")
        echo "Environment: ${USERNAME}"
        echo "State: ${STATE}"
        echo "Port: ${PORT}"
        if [ -f "${USER_ENV_DIR}/api.pid" ]; then
            PID=$(cat "${USER_ENV_DIR}/api.pid")
            if ps -p $PID > /dev/null; then
                echo "API Server: Running (PID: $PID)"
            else
                echo "API Server: Stopped"
            fi
        else
            echo "API Server: Not running"
        fi
        ;;
        
    *)
        echo "Usage: $0 {start|stop|status}"
        exit 1
        ;;
esac
EOF

chmod +x "${RUN_SCRIPT}"

echo -e "\n${GREEN}✓ Environment setup complete!${NC}"
echo -e "\nEnvironment details:"
echo -e "  Username: ${USERNAME}"
echo -e "  Port: ${PORT}"
echo -e "  Directory: ${USER_ENV_DIR}"
echo -e "  Config: ${ENV_FILE}"
echo -e "  Run script: ${RUN_SCRIPT}"
echo -e "\nTo manage the environment:"
echo -e "  ${RUN_SCRIPT} start   - Start services"
echo -e "  ${RUN_SCRIPT} stop    - Stop services"
echo -e "  ${RUN_SCRIPT} status  - Check status"
echo -e "\nTo modify configuration, edit: ${ENV_FILE}"