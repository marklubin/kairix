all: clean lint-unsafe check test


clean-env-links:
    rm -rf envs
    rm -rf kairix-apps/.envs
    rm -rf kairix-core/.envs
    rm -rf kairix-offline/.envs
    rm -rf kairix-website/.envs

create-env-links:
    mkdir envs
    ln -s $HOME/kairix/envs kairix-apps/.envs
    ln -s $HOME/kairix/envs kairix-core/.envs
    ln -s $HOME/kairix/envs kairix-offline/.envs
    ln -s $HOME/kairix/envs kairix-website/.envs


run-user USER CMD *ARGS:
    dotenv -e .envs/{{USER}}.env uv run {{CMD}} {{ARGS}}

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
    rm -rf envs/{{USER}}.env
    cp .env envs/{{USER}}.env
    rm -rf .env

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

