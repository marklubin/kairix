# =============================================================================
# Stage 1: Builder - install dependencies with uv
# =============================================================================
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Enable bytecode compilation for faster startup
ENV UV_COMPILE_BYTECODE=1
# Copy mode instead of link (works across stages)
ENV UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies first (better layer caching)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Copy source and install project
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev

# =============================================================================
# Stage 2: Runtime - minimal image without uv
# =============================================================================
FROM python:3.12-slim-bookworm

# Install curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --system --gid 999 kairix \
    && useradd --system --gid 999 --uid 999 --create-home kairix

# Copy the application from builder
COPY --from=builder --chown=kairix:kairix /app /app

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Use non-root user
USER kairix
WORKDIR /app

# Default command (can be overridden in compose)
CMD ["python", "-m", "uvicorn", "kairix_agent.server.main:app", "--host", "0.0.0.0", "--port", "8000"]
