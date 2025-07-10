# Kairix CLI

Command-line interface for managing Kairix system infrastructure and users.

## Installation

```bash
uv sync
```

## Usage

```bash
# System management commands
kairix system provision    # Provision a new host
kairix system start       # Start all services
kairix system stop        # Stop all services
kairix system status      # Check service status

# User management commands
kairix users create <username>  # Create a new user
kairix users list              # List all users
kairix users delete <username> # Delete a user
```

## Development

Run tests with 100% coverage requirement:
```bash
uv run pytest
```

Run linting and type checking:
```bash
uv run ruff check --fix .
uv run mypy src/
```