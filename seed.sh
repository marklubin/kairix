#!/bin/bash
# Kairix seed script - installs just and starts provisioning

set -e

echo "Starting Kairix provisioning..."

# Install just
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin

# Clone repository if not already present
if [ ! -d "kairix" ]; then
    git clone https://github.com/marklubin/kairix.git
fi

cd kairix

# Run the full provisioning
just provision

echo "Provisioning complete! Run 'just status' to check service status."