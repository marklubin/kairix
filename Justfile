all: clean lint-unsafe check test
set-env PLATFORM INF USER:
    rm -f .env 
    touch .env
    echo "#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~" >> .env
    echo "# Auto-generated Kairix Environment File" >> .env
    echo "#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~" >> .env

    echo "#~~~~~~~~~~~~~~~~~~[Base Config]~~~~~~~~~~~~~~~~~~~~" >> .env
    cat $HOME/kairix/environments/base.env >> .env

    echo "#~~~~~~~~~~~~~~~~~~[Platform Config]~~~~~~~~~~~~~~~~~~~~" >> .env
    cat $HOME/kairix/environments/platform/{{PLATFORM}}.env >> .env

    echo "#~~~~~~~~~~~~~~~~~~[Inference Config]~~~~~~~~~~~~~~~~~~~~" >> .env
    cat $HOME/kairix/environments/inference/{{INF}}.env  >> .env

    echo "#~~~~~~~~~~~~~~~~~~[User Config]~~~~~~~~~~~~~~~~~~~~" >> .env
        cat $HOME/kairix/environments/users/{{USER}}.env  >> .env

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


start_db:
    docker compose up -d

install:
    uv sync
    uv run python -c "from kairix_core.runtime.neo4j import Neo4jRuntime; Neo4jRuntime().install()"


clean:
    find . -type d -name ".venv" -exec rm -rf {} +
    find . -type f -name "uv.lock" -delete
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete
    find . -type f -name "*.pyo" -delete
    find . -type f -name ".coverage" -delete
    find . -type d -name "*.egg-info" -exec rm -rf {} +
    find . -type d -name ".pytest_cache" -exec rm -rf {} +


tree:
    tree -I '__pycache__|*.pyc|.git'

clear-db-label LABEL:
      echo "MATCH (n:{{LABEL}}) DETACH DELETE n" | cypher-shell -a bolt://localhost:7687 -u neo4j -p password
