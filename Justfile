all: clean install fix typecheck mypy test

# Install dependencies using uv
install:
    uv sync

# Run all tests
test:
    uv run pytest tests/

# Run specific test file
test-file FILE:
    uv run pytest tests/{{FILE}}

# Run linting with ruff
fix:
    uv run ruff check --fix .

# Check code without fixing (for CI)
check:
    uv run ruff check .
    cd src && uv run mypy -p kairix_engine --warn-unused-ignores
    uv run mypy tests/ --warn-unused-ignores
    uv run python scripts/async_test_validator.py --src src --tests tests

# Run linting with unsafe fixes
fix-unsafe:
    uv run ruff check --fix --unsafe-fixes .

# Run type checking with ty and async test validation
typecheck:
    uv run ty check src/ tests/
    @echo "Checking async method test coverage..."
    uv run python scripts/async_test_validator.py --src src --tests tests

# Run async test validation only
async-check:
    uv run python scripts/async_test_validator.py --src src --tests tests

# Run async test validation in strict mode (requires quality tests)
async-check-strict:
    uv run python scripts/async_test_validator.py --src src --tests tests --strict --verbose

# Run mypy type checking with async checking
mypy:
    uv run mypy src/kairix_engine --warn-unused-ignores
    uv run mypy tests/ --warn-unused-ignores

# Clean Python cache files
clean:
    find . -type d -name ".venv" -exec rm -rf {} +
    find . -type f -name "uv.lock" -delete
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete
    find . -type f -name "*.pyo" -delete
    find . -type f -name ".coverage" -delete
    find . -type d -name "*.egg-info" -exec rm -rf {} +
    find . -type d -name ".pytest_cache" -exec rm -rf {} +


# Show project structure
tree:
    tree -I '__pycache__|*.pyc|.git'

clear-source-documents:
      echo "MATCH (n:SourceDocument) DETACH DELETE n" | cypher-shell -a bolt://localhost:7687 -u neo4j -p password

clear-agents:
      echo "MATCH (n:Agent) DETACH DELETE n" | cypher-shell -a bolt://localhost:7687 -u neo4j -p password

clear-memory-shards:
      echo "MATCH (n:MemoryShard) DETACH DELETE n" | cypher-shell -a bolt://localhost:7687 -u neo4j -p password

clear-summaries:
      echo "MATCH (n:Summary) DETACH DELETE n" | cypher-shell -a bolt://localhost:7687 -u neo4j -p password

clear-embeddings:
      echo "MATCH (n:Embedding) DETACH DELETE n" | cypher-shell -a bolt://localhost:7687 -u neo4j -p password

clear-neo4j: clear-embeddings clear-summaries clear-memory-shards clear-agents clear-source-documents
      echo "Neo4j cleared!"

mac-env:
    pwd && cp env/mac.env .env
default-env:
    cp env/default.env .env
