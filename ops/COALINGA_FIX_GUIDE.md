# Coalinga Server Fix Guide

## Issues Fixed (Already Committed & Pushed)

### 1. Incremental Reflection Running Too Frequently
- **Fixed in**: `kairix-core/src/kairix_core/cognition/perceptor/incremental_reflection.py`
- **Change**: Now counts message pairs instead of individual messages
- **Effect**: With interval=20, will run every 20 exchanges instead of every 10

### 2. MCP Server Validation Timeout
- **Fixed in**: `kairix-apps/validate_mcp_servers.py`
- **Change**: Added 10-second timeout to MCP server validation
- **Effect**: Server won't hang if MCP server fails to respond

## Current Problems

### SSH Connection Issue
- **Symptom**: SSH connection closes during key exchange
- **Error**: `Connection closed by 45.76.169.111 port 22` during `SSH2_MSG_KEX_ECDH_REPLY`
- **Likely Cause**:
  - Fail2ban blocking automated connection attempts
  - SSH MaxStartups limit
  - Too many rapid connection attempts from this machine

### MCP Server Configuration
- **Issue**: MCP config comes from Doppler `MCP_CONFIG_JSON` env var
- **Problem**: Path `/home/kairix` likely doesn't exist on coalinga
- **Need to check**: What the actual working directory is on coalinga

## Manual Deployment Steps

### Step 1: SSH to Coalinga
```bash
ssh coalinga
```

### Step 2: Navigate to Kairix Directory
```bash
# Find where kairix is installed
ls -la /opt/kairix* /root/kairix* ~/kairix* 2>/dev/null

# Navigate to it (adjust path as needed)
cd /opt/kairix  # or wherever it is
```

### Step 3: Pull Latest Changes
```bash
git pull origin feature/diskcache-notebook-viewer
```

### Step 4: Update Dependencies
```bash
cd kairix-core
uv sync
cd ../kairix-apps
uv sync
cd ..
```

### Step 5: Check/Fix MCP Configuration in Doppler
```bash
# Check current MCP config
doppler secrets get MCP_CONFIG_JSON --plain

# It should look like:
# {
#   "mcpServers": {
#     "filesystem": {
#       "command": "npx",
#       "args": ["-y", "@modelcontextprotocol/server-filesystem", "/root"],
#       "description": "Access to filesystem operations"
#     }
#   }
# }

# If the path is wrong, update it:
doppler secrets set MCP_CONFIG_JSON='{"mcpServers":{"filesystem":{"command":"npx","args":["-y","@modelcontextprotocol/server-filesystem","/root"],"description":"Access to filesystem operations"}}}'

# IMPORTANT: Replace /root with the actual working directory path
```

### Step 6: Test MCP Server Manually
```bash
cd kairix-apps

# Test the validation script
uv run python validate_mcp_servers.py

# Should show:
# ✓ filesystem: OK
#   Tools: 14
#   Resources: 0
#   Prompts: 0
```

### Step 7: Restart Server
```bash
sudo systemctl restart kairix-server-mark
```

### Step 8: Monitor Startup
```bash
# Watch the logs in real-time
sudo journalctl -u kairix-server-mark -f

# Look for:
# - "MCP servers validated successfully" (should appear quickly, not hang)
# - "Persona created successfully"
# - "MCP servers connected successfully"
# - "OpenAI adapter initialized successfully"
```

### Step 9: Test Server
```bash
# Check service status
sudo systemctl status kairix-server-mark

# Test health endpoint
curl http://localhost:8000/health

# Should return: {"status":"healthy","service":"kairix-api"}
```

### Step 10: Test External Access
```bash
# From your local machine:
curl https://dev.kairix.net/api/health
```

## Troubleshooting

### If Server Still Hangs on Startup
1. Check which MCP server is failing:
```bash
cd kairix-apps
uv run python validate_mcp_servers.py
```

2. If timeout errors appear, the MCP server path is likely wrong
3. Update the path in Doppler to match the actual filesystem location

### If MCP Server Path is Wrong
1. Find the correct path:
```bash
pwd  # from kairix directory
```

2. Update Doppler:
```bash
doppler secrets set MCP_CONFIG_JSON='{"mcpServers":{"filesystem":{"command":"npx","args":["-y","@modelcontextprotocol/server-filesystem","CORRECT_PATH_HERE"],"description":"Access to filesystem operations"}}}'
```

3. Restart the server

### If Reflection Still Runs Too Often
1. Check the env var:
```bash
doppler secrets get KAIRIX_SUMMARIZATION_INTERVAL --plain
```

2. Should be `20` or higher
3. The fix ensures it counts pairs, so `20` = every 20 user+assistant exchanges

## Summary of Fixes

| Issue | File Changed | What Changed |
|-------|--------------|--------------|
| Reflection frequency | `kairix-core/src/kairix_core/cognition/perceptor/incremental_reflection.py` | Tracks message pairs, not individual messages |
| Server startup hang | `kairix-apps/validate_mcp_servers.py` | Added 10s timeout to MCP validation |
| MCP path (manual) | Doppler `MCP_CONFIG_JSON` | Need to set correct filesystem path |

## Commit Hash
Latest commit: `71e60f6` on branch `feature/diskcache-notebook-viewer`
