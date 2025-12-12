"""Simple MCP integration test to verify tools are accessible via MCPEz."""
import os
import pytest
import pytest_asyncio
import httpx

# Set up test environment
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["KAIRIX_APP_ID"] = "test_mcp_simple"
os.environ["KAIRIX_AGENT_CONFIGURATION_SET_KEY"] = "openai"

from kairix_core.runtime.logging import LoggingRuntime

logger = LoggingRuntime().logger


def check_mcpez_available():
    """Check if MCPEz is running and accessible."""
    try:
        response = httpx.get("http://localhost:8088", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


# Skip all tests if MCPEz is not running
pytestmark = pytest.mark.skipif(
    not check_mcpez_available(),
    reason="MCPEz not running. Start with: docker ps | grep mcpez"
)


@pytest_asyncio.fixture
async def agent_runtime():
    """Create an agent runtime with MCP integration."""
    from kairix_core.runtime.agent import AgentRuntime

    runtime = AgentRuntime()
    yield runtime


@pytest.mark.asyncio
async def test_mcp_server_provides_filesystem_tools(agent_runtime):
    """Verify MCP filesystem server is configured and provides expected tools."""

    assert agent_runtime.mcp_server is not None, "MCP server should be configured"

    async with agent_runtime.mcp_server as server:
        tools = await server.list_tools()

        assert len(tools) > 0, "Should have tools available"
        tool_names = [tool.name for tool in tools]

        # Verify expected filesystem tools are present
        expected_tools = ['read_file', 'list_directory', 'write_file']
        for expected in expected_tools:
            assert expected in tool_names, f"Should have {expected} tool"

        logger.info(f"✓ MCP server provides {len(tools)} tools: {', '.join(tool_names)}")


@pytest.mark.asyncio
async def test_mcp_server_can_list_test_directory(agent_runtime):
    """Verify MCP tools can list the test directory contents."""

    async with agent_runtime.mcp_server as server:
        tools = await server.list_tools()
        list_dir_tool = next((t for t in tools if t.name == "list_directory"), None)

        assert list_dir_tool is not None, "Should have list_directory tool"

        # Call the list_directory tool
        result = await server.call_tool(
            "list_directory",
            arguments={"path": "."}
        )

        assert result is not None, "Should get directory listing"
        logger.info(f"✓ Successfully listed directory via MCP tool")


@pytest.mark.asyncio
async def test_mcp_server_can_read_test_file(agent_runtime):
    """Verify MCP tools can read a test file."""

    async with agent_runtime.mcp_server as server:
        # Call the read_file tool to read our test file from the allowed directory
        result = await server.call_tool(
            "read_file",
            arguments={"path": "/home/mlubin/kairix/kairix-apps/mcp-test-files/test.txt"}
        )

        assert result is not None, "Should get file contents"

        # The result should contain our test message
        result_str = str(result)
        assert "test file" in result_str.lower(), "Should contain test file content"

        logger.info(f"✓ Successfully read file via MCP tool")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
