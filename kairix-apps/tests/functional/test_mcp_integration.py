"""Functional tests for MCP server integration with conversational agent via MCPEz."""
import asyncio
import os
import pytest
import pytest_asyncio
import httpx
from pathlib import Path

# Set up test environment before imports
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["KAIRIX_APP_ID"] = "test_mcp"
os.environ["KAIRIX_AGENT_CONFIGURATION_SET_KEY"] = "openai"
os.environ["KAIRIX_USER_NAME"] = "TestUser"
os.environ["KAIRIX_PERSONA_NAME"] = "TestAgent"
os.environ["KAIRIX_SUMMARIZATION_INTERVAL"] = "10"
os.environ["KAIRIX_MESSAGE_RETENTION_WINDOW"] = "20"
os.environ["KAIRIX_N_SUMMARIES_PER_MESSAGE"] = "5"
os.environ["KAIRIX_SERVER_PORT"] = "8000"

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
    reason="MCPEz not running. See docs/MCPEZ_SETUP.md for setup instructions"
)


@pytest_asyncio.fixture
async def agent_runtime():
    """Create an agent runtime with MCP integration."""
    from kairix_core.runtime.agent import AgentRuntime

    runtime = AgentRuntime()
    yield runtime


@pytest_asyncio.fixture
async def persona():
    """Create a conversational persona with MCP integration."""
    from kairix_apps.engine import KairixEngine

    try:
        persona = KairixEngine.conversational_persona_for_environment()
        yield persona
    finally:
        # Cleanup
        pass


@pytest.mark.asyncio
async def test_mcp_filesystem_tools_available(agent_runtime):
    """Test that MCP filesystem tools are available to the agent."""

    # Verify MCP server is configured
    assert agent_runtime.mcp_server is not None, "MCP server should be configured"

    # Connect to MCP server
    async with agent_runtime.mcp_server as server:
        # List available tools
        tools = await server.list_tools()

        assert tools is not None, "Should receive tools list"
        assert len(tools) > 0, "Should have at least one tool available"

        # Check for filesystem tools
        tool_names = [tool.name for tool in tools]
        logger.info(f"Available MCP tools: {tool_names}")

        # Filesystem server should provide read_file, list_directory, etc.
        assert any("read" in name.lower() or "file" in name.lower() for name in tool_names), \
            "Should have file reading tools"


@pytest.mark.asyncio
async def test_agent_can_use_mcp_tools(persona):
    """Test that the conversational agent can use MCP tools during conversation."""

    # Ask the agent to list files in the MCP test directory
    response = await persona.respond_to_stimulus(
        "List all files in the current directory and tell me what you find."
    )

    assert response is not None, "Should receive a response"
    assert len(response) > 0, "Response should not be empty"

    # The response should mention files from our test directory
    response_lower = response.lower()
    assert "file" in response_lower or "directory" in response_lower, \
        "Response should mention files or directory"

    logger.info(f"Agent response: {response[:200]}...")


@pytest.mark.asyncio
async def test_agent_can_read_file_contents(persona):
    """Test that the agent can read specific file contents using MCP tools."""

    # Ask the agent to read a specific test file
    response = await persona.respond_to_stimulus(
        "Read the contents of readme.txt and summarize what it says."
    )

    assert response is not None, "Should receive a response"
    assert len(response) > 0, "Response should not be empty"

    # The response should reference content from readme.txt
    response_lower = response.lower()
    assert any(keyword in response_lower for keyword in ["test", "mcp", "integration"]), \
        "Response should mention content from readme.txt"

    logger.info(f"Agent response: {response[:200]}...")


@pytest.mark.asyncio
async def test_mcp_tools_in_multi_turn_conversation(persona):
    """Test that MCP tools work across multiple conversation turns."""

    # First turn: list files
    response1 = await persona.respond_to_stimulus(
        "What files are available in the current directory?"
    )
    assert response1 is not None
    logger.info(f"Turn 1: {response1[:100]}...")

    # Second turn: read a file (agent should remember context)
    response2 = await persona.respond_to_stimulus(
        "Read the readme file and tell me its purpose."
    )
    assert response2 is not None
    logger.info(f"Turn 2: {response2[:100]}...")

    # The second response should contain information from the file
    assert len(response2) > 20, "Should provide meaningful response about file contents"


@pytest.mark.asyncio
async def test_mcp_error_handling(persona):
    """Test that the agent handles MCP tool errors gracefully."""

    # Ask agent to read a non-existent file
    response = await persona.respond_to_stimulus(
        "Read the file called nonexistent_file_12345.txt"
    )

    assert response is not None, "Should receive a response even for errors"

    # Agent should communicate that the file doesn't exist or isn't found
    response_lower = response.lower()
    assert any(keyword in response_lower for keyword in ["not found", "doesn't exist", "cannot find", "no such"]), \
        "Response should indicate file not found"

    logger.info(f"Error handling response: {response[:200]}...")


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "-s"])
