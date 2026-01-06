#!/bin/bash
# Setup NVIDIA GPU passthrough for podman containers
# Run this on salinas to enable GPU access for kp3-service

set -e

echo "=== Setting up NVIDIA Container Toolkit for Podman ==="

# Detect package manager
if command -v apt-get &> /dev/null; then
    PKG_MGR="apt"
elif command -v dnf &> /dev/null; then
    PKG_MGR="dnf"
else
    echo "Error: Unsupported package manager. Need apt or dnf."
    exit 1
fi

# Check if nvidia-smi works
if ! command -v nvidia-smi &> /dev/null; then
    echo "Error: nvidia-smi not found. Install NVIDIA drivers first."
    exit 1
fi

echo "GPU detected:"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

# Install nvidia-container-toolkit
echo ""
echo "=== Installing nvidia-container-toolkit ==="

if [ "$PKG_MGR" = "apt" ]; then
    # Ubuntu/Debian/Pop!_OS
    if [ ! -f /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg ]; then
        curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
            sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    fi

    if [ ! -f /etc/apt/sources.list.d/nvidia-container-toolkit.list ]; then
        curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
            sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
            sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
        sudo apt-get update
    fi

    sudo apt-get install -y nvidia-container-toolkit
else
    # Fedora/RHEL
    if [ ! -f /etc/yum.repos.d/nvidia-container-toolkit.repo ]; then
        curl -s -L https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo | \
            sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo
    fi

    sudo dnf install -y nvidia-container-toolkit
fi

# Generate CDI spec
echo ""
echo "=== Generating CDI spec for Podman ==="

sudo mkdir -p /etc/cdi
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml

echo ""
echo "=== Verifying CDI configuration ==="

if [ -f /etc/cdi/nvidia.yaml ]; then
    echo "CDI spec created: /etc/cdi/nvidia.yaml"
    echo "Devices available:"
    grep -E "^\s+name:" /etc/cdi/nvidia.yaml | head -5
else
    echo "Error: CDI spec not created"
    exit 1
fi

# Test GPU access in podman
echo ""
echo "=== Testing GPU access in Podman ==="

if podman run --rm --device nvidia.com/gpu=all nvidia/cuda:12.0-base nvidia-smi > /dev/null 2>&1; then
    echo "GPU access verified in containers"
else
    echo "Warning: Could not verify GPU access. You may need to restart podman or the system."
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "GPU passthrough is now configured. Deploy with:"
echo "  cd ~/kairix/v2-runtime && ./deploy.sh salinas"
echo ""
echo "The kp3-service will use GPU 1 (CUDA_VISIBLE_DEVICES=1)"
