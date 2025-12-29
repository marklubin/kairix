# =============================================================================
# Stage 1: Builder - install dependencies with uv
# =============================================================================
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Enable bytecode compilation for faster startup
ENV UV_COMPILE_BYTECODE=1
# Copy mode instead of link (works across stages)
ENV UV_LINK_MODE=copy

WORKDIR /app

# Copy kairix-common first (it's a local dependency)
COPY kairix-common/ /kairix-common/

# Copy dependency files (changes here invalidate cache)
COPY v2-runtime/uv.lock v2-runtime/pyproject.toml ./

# Install dependencies (cached unless uv.lock/pyproject.toml change)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

# Copy source and install project
COPY v2-runtime/src/ ./src/
COPY v2-runtime/alembic/ ./alembic/
COPY v2-runtime/alembic.ini ./

RUN --mount=type=cache,target=/root/.cache/uv \
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
# Also copy kairix-common for runtime imports
COPY --from=builder --chown=kairix:kairix /kairix-common /kairix-common

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Use non-root user
USER kairix
WORKDIR /app

# Default command (can be overridden in compose)
CMD ["python", "-m", "uvicorn", "kairix_agent.server.main:app", "--host", "0.0.0.0", "--port", "8000"]
