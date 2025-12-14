# KP3 Project Instructions

## Development Workflow

**For each new piece of code, follow this loop:**
1. Implement the code
2. Write tests for it
3. Run tests to verify
4. Move to next piece

Do not batch implementations - test each piece as you go.

## Commands

```bash
# Run tests
uv run pytest

# Run specific test file
uv run pytest tests/test_passages.py

# Run with output
uv run pytest -v

# Type check
uv run pyright src/kp3/

# Lint
uv run ruff check src/kp3/

# Format
uv run ruff format src/kp3/

# Start database
podman-compose up -d

# Stop database
podman-compose down

# Run migrations
uv run alembic upgrade head
```

## Project Structure

- `src/kp3/db/` - SQLAlchemy models and engine
- `src/kp3/services/` - Business logic (passages, derivations, runs)
- `src/kp3/processors/` - Processing logic (LLM, embeddings)
- `src/kp3/importers/` - Data import (kairix sqlite)
- `tests/` - Tests with testcontainers for Postgres

## Testing

Tests use testcontainers to spin up a fresh Postgres+pgvector instance. Each test gets a session that rolls back after completion.
