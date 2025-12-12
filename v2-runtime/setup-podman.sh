#!/bin/bash
# =============================================================================
# Podman Rootless Setup Script
# =============================================================================
# Run this once on a fresh server to configure Podman for rootless operation.
# Usage: ./setup-podman.sh
#
# What this does:
#   1. Enables the Podman socket for your user
#   2. Enables lingering (keeps services running after logout)
#   3. Verifies the socket is working
#   4. Outputs the DOCKER_SOCK path for .env

set -e

echo "=== Podman Rootless Setup ==="
echo

# Get user info
USER_ID=$(id -u)
USER_NAME=$(whoami)
SOCKET_PATH="/run/user/${USER_ID}/podman/podman.sock"

echo "User: ${USER_NAME} (UID: ${USER_ID})"
echo "Socket path: ${SOCKET_PATH}"
echo

# Step 1: Enable lingering (requires sudo)
echo ">>> Enabling lingering for ${USER_NAME}..."
if sudo loginctl enable-linger "${USER_NAME}"; then
    echo "    Lingering enabled (services persist after logout)"
else
    echo "    WARNING: Failed to enable lingering. You may need to run:"
    echo "    sudo loginctl enable-linger ${USER_NAME}"
fi
echo

# Step 2: Enable and start the Podman socket
echo ">>> Enabling Podman socket..."
systemctl --user enable podman.socket
systemctl --user start podman.socket
echo "    Podman socket enabled and started"
echo

# Step 3: Verify the socket exists
echo ">>> Verifying socket..."
if [ -S "${SOCKET_PATH}" ]; then
    echo "    Socket exists at ${SOCKET_PATH}"
else
    echo "    ERROR: Socket not found at ${SOCKET_PATH}"
    echo "    Try: systemctl --user status podman.socket"
    exit 1
fi
echo

# Step 4: Test the socket
echo ">>> Testing Podman API..."
if curl --silent --unix-socket "${SOCKET_PATH}" http://localhost/v1.40/_ping | grep -q "OK"; then
    echo "    Podman API responding correctly"
else
    echo "    WARNING: Podman API not responding. Check: systemctl --user status podman.socket"
fi
echo

# Step 5: Check if DOCKER_SOCK needs to be set
echo "=== Configuration ==="
if [ "${USER_ID}" -eq 1000 ]; then
    echo "Your UID is 1000 - the default in docker-compose.yml will work."
    echo "No .env changes needed for DOCKER_SOCK."
else
    echo "Your UID is ${USER_ID} - add this to your .env file:"
    echo
    echo "    DOCKER_SOCK=${SOCKET_PATH}"
    echo

    # Offer to add it automatically
    read -p "Add to .env now? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if grep -q "^DOCKER_SOCK=" .env 2>/dev/null; then
            sed -i "s|^DOCKER_SOCK=.*|DOCKER_SOCK=${SOCKET_PATH}|" .env
            echo "Updated DOCKER_SOCK in .env"
        else
            echo "DOCKER_SOCK=${SOCKET_PATH}" >> .env
            echo "Added DOCKER_SOCK to .env"
        fi
    fi
fi
echo

echo "=== Setup Complete ==="
echo
echo "Next steps:"
echo "  1. Create metamcp database: podman exec kairix-postgres psql -U kairix -c 'CREATE DATABASE metamcp;'"
echo "  2. Start services: podman-compose up -d"
echo "     Or: docker compose up -d (if using podman-docker compatibility)"
echo
