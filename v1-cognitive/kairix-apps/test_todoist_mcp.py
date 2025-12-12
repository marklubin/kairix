#!/usr/bin/env python3
"""Test Todoist MCP server connection."""

import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_todoist():
    """Test connecting to Todoist MCP server."""

    # Set up environment
    env = {
        **os.environ,
        "TODOIST_API_TOKEN": "9ace69096a3256a42819215527ace1b0959d78f0"
    }

    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@abhiz123/todoist-mcp-server"],
        env=env
    )

    print("Starting Todoist MCP server...")

    try:
        async with stdio_client(server_params) as (read, write):
            print("Connected to stdio streams")

            async with ClientSession(read, write) as session:
                print("ClientSession created, initializing...")

                # Try with a longer timeout
                result = await asyncio.wait_for(session.initialize(), timeout=15.0)

                print(f"✓ Initialized successfully!")
                print(f"  Server name: {result.serverInfo.name}")
                print(f"  Server version: {result.serverInfo.version}")

                # List tools
                tools = await session.list_tools()
                print(f"  Available tools: {len(tools.tools)}")
                for tool in tools.tools:
                    print(f"    - {tool.name}: {tool.description}")

    except asyncio.TimeoutError:
        print("✗ Timeout during initialization (15s)")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_todoist())
