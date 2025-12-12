#!/bin/bash

# Install Open WebUI for Ollama

echo "Installing Open WebUI for Ollama..."

# Method 1: Docker (Recommended)
echo "Method 1: Using Docker"
echo "====================="
docker run -d -p 3000:8080 \
  --add-host=host.docker.internal:host-gateway \
  -v open-webui:/app/backend/data \
  --name open-webui \
  --restart always \
  ghcr.io/open-webui/open-webui:main

echo "Open WebUI is running at: http://localhost:3000"
echo ""

# Method 2: Using Python
echo "Method 2: Using pip (alternative)"
echo "================================"
echo "pip install open-webui"
echo "open-webui serve"