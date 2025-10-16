# MCP Functional Tests

These tests verify that the Kairix agent can access MCP tools through MCPEz.

## Prerequisites

1. **MCPEz must be running**:
   ```bash
   docker ps | grep mcpez
   ```

2. **MCPEz must be configured** with a `kairix-agent` application containing a filesystem server

See `docs/MCPEZ_SETUP.md` for setup instructions.

## Running Tests

```bash
# Run all MCP tests
uv run python -m pytest tests/functional/test_mcp_*.py -v

# Run specific test
uv run python -m pytest tests/functional/test_mcp_simple.py::test_mcp_server_provides_filesystem_tools -v
```

## Test Files

- **test_mcp_simple.py**: Basic MCP connection and tool availability tests
- **test_mcp_integration.py**: Full agent conversation tests with MCP tools

## Common Issues

### Tests Skip with "MCPEz not configured"

MCPEz needs to be running and configured with the `kairix-agent` application.

1. Start MCPEz (auto-started with Kairix server)
2. Open http://localhost:8088
3. Create `kairix-agent` application
4. Add filesystem server (see docs/MCPEZ_SETUP.md)

### Connection Errors

Check that agent is configured to connect to MCPEz:

```bash
# Should show MCPEz SSE endpoint
tail -f /var/log/kairix/server.log | grep "MCP server configured"
```

Expected output:
```
MCP server configured: http://localhost:8088/mcp/kairix-agent/sse
```

## Development

Since these tests require Docker and MCPEz, they are currently excluded from CI/CD.

To enable them:
1. Set up MCPEz in CI environment
2. Configure test application
3. Un-skip tests in pytest.ini
