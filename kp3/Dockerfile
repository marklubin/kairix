# KP3 - Knowledge Processing Pipeline
# Runs as kp3-service by default, can override with different command
#
# Build: docker build -t kp3 .
# Run:   docker run -p 8080:8080 kp3

FROM python:3.12-slim

# Install curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Allow any kp3 command via CMD override
ENTRYPOINT ["uv", "run"]
CMD ["kp3-service"]
