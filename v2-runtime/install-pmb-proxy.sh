#!/bin/bash
set -e

# Check for root privileges
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use sudo)"
   exit 1
fi

# Check socat is installed
if ! command -v socat &> /dev/null; then
    echo "socat is not installed. Please install it first."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/pmb-proxy.service"

if [[ ! -f "$SERVICE_FILE" ]]; then
    echo "Service file not found: $SERVICE_FILE"
    exit 1
fi

# Copy service file
cp "$SERVICE_FILE" /etc/systemd/system/pmb-proxy.service
echo "Copied service file to /etc/systemd/system/"

# Reload systemd
systemctl daemon-reload
echo "Reloaded systemd daemon"

# Enable and start service
systemctl enable pmb-proxy.service
echo "Enabled pmb-proxy.service"

systemctl start pmb-proxy.service
echo "Started pmb-proxy.service"

# Show status
systemctl status pmb-proxy.service --no-pager
