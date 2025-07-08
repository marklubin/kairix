# Kairix Tools

A comprehensive toolkit for Kairix infrastructure management, including:
- **SRE Agent**: Automated monitoring and recovery system
- **User Management CLI**: Streamlined user onboarding tool

## Features

### SRE Agent
- **Automated Health Checks**: Monitors services across multiple users and ports
- **Log Analysis**: Analyzes logs for errors, anomalies, and user activity patterns
- **Auto-Recovery**: Attempts basic recovery actions when issues are detected
- **24-Hour Memory**: Maintains contextual awareness of system history
- **Interactive Chat**: REPL interface for querying system state and manual interventions
- **OpenAI Integration**: Uses function calling for intelligent decision making

### User Management (kairixctl)
- **Automated User Setup**: Generate Caddy configs with one command
- **Port Auto-Detection**: Automatically finds next available ports
- **Password Hashing**: Bcrypt hashing for Caddy basic_auth
- **User Discovery**: List and check status of all users
- **Complete Checklists**: Step-by-step guidance for operators

## Installation

```bash
# Clone the repository
cd kairix-sre-agent

# Install dependencies using uv
just install
```

## Configuration

The agent uses sensible defaults but can be configured via environment variables:

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `DISCORD_WEBHOOK_URL`: Optional webhook for critical alerts

## Usage

### SRE Agent

#### Run a Health Check

```bash
# Single health check run
just sre-run

# With verbose logging
just sre-debug
```

### Interactive Shell

```bash
# Start the chat interface
just sre-shell
```

Available commands in the shell:
- `/help` - Show available commands
- `/status` - Show current system status
- `/history` - Show recent agent runs
- `/services` - List all monitored services
- `/check` - Run a health check
- `/logs` - Analyze recent logs
- `/exit` - Exit the chat

#### View Status

```bash
# Show status for last 24 hours
just sre-status

# Show status for last 48 hours
just sre-status 48
```

### User Management

#### Add New User

```bash
# Interactive user creation
just new-user
```

#### List Users

```bash
# Show all configured users
just list-users
```

#### Check User

```bash
# Check specific user status
just check-user alice
```

## Architecture

The agent is built with a modular architecture:

- **Health Checker**: Monitors service availability via HTTP and process checks
- **Log Analyzer**: Parses logs for errors, patterns, and anomalies
- **Recovery Actions**: Implements safe recovery strategies (restart, cache clear)
- **Memory Store**: SQLite-based storage for historical context
- **Chat Interface**: Interactive REPL for manual operations

## Automated Deployment

### Systemd Service

```bash
# Install as a systemd service
just install-service

# Start the service
sudo systemctl enable --now kairix-sre-agent
```

### Cron Job

```bash
# Install cron job (runs every 5 minutes)
just install-cron
```

## Development

```bash
# Run linting
just lint

# Fix linting issues
just fix

# Run type checking
just mypy

# Run all checks
just check

# Watch mode for development
just watch
```

## Log Structure

The agent expects logs to be organized as:
```
/var/log/kairix/
├── mark/
│   ├── mark_ui.log
│   ├── mark_api.log
│   └── mark_tools.log
├── alice/
│   ├── alice_ui.log
│   ├── alice_api.log
│   └── alice_tools.log
└── sre-agent/
    ├── agent.log
    └── cron.log
```

## Service Port Convention

- UI services: 600x (6000, 6001, 6002...)
- API services: 700x (7000, 7001, 7002...)
- Tools services: 800x (8000, 8001, 8002...)

Where x corresponds to the user index.

## Documentation

- [**RUNBOOK.md**](RUNBOOK.md) - SRE Agent operational guide
- [**QUICK_REFERENCE.md**](QUICK_REFERENCE.md) - Command cheat sheet
- [**TROUBLESHOOTING.md**](TROUBLESHOOTING.md) - Problem-solving guide
- [**USER_MANAGEMENT.md**](USER_MANAGEMENT.md) - User onboarding guide

## How It Works

1. **Service Discovery**: Reads `~/kairix/caddyfile` to find all users and services
2. **Health Monitoring**: Checks HTTP endpoints, processes, and ports
3. **Log Analysis**: Scans service logs for errors and anomalies
4. **Intelligent Decisions**: Uses OpenAI to orchestrate checks and responses
5. **Recovery Actions**: Attempts safe fixes for common issues
6. **Historical Context**: Maintains 24-hour memory for pattern detection

## Quick Start

```bash
# 1. Install dependencies
just install

# 2. Set OpenAI API key
export OPENAI_API_KEY="sk-..."

# 3. Run health check
just sre-run

# 4. Check status
just sre-status

# 5. Set up automation (runs every 5 minutes)
just install-cron
```

## License

MIT