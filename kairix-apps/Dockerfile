# Kairix Apps API Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Copy kairix-core dependency
COPY kairix-core /kairix-core

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY kairix-apps ./kairix-apps

# Create cache directory for sentence transformers
RUN mkdir -p /app/.cache

# Expose port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "uvicorn", "kairix_apps.server:app", "--host", "0.0.0.0", "--port", "8000"]