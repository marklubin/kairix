# KP3 - Knowledge Processing Pipeline
# Runs as kp3-service by default, can override with different command
# Build context: parent directory (kairix/)

FROM python:3.12-slim

# Install curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy kairix-common first (it's a local dependency)
COPY kairix-common/ /kairix-common/

# Copy project files (from kp3/ subdirectory of context)
COPY kp3/pyproject.toml kp3/uv.lock kp3/README.md ./
COPY kp3/src/ ./src/
COPY kp3/alembic/ ./alembic/
COPY kp3/alembic.ini ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Allow any kp3 command via CMD override
ENTRYPOINT ["uv", "run"]
CMD ["kp3-service"]
