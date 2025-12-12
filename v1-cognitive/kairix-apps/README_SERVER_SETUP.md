# Kairix Server Setup & Testing Guide

## Quick Start

### 1. Install Dependencies
```bash
cd kairix-apps
uv sync --extra-index-url https://download.pytorch.org/whl/cpu
```

### 2. Start the Server
```bash
doppler run -p kairix -c mark -- uv run python src/kairix_apps/server.py
```

The server will start on port 8888 (configurable via `KAIRIX_SERVER_PORT`).

### 3. Verify Server is Running
```bash
curl http://localhost:8888/health
```

Should return: `{"status":"healthy","service":"kairix-api"}`

## Admin Panel

Access the web-based admin panel at:
```
http://localhost:8888/admin
```

Features:
- View server status and configuration
- Test chat completions via web form
- Real-time response display
- No authentication required (use with caution in production)

## Running Tests

### Automated Test Suite
```bash
./run-tests.sh
```

Or directly:
```bash
uv run python test_server.py
```

### Test Results
- ✅ **6/7 tests passing**
- ⚠️ 1 warning (CORS on OPTIONS)
- ✅ Chat completion validation error FIXED!

See `TESTING.md` for detailed test documentation.

## API Endpoints

### Health Check
```bash
GET /health
```
Returns server health status.

### List Models
```bash
GET /v1/models
```
Returns available AI models.

### Chat Completion
```bash
POST /v1/chat/completions
Headers:
  Content-Type: application/json
  x-api-key: <your-key>
Body:
{
  "model": "kairix-conversational",
  "messages": [{"role": "user", "content": "Hello"}],
  "stream": false
}
```

### Admin Info
```bash
GET /admin/info
```
Returns server configuration and status.

### Admin Panel
```bash
GET /admin
```
Returns HTML admin interface.

## Configuration

Required environment variables (via Doppler):
- `KAIRIX_SERVER_PORT` - Server port (default: 8888)
- `KAIRIX_PERSONA_NAME` - AI persona name (e.g., "Apiana")
- `KAIRIX_USER_NAME` - User name (e.g., "Mark")
- `KAIRIX_AGENT_CONFIGURATION_SET_KEY` - Agent config (e.g., "openai")
- `OPENAI_API_KEY` - OpenAI API key
- `KAIRIX_LOG_LEVEL` - Logging level (DEBUG, INFO, etc.)

Optional:
- `KAIRIX_API_KEY` - API authentication key
- `KAIRIX_MAGG_EXECUTABLE` - Path to MCP aggregator (optional)

## Architecture

### Components
1. **FastAPI Server** - HTTP API with CORS support
2. **OpenAI Adapter** - Translates requests to OpenAI format
3. **Conversational Persona** - AI agent with memory and context
4. **Perceptors** - Context gathering (location, weather, history)
5. **SQLite Storage** - Vector database for memories
6. **Admin Panel** - Web UI for testing

### MCP Server (Optional)
The server supports Model Context Protocol (MCP) for extended functionality, but runs fine without it. If magg is not available, the server continues with core features.

## Development

### Hot Reload
For development with auto-reload:
```bash
uvicorn kairix_apps.server:app --reload --port 8888
```

### Dependency Changes
After modifying `pyproject.toml`:
```bash
uv sync
```

### Code Quality
```bash
uv run ruff check --fix src/
uv run mypy src/
```

## Troubleshooting

### Server won't start
1. Check port 8888 is not in use: `lsof -i :8888`
2. Verify Doppler credentials: `doppler login`
3. Check environment variables: `doppler secrets -p kairix -c mark`

### MCP Server Errors
These are warnings and can be ignored:
```
WARNING: MCP server not available, continuing without it
```
The server works without MCP.

### Chat Completion Validation Error
**FIXED!** The validation error was caused by a missing `logprobs` field in OpenAI's ResponseTextDeltaEvent. The server now monkey-patches the Pydantic model at startup to make this field optional.

### Dependencies Taking Long Time
First install downloads ~2GB of dependencies. Subsequent installs are cached.

## Production Deployment

### Using systemd
Create `/etc/systemd/system/kairix-server.service`:
```ini
[Unit]
Description=Kairix AI Server
After=network.target

[Service]
Type=simple
User=kairix
WorkingDirectory=/home/kairix/kairix/kairix-apps
ExecStart=/usr/local/bin/doppler run -p kairix -c prod -- /usr/local/bin/uv run python src/kairix_apps/server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable kairix-server
sudo systemctl start kairix-server
sudo systemctl status kairix-server
```

### Security Considerations
1. Set `KAIRIX_API_KEY` for authentication
2. Use HTTPS with reverse proxy (Caddy/nginx)
3. Restrict `/admin` endpoint in production
4. Use separate Doppler configs for dev/prod
5. Enable rate limiting
6. Monitor logs for suspicious activity

## Testing User Profiles

The current test profile:
- **User:** Mark
- **Persona:** Apiana
- **Database:** `/home/mlubin/kairix/kairix-apps/.kairix/k.db`

To create a new test user, update the Doppler config or set environment variables before starting the server.

## Next Steps

1. ✅ Server running with admin panel
2. ✅ Automated test suite
3. ⚠️ Fix chat completion validation (optional)
4. 📋 Add streaming response support
5. 📋 Add context update endpoint testing
6. 📋 Production deployment with authentication
7. 📋 Multi-user support

## Support

- Documentation: See `TESTING.md` for test details
- Issues: Check server logs at DEBUG level
- Configuration: Review `CLAUDE.md` in project root
