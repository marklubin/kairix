#!/usr/bin/env python3
"""Validate MCP servers defined in mcp_config.json"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def validate_server(name: str, config: dict[str, Any], timeout: int = 10) -> dict[str, Any]:
    """Validate a single MCP server.

    Args:
        name: Server name
        config: Server configuration
        timeout: Timeout in seconds for validation (default: 10)

    Returns:
        Dict with validation results including tools, resources, prompts, and any errors
    """
    result = {
        "name": name,
        "command": config["command"],
        "args": config.get("args", []),
        "description": config.get("description", ""),
        "status": "unknown",
        "tools": [],
        "resources": [],
        "prompts": [],
        "error": None
    }

    try:
        # Create server parameters
        server_params = StdioServerParameters(
            command=config["command"],
            args=config.get("args", []),
            env=config.get("env")
        )

        # Wrap the entire validation in a timeout
        async def validate_with_connection():
            # Connect to the server
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize the session
                    await session.initialize()

                    # List available tools
                    tools_result = await session.list_tools()
                    result["tools"] = [
                        {
                            "name": tool.name,
                            "description": tool.description or "",
                            "inputSchema": tool.inputSchema
                        }
                        for tool in tools_result.tools
                    ]

                    # List available resources
                    try:
                        resources_result = await session.list_resources()
                        result["resources"] = [
                            {
                                "uri": resource.uri,
                                "name": resource.name,
                                "description": resource.description or "",
                                "mimeType": resource.mimeType
                            }
                            for resource in resources_result.resources
                        ]
                    except Exception as e:
                        # Some servers may not support resources
                        result["resources"] = []

                    # List available prompts
                    try:
                        prompts_result = await session.list_prompts()
                        result["prompts"] = [
                            {
                                "name": prompt.name,
                                "description": prompt.description or ""
                            }
                            for prompt in prompts_result.prompts
                        ]
                    except Exception as e:
                        # Some servers may not support prompts
                        result["prompts"] = []

                    result["status"] = "ok"

        # Run validation with timeout
        await asyncio.wait_for(validate_with_connection(), timeout=timeout)

    except asyncio.TimeoutError:
        result["status"] = "error"
        result["error"] = f"Validation timed out after {timeout} seconds"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


async def validate_all_servers(config_path: Path) -> list[dict[str, Any]]:
    """Validate all MCP servers in the config file."""

    # Load config
    with open(config_path) as f:
        config = json.load(f)

    servers = config.get("mcpServers", {})

    # Validate each server
    results = []
    for name, server_config in servers.items():
        print(f"Validating MCP server: {name}...")
        result = await validate_server(name, server_config)
        results.append(result)

        if result["status"] == "ok":
            print(f"  ✓ {name}: OK")
            print(f"    Tools: {len(result['tools'])}")
            print(f"    Resources: {len(result['resources'])}")
            print(f"    Prompts: {len(result['prompts'])}")
        else:
            print(f"  ✗ {name}: ERROR")
            print(f"    {result['error']}")

    return results


def generate_system_prompt_info(results: list[dict[str, Any]]) -> str:
    """Generate generic system prompt documentation for available MCP tools."""

    lines = ["# Available MCP Tools\n"]

    working_servers = [r for r in results if r["status"] == "ok"]

    if not working_servers:
        lines.append("No MCP servers are currently available.\n")
        return "\n".join(lines)

    lines.append("The following tools are available through MCP servers:\n")

    for server in working_servers:
        lines.append(f"\n## {server['name']}")
        if server["description"]:
            lines.append(f"{server['description']}\n")

        if server["tools"]:
            lines.append("\n### Tools:")
            for tool in server["tools"]:
                lines.append(f"- **{tool['name']}**: {tool['description']}")

        if server["resources"]:
            lines.append(f"\n### Resources: {len(server['resources'])} available")

        if server["prompts"]:
            lines.append(f"\n### Prompts: {len(server['prompts'])} available")

    return "\n".join(lines)


async def main():
    """Main validation entry point."""

    # Find config file
    config_path = Path(__file__).parent / "mcp_config.json"

    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)

    print(f"Loading MCP config from: {config_path}\n")

    # Validate all servers
    results = await validate_all_servers(config_path)

    # Generate system prompt info
    prompt_info = generate_system_prompt_info(results)

    # Save results
    output_path = Path(__file__).parent / "mcp_validation_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nValidation results saved to: {output_path}")

    # Save system prompt info
    prompt_path = Path(__file__).parent / "mcp_tools_info.md"
    with open(prompt_path, "w") as f:
        f.write(prompt_info)
    print(f"System prompt info saved to: {prompt_path}")

    # Exit with error if any server failed
    failed = [r for r in results if r["status"] == "error"]
    if failed:
        print(f"\n{len(failed)} server(s) failed validation")
        sys.exit(1)

    print(f"\n✓ All {len(results)} MCP server(s) validated successfully")


if __name__ == "__main__":
    asyncio.run(main())
