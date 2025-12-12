#!/bin/bash
# Deployment script for coalinga server

set -e  # Exit on error

echo "=== Deploying Kairix Server to Coalinga ==="
echo ""

# Pull latest changes
echo "1. Pulling latest changes..."
git pull origin feature/diskcache-notebook-viewer

# Install/update dependencies
echo ""
echo "2. Updating dependencies..."
cd kairix-core
uv sync
cd ../kairix-apps
uv sync
cd ..

# Restart the server
echo ""
echo "3. Restarting kairix-server-mark service..."
sudo systemctl restart kairix-server-mark

# Wait a moment for startup
echo ""
echo "4. Waiting for server to start..."
sleep 5

# Check status
echo ""
echo "5. Checking service status..."
sudo systemctl status kairix-server-mark --no-pager -l

# Check if server is responding
echo ""
echo "6. Testing API endpoint..."
curl -s http://localhost:8000/health || echo "Health check failed"

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "View logs with: sudo journalctl -u kairix-server-mark -f"
echo "Check status with: sudo systemctl status kairix-server-mark"
