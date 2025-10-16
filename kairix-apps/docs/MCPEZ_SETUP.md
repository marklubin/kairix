# MCPEz Setup Guide

## Overview

MCPEz is an MCP server aggregator that provides a web UI for managing multiple MCP servers. Kairix connects to MCPEz via a single SSE endpoint, and MCPEz handles all the MCP server connections.

```
┌──────────────┐
│ Kairix Agent │ ──→ http://localhost:8088/mcp/kairix-agent/sse
└──────────────┘
       ↓
┌──────────────┐
│    MCPEz     │ ← Configure servers via Web UI
│  Aggregator  │
└──────┬───────┘
       ├─► Filesystem MCP Server (STDIO)
       ├─► Weather MCP Server (SSE)
       └─► Custom MCP Server (STDIO/SSE)
```

## Quick Start

### 1. MCPEz is Auto-Started

When Kairix server starts, MCPEz is automatically launched:
- Container: `kairix-mcpez`
- Port: 8088
- Web UI: http://localhost:8088

### 2. Configure Filesystem Server

1. **Open MCPEz Web UI**: http://localhost:8088

2. **Create Application**:
   - Click "New Application"
   - Name: `kairix-agent`
   - Description: "Kairix AI Agent"

3. **Add Filesystem Server**:
   - Click "Add Server"
   - Server Type: **STDIO**
   - Configuration:
     ```
     Command: npx
     Args: -y @modelcontextprotocol/server-filesystem /home/mlubin/kairix/kairix-apps/mcp-test-files
     Environment: (leave empty)
     ```

4. **Save Configuration**

5. **Test in AI Playground**:
   - Go to "Chat" or "Playground"
   - Connect to `kairix-agent`
   - Send: "List files in the current directory"
   - Should see MCP tools being called

### 3. Agent Connects Automatically

Kairix agent is configured to connect to:
```
http://localhost:8088/mcp/kairix-agent/sse
```

No additional configuration needed!

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `KAIRIX_MCPEZ_URL` | `http://localhost:8088` | MCPEz base URL |
| `KAIRIX_MCP_APP_ID` | `kairix-agent` | Application ID in MCPEz |

### Custom Configuration

If you want to use a different MCPEz instance or app name:

```bash
export KAIRIX_MCPEZ_URL=http://your-mcpez:8088
export KAIRIX_MCP_APP_ID=your-app-name
```

Or in Doppler:
```bash
doppler secrets set KAIRIX_MCPEZ_URL http://your-mcpez:8088
doppler secrets set KAIRIX_MCP_APP_ID your-app-name
```

## Adding More MCP Servers

### Example: Weather Server (SSE)

1. In MCPEz UI, go to your application
2. Click "Add Server"
3. Configure:
   - Server Type: **SSE**
   - URL: `https://weather-api.example.com/mcp/sse`
   - Headers: `Authorization: Bearer YOUR_TOKEN`
4. Save

The Kairix agent will immediately have access to weather tools!

### Example: Database Server (STDIO)

1. In MCPEz UI, go to your application
2. Click "Add Server"
3. Configure:
   - Server Type: **STDIO**
   - Command: `python`
   - Args: `/path/to/database-mcp-server.py`
   - Environment: `DATABASE_URL=postgresql://...`
4. Save

### Example: Another Filesystem Directory

1. In MCPEz UI, go to your application
2. Click "Add Server"
3. Configure:
   - Server Type: **STDIO**
   - Command: `npx`
   - Args: `-y @modelcontextprotocol/server-filesystem /path/to/other/directory`
4. Save

## Configuration Export/Import

MCPEz supports JSON configuration export:

1. Configure all your servers in the Web UI
2. Export configuration as JSON
3. Share with team or use in other environments
4. Import on new MCPEz instances

This makes it easy to replicate configurations!

## Verification

### Check MCPEz is Running

```bash
# Check container
docker ps | grep mcpez

# Check web UI
curl http://localhost:8088

# Check SSE endpoint
curl http://localhost:8088/mcp/kairix-agent/sse
```

### Check Agent Connection

```bash
cd kairix-apps

# Agent logs will show:
# "MCP server configured: http://localhost:8088/mcp/kairix-agent/sse"

# Test in agent
uv run python -c "
import asyncio
import os

os.environ['KAIRIX_USER_NAME'] = 'TestUser'
os.environ['KAIRIX_PERSONA_NAME'] = 'TestAgent'
os.environ['KAIRIX_AGENT_CONFIGURATION_SET_KEY'] = 'openai'
os.environ['KAIRIX_SUMMARIZATION_INTERVAL'] = '10'
os.environ['KAIRIX_MESSAGE_RETENTION_WINDOW'] = '20'
os.environ['KAIRIX_N_SUMMARIES_PER_MESSAGE'] = '5'

from kairix_apps.engine import KairixEngine

async def test():
    persona = KairixEngine.conversational_persona_for_environment()
    response = await persona.respond_to_stimulus('List files')
    print(response)

asyncio.run(test())
"
```

## Troubleshooting

### MCPEz Not Responding
```bash
# Check logs
docker logs kairix-mcpez

# Restart
docker restart kairix-mcpez

# Or restart Kairix server (which restarts MCPEz)
sudo systemctl restart kairix-server
```

### Agent Can't Connect
1. Verify MCPEz is running: `docker ps | grep mcpez`
2. Verify app_id exists in MCPEz UI
3. Check agent logs for connection errors
4. Test endpoint: `curl http://localhost:8088/mcp/kairix-agent/sse`

### No MCP Tools Available
1. Check that servers are configured in MCPEz UI
2. Test servers in MCPEz AI Playground first
3. Verify server configurations are correct
4. Check MCPEz logs for server startup errors

### Servers Not Starting in MCPEz
- **STDIO servers**: Check command is valid and executable
- **SSE servers**: Check URL is reachable and returns valid responses
- View server logs in MCPEz UI for error details

## Benefits

1. **Single Endpoint**: Agent connects to one URL for all MCP servers
2. **Web UI**: Visual configuration and management
3. **Multiple Servers**: Add as many as you need
4. **Mix Types**: Combine STDIO and SSE servers
5. **Easy Replication**: Export/import JSON configs
6. **No Code Changes**: Add servers without redeploying agent

## Production Deployment

### Remote MCPEz

If MCPEz is on a different server:

```bash
export KAIRIX_MCPEZ_URL=https://mcpez.your-domain.com
```

### Behind Reverse Proxy

If MCPEz is behind Caddy/nginx:

```
# Caddyfile
your-domain.com {
    handle /mcpez/* {
        reverse_proxy localhost:8088
    }
}
```

Then:
```bash
export KAIRIX_MCPEZ_URL=https://your-domain.com/mcpez
```

### Multiple Agents

Different agents can use different app IDs:

```bash
# Agent 1
export KAIRIX_MCP_APP_ID=agent-1

# Agent 2
export KAIRIX_MCP_APP_ID=agent-2
```

Each gets its own set of configured servers in MCPEz!

## Default Configuration

Here's a starter configuration for MCPEz (import via web UI):

```json
{
  "app_id": "kairix-agent",
  "name": "Kairix AI Agent",
  "description": "AI assistant with filesystem access",
  "servers": [
    {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/mlubin/kairix/kairix-apps/mcp-test-files"],
      "env": {}
    }
  ]
}
```

Save this to `mcpez-config.json` and import in the MCPEz UI.
