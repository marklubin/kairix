# Getting Started with Kairix

This guide will help you get Kairix up and running in under 10 minutes.

## Prerequisites

Before you begin, ensure you have:

- Python 3.10 or higher
- Docker and Docker Compose
- `uv` package manager ([installation guide](https://github.com/astral-sh/uv))
- 4GB of available RAM
- 10GB of free disk space

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/kairix.git
cd kairix
```

### 2. Install Dependencies

```bash
# Install Python dependencies using uv
uv sync

# Start Neo4j database
docker-compose up -d neo4j
```

### 3. Configure Your Environment

Create a `.env` file in the project root:

```bash
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_secure_password

# OpenAI Configuration (optional, for OpenAI models)
OPENAI_API_KEY=your_openai_api_key

# Server Configuration
KAIRIX_HOST=0.0.0.0
KAIRIX_PORT=8080
```

### 4. Start the Kairix Server

```bash
# Start the backend server
uv run python -m kairix_apps.server

# In a new terminal, start the web client
cd kairix-apps/client
npm install
npm run dev
```

### 5. Access Kairix

Open your browser and navigate to: http://localhost:3000

You should see the Kairix welcome screen!

## Your First Conversation

1. **Create an Agent**: Click "New Agent" and give your agent a name
2. **Start Chatting**: Type a message and press Enter
3. **Watch Memory Build**: As you chat, your agent remembers and learns
4. **Test Memory**: Ask your agent about previous conversations

## Next Steps

- **Process ChatGPT History**: Import your ChatGPT conversations:
  ```bash
  uv run chatgpt-export-v2 -i export.json -o output/
  ```

- **Configure Voice**: Enable voice interaction in Settings

- **Explore the API**: Check out the [API Reference](api-reference.md)

## Common Issues

### Neo4j Won't Start
```bash
# Check if port 7687 is already in use
lsof -i :7687

# Check Docker logs
docker-compose logs neo4j
```

### ImportError on Startup
```bash
# Ensure you're using uv and dependencies are installed
uv sync
```

### Connection Refused
- Verify Neo4j is running: `docker-compose ps`
- Check your `.env` file has correct credentials
- Ensure firewall isn't blocking ports 7687 and 8080

## Getting Help

- Join our Discord: [discord.gg/kairix](https://discord.gg/kairix)
- Check [Troubleshooting Guide](troubleshooting.md)
- Report issues: [GitHub Issues](https://github.com/yourusername/kairix/issues)