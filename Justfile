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

clean:
    find . -type d -name ".venv" -exec rm -rf {} +
    find . -type f -name "uv.lock" -delete
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete
    find . -type f -name "*.pyo" -delete
    find . -type f -name ".coverage" -delete
    find . -type d -name "*.egg-info" -exec rm -rf {} +
    find . -type d -name ".pytest_cache" -exec rm -rf {} +

# Complete system provision from scratch
provision: install-deps install-doppler install-magg install-sqlite-vss sys-create setup-caddy setup-services
    @echo "System provisioned successfully!"

# Install system dependencies
install-deps:
    # Install uv
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Install just (if not already installed via seed.sh)
    which just || (curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin)
    # Install Caddy
    sudo apt update && sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
    sudo apt update && sudo apt install -y caddy

# Install Doppler CLI
install-doppler:
    curl -Ls --tlsv1.2 --proto "=https" --retry 3 https://cli.doppler.com/install.sh | sudo sh
    doppler login

# Install MCP Aggregator
install-magg:
    cargo install magg
    mkdir -p ~/.config/magg
    echo '{}' > ~/.config/magg/config.json

# Install SQLite VSS extension
install-sqlite-vss:
    # Download and install sqlite-vss
    mkdir -p ~/.local/lib
    curl -L https://github.com/asg017/sqlite-vss/releases/latest/download/sqlite-vss-linux-x86_64.zip -o /tmp/sqlite-vss.zip
    unzip /tmp/sqlite-vss.zip -d ~/.local/lib/
    rm /tmp/sqlite-vss.zip
    echo 'export LD_LIBRARY_PATH=$HOME/.local/lib:$LD_LIBRARY_PATH' >> ~/.bashrc

sys-create:
  sudo useradd -m -s /usr/sbin/nologin kairix
  sudo mkdir -p "/home/kairix"
  sudo chown -R kairix:kairix "/home/kairix"
  sudo mkdir -p "/var/kairix
  sudo chown -R kairix:kairix "/var/kairix"

setup-caddy:
    sudo cp Caddyfile /etc/caddy/Caddyfile
    sudo systemctl reload caddy

# Setup and start services
setup-services:
    sudo systemctl daemon-reload
    sudo systemctl enable kairix-server kairix-website
    sudo systemctl start kairix-server kairix-website

# Start services (development)
dev-start:
    just run-server dev &
    just run-website dev &

# Stop services
stop-services:
    sudo systemctl stop kairix-server kairix-website

# Check service status
status:
    sudo systemctl status kairix-server kairix-website

[working-directory: 'kairix-core/scripts']
run-script SCRIPT:
    uv run python {{SCRIPT}}

[working-directory: 'kairix-apps']
run-server CONFIG:
    doppler run -c {{CONFIG}} -- uv run python src/kairix_apps/server.py

[working-directory: 'kairix-website']
run-website CONFIG:
    doppler run -c {{CONFIG}} -- npm run serve

copy-db:
  scp -r .sqlite coalinga:/home/kairix/kairix/
