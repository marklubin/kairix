set shell := ["bash", "-cu"]


all: clean lint-unsafe check test




# Run all tests
test:
    uv run pytest tests/

# Run specific test file
test-file FILE:
    uv run pytest tests/{{FILE}}

lint:
    uv run ruff check --fix src/

lint-unsafe:
    uv run ruff check --fix --unsafe-fixes .


# Check code without fixing (for CI)
check:
    uv run ty check src/
    uv run mypy src/


install:
    uv sync


clean:
    find . -type d -name ".venv" -exec rm -rf {} +
    find . -type f -name "uv.lock" -delete
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete
    find . -type f -name "*.pyo" -delete
    find . -type f -name ".coverage" -delete
    find . -type d -name "*.egg-info" -exec rm -rf {} +
    find . -type d -name ".pytest_cache" -exec rm -rf {} +
