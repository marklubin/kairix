# KP3 - Knowledge Processing Pipeline
# Ephemeral container for running processing jobs

FROM python:3.12-slim

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

# Default entrypoint runs kp3 CLI
ENTRYPOINT ["uv", "run", "kp3"]
CMD ["--help"]
