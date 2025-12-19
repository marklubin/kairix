#!/usr/bin/env bash
# =============================================================================
# run-job.sh - Run kp3 commands in an ephemeral container
# =============================================================================
# Usage:
#   ./scripts/run-job.sh <kp3-command> [args...]
#
# Examples:
#   ./scripts/run-job.sh passage ls
#   ./scripts/run-job.sh run create "SELECT ..." -p embedding
#   ./scripts/run-job.sh sql "SELECT COUNT(*) FROM passages"
#   ./scripts/run-job.sh importer kairix /data/mark.db
#
# Environment:
#   KP3_DATABASE_URL - Database connection string (default: uses kairix-postgres)
#   KP3_OLLAMA_HOST  - Ollama server URL (default: http://host.containers.internal:11434)
#   ANTHROPIC_API_KEY - Required for LLM processing jobs
#
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Defaults
KP3_DATABASE_URL="${KP3_DATABASE_URL:-postgresql+asyncpg://kp3:kp3@kairix-postgres:5432/kp3}"
KP3_OLLAMA_HOST="${KP3_OLLAMA_HOST:-http://host.containers.internal:11434}"
ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"

# Check if image exists, build if not
IMAGE_NAME="kp3:latest"
if ! podman image exists "$IMAGE_NAME" 2>/dev/null; then
    echo "Building kp3 image..."
    podman build -t "$IMAGE_NAME" "$PROJECT_DIR"
fi

# Build volume mounts for data files if any args look like paths
VOLUME_MOUNTS=()
for arg in "$@"; do
    if [[ -f "$arg" ]]; then
        # Mount the file into /data with same basename
        VOLUME_MOUNTS+=("-v" "$arg:/data/$(basename "$arg"):ro")
    fi
done

# Run ephemeral container
exec podman run --rm \
    --network v2-runtime_kairix-net \
    --add-host host.containers.internal:host-gateway \
    -e "KP3_DATABASE_URL=$KP3_DATABASE_URL" \
    -e "KP3_OLLAMA_HOST=$KP3_OLLAMA_HOST" \
    -e "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY" \
    "${VOLUME_MOUNTS[@]}" \
    "$IMAGE_NAME" "$@"
