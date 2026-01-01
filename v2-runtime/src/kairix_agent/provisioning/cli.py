"""CLI for provisioning Kairix agents.

Usage:
    uv run provision-agent --name Corindel
    uv run provision-agent --list-blocks
    uv run provision-agent --list-archives
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from typing import TYPE_CHECKING

from letta_client import AsyncLetta, ConflictError

from kairix_agent.config import Config
from kairix_agent.provisioning.agents import (
    AgentSpec,
    create_conversational_agent,
)
from kairix_agent.provisioning.blocks import BlockDefinition  # noqa: TC001
from kairix_agent.provisioning.prompts import get_agent_definition

if TYPE_CHECKING:
    from letta_client.types import BlockResponse
    from letta_client.types.archive import Archive

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def find_or_create_block(
    client: AsyncLetta,
    block_def: BlockDefinition,
    existing_blocks: dict[str, BlockResponse],
    force_create: bool = False,
) -> str:
    """Find existing block by label or create new one. Returns block ID.

    Args:
        client: Letta client.
        block_def: Block definition to create or find.
        existing_blocks: Dict of label -> BlockResponse for existing blocks.
        force_create: If True, always create a new block even if one exists with
            the same label. Use this for new conversational agents to ensure they
            get their own unique blocks rather than sharing with other agents.
    """
    if not force_create and block_def.label in existing_blocks:
        block = existing_blocks[block_def.label]
        logger.info("  Using existing block: %s (%s)", block_def.label, block.id)
        return block.id

    # Create new block
    block = await client.blocks.create(
        label=block_def.label,
        value=block_def.initial_value,
        description=block_def.description,
        limit=block_def.limit,
        read_only=block_def.read_only,
    )
    logger.info("  Created new block: %s (%s)", block_def.label, block.id)
    return block.id


async def find_agent_by_name(
    client: AsyncLetta,
    name: str,
) -> tuple[str, dict[str, str], set[str]] | None:
    """Find an existing agent by name.

    Returns:
        Tuple of (agent_id, dict of label -> block_id, set of archive ids) if found, None otherwise.
    """
    async for agent in client.agents.list(name=name):
        if agent.name == name:
            # Get attached blocks via dedicated endpoint
            # (agents.retrieve().memory.blocks is broken in SDK - returns empty)
            existing_blocks: dict[str, str] = {}
            # order='asc' required: SDK pagination assumes asc, but server defaults to desc
            async for block in client.agents.blocks.list(agent_id=agent.id, order="asc"):
                if block.label:
                    existing_blocks[block.label] = block.id
                    logger.debug("  Found existing block: %s (%s)", block.label, block.id)

            # Get attached archives
            archive_ids: set[str] = set()
            async for archive in client.archives.list(agent_id=agent.id):
                archive_ids.add(archive.id)

            return agent.id, existing_blocks, archive_ids
    return None


async def provision_agent(
    client: AsyncLetta,
    spec: AgentSpec,
    existing_blocks: dict[str, BlockResponse],
    archive_id: str | None = None,
    universal_block_ids: dict[str, str] | None = None,
    is_conversational: bool = False,
) -> str:
    """Provision an agent based on its spec. Returns agent ID.

    If an agent with the same name exists, validates and remediates its configuration
    instead of creating a duplicate.

    Args:
        client: Letta client.
        spec: Agent specification.
        existing_blocks: Dict of label -> BlockResponse for all existing blocks.
        archive_id: Optional archive ID to attach.
        universal_block_ids: Optional dict of label -> block_id for universal blocks.
            Used by subagents to attach the same blocks as the conversational agent.
        is_conversational: If True, this is a new conversational agent that should
            create fresh blocks rather than reusing blocks from other agents.
    """
    # Check if agent already exists
    existing = await find_agent_by_name(client, spec.name)

    if existing:
        agent_id, existing_agent_blocks, existing_archive_ids = existing
        logger.info("Found existing agent: %s (%s)", spec.name, agent_id)
        return await _remediate_existing_agent(
            client,
            agent_id,
            spec,
            existing_blocks,
            existing_agent_blocks,
            existing_archive_ids,
            archive_id,
            universal_block_ids,
        )

    # Agent doesn't exist - create new
    return await _create_new_agent(
        client, spec, existing_blocks, archive_id, universal_block_ids, is_conversational
    )


async def _remediate_existing_agent(
    client: AsyncLetta,
    agent_id: str,
    spec: AgentSpec,
    existing_blocks: dict[str, BlockResponse],
    existing_agent_blocks: dict[str, str],
    existing_archive_ids: set[str],
    archive_id: str | None,
    universal_block_ids: dict[str, str] | None = None,
) -> str:
    """Remediate an existing agent's configuration.

    Checks for missing or incorrect blocks and archives, fixes them if needed.
    Always updates the system prompt to match the current DB definition.

    Args:
        client: Letta client.
        agent_id: ID of the existing agent.
        spec: Agent specification.
        existing_blocks: Dict of label -> BlockResponse for all blocks in the system.
        existing_agent_blocks: Dict of label -> block_id for blocks attached to this agent.
        existing_archive_ids: Set of archive IDs attached to this agent.
        archive_id: Optional archive ID that should be attached.
        universal_block_ids: Optional dict of label -> block_id for universal blocks.
    """
    # Use no-retry client for archive/tool attach operations (409 Conflict is expected, not retryable)
    no_retry_client = client.with_options(max_retries=0)

    # Always update system prompt to ensure it matches DB definition
    logger.info("Updating system prompt for agent %s...", agent_id)
    await client.agents.update(agent_id=agent_id, system=spec.system_prompt)
    logger.info("  System prompt updated")

    # Check blocks - both missing AND incorrect (wrong ID)
    # Both universal and subagent blocks should use IDs from convo agent if available
    blocks_need_fixing = False

    for block_def in [*spec.universal_blocks, *spec.subagent_blocks]:
        label = block_def.label
        current_block_id = existing_agent_blocks.get(label)

        # Determine the correct block ID for this label
        # Priority: convo agent's block > current block > create new
        # NOTE: We do NOT reuse system-wide blocks for conversational agents
        # to avoid accidentally sharing blocks between different agent entities
        correct_block_id: str | None = None
        if universal_block_ids and label in universal_block_ids:
            # Use the exact ID from conversational agent (for both universal and subagent blocks)
            correct_block_id = universal_block_ids[label]
        elif current_block_id:
            # Block exists and no convo agent ID to match - keep it
            continue
        else:
            # Block missing - create a new one for this agent
            # (Don't reuse system-wide blocks - they may belong to other agents)
            block = await client.blocks.create(
                label=block_def.label,
                value=block_def.initial_value,
                description=block_def.description,
                limit=block_def.limit,
                read_only=block_def.read_only,
            )
            correct_block_id = block.id
            logger.info("  Created block: %s (%s)", label, correct_block_id)

        # Check if we need to fix this block
        if current_block_id is None:
            # Block missing - attach it
            logger.info("  Attaching missing block: %s (%s)", label, correct_block_id)
            await client.agents.blocks.attach(agent_id=agent_id, block_id=correct_block_id)
            blocks_need_fixing = True
        elif current_block_id != correct_block_id:
            # Wrong block attached - detach and attach correct one
            logger.info("  Replacing incorrect block %s: %s -> %s", label, current_block_id, correct_block_id)
            await client.agents.blocks.detach(agent_id=agent_id, block_id=current_block_id)
            await client.agents.blocks.attach(agent_id=agent_id, block_id=correct_block_id)
            blocks_need_fixing = True

    if not blocks_need_fixing:
        logger.info("All required blocks present and correct")

    # Check archive attachment
    if archive_id and archive_id not in existing_archive_ids:
        logger.info("Attaching missing archive %s...", archive_id)
        try:
            await no_retry_client.agents.archives.attach(archive_id=archive_id, agent_id=agent_id)
            logger.info("  Archive attached successfully")
        except ConflictError:
            logger.info("  Archive already attached (conflict ignored)")
    elif archive_id:
        logger.info("Archive already attached")

    # Check for missing tools
    if spec.tools:
        existing_tool_names: set[str] = set()
        async for tool in client.agents.tools.list(agent_id=agent_id):
            if tool.name:
                existing_tool_names.add(tool.name)

        missing_tools = set(spec.tools) - existing_tool_names
        if missing_tools:
            logger.info("Agent missing tools: %s", missing_tools)
            for tool_name in missing_tools:
                # Find tool by name
                tool_id: str | None = None
                async for tool in client.tools.list():
                    if tool.name == tool_name:
                        tool_id = tool.id
                        break
                if tool_id:
                    try:
                        await no_retry_client.agents.tools.attach(agent_id=agent_id, tool_id=tool_id)
                        logger.info("  Attached tool: %s", tool_name)
                    except ConflictError:
                        logger.info("  Tool %s already attached (conflict ignored)", tool_name)
                else:
                    logger.warning("  Tool not found: %s", tool_name)
        else:
            logger.info("All required tools present")

    logger.info("Agent remediation complete: %s", agent_id)
    return agent_id


async def _create_new_agent(
    client: AsyncLetta,
    spec: AgentSpec,
    existing_blocks: dict[str, BlockResponse],
    archive_id: str | None,
    universal_block_ids: dict[str, str] | None = None,
    is_conversational: bool = False,
) -> str:
    """Create a new agent from scratch.

    Args:
        client: Letta client.
        spec: Agent specification.
        existing_blocks: Dict of label -> BlockResponse for all existing blocks.
        archive_id: Optional archive ID to attach.
        universal_block_ids: Optional dict of label -> block_id for universal blocks.
        is_conversational: If True, this is a new conversational agent and should
            create fresh blocks rather than reusing existing ones from other agents.
    """
    logger.info("Provisioning new agent: %s", spec.name)

    # Collect block IDs
    block_ids: list[str] = []

    # For new conversational agents, always create fresh blocks to avoid
    # sharing blocks with other agents (each agent gets its own identity)
    force_create = is_conversational

    # Universal blocks - use explicit IDs if provided, otherwise reuse existing or create
    logger.info("Setting up universal blocks...")
    for block_def in spec.universal_blocks:
        if universal_block_ids and block_def.label in universal_block_ids:
            # Use the exact block ID from the conversational agent
            block_id = universal_block_ids[block_def.label]
            logger.info("  Using universal block: %s (%s)", block_def.label, block_id)
        else:
            block_id = await find_or_create_block(client, block_def, existing_blocks, force_create)
        block_ids.append(block_id)

    # Subagent blocks - reuse from convo agent if exists, otherwise create
    # (subagent blocks are attached to declaring subagent + convo agent)
    logger.info("Setting up subagent blocks...")
    for block_def in spec.subagent_blocks:
        if universal_block_ids and block_def.label in universal_block_ids:
            # Reuse existing block from conversational agent
            block_id = universal_block_ids[block_def.label]
            logger.info("  Using existing subagent block: %s (%s)", block_def.label, block_id)
        else:
            # Check system-wide existing blocks, or create new
            block_id = await find_or_create_block(client, block_def, existing_blocks, force_create)
        block_ids.append(block_id)

    # Create the agent
    logger.info("Creating agent with %d blocks (include_base_tools=%s)...", len(block_ids), spec.include_base_tools)
    agent = await client.agents.create(
        name=spec.name,
        description=spec.description,
        system=spec.system_prompt,
        model=spec.model,
        embedding=spec.embedding,
        context_window_limit=spec.context_window,
        enable_reasoner=spec.enable_reasoner,
        max_tokens=spec.max_tokens,
        max_reasoning_tokens=spec.max_reasoning_tokens,
        block_ids=block_ids,
        include_base_tools=spec.include_base_tools,
    )

    logger.info("Agent created: %s (%s)", spec.name, agent.id)

    # Attach tools from spec
    if spec.tools:
        logger.info("Attaching %d tools...", len(spec.tools))
        for tool_name in spec.tools:
            # Find tool by name
            tool_id: str | None = None
            async for tool in client.tools.list():
                if tool.name == tool_name:
                    tool_id = tool.id
                    break
            if tool_id:
                await client.agents.tools.attach(agent_id=agent.id, tool_id=tool_id)
                logger.info("  Attached tool: %s", tool_name)
            else:
                logger.warning("  Tool not found: %s", tool_name)

    # Attach archive if provided
    if archive_id:
        logger.info("Attaching archive %s to agent...", archive_id)
        await client.agents.archives.attach(archive_id=archive_id, agent_id=agent.id)
        logger.info("  Archive attached successfully")

    return agent.id


async def list_blocks(client: AsyncLetta) -> None:
    """List all existing blocks."""
    logger.info("Existing blocks:")
    async for block in client.blocks.list():
        logger.info("  - %s (%s): %d chars", block.label, block.id, len(block.value))


async def list_agents(client: AsyncLetta) -> None:
    """List all existing agents."""
    logger.info("Existing agents:")
    async for agent in client.agents.list():
        logger.info("  - %s (%s)", agent.name, agent.id)


async def list_archives(client: AsyncLetta) -> None:
    """List all existing archives."""
    logger.info("Existing archives:")
    async for archive in client.archives.list():
        logger.info("  - %s (%s)", archive.name, archive.id)


async def find_or_create_archive(
    client: AsyncLetta,
    name: str,
    existing_archives: dict[str, Archive],
) -> str:
    """Find existing archive by name or create new one. Returns archive ID."""
    if name in existing_archives:
        archive = existing_archives[name]
        logger.info("  Using existing archive: %s (%s)", name, archive.id)
        return archive.id

    # Create new archive
    archive = await client.archives.create(
        name=name,
        description=f"Shared archival memory for {name} entity",
        embedding="openai/text-embedding-3-small",
    )
    logger.info("  Created new archive: %s (%s)", name, archive.id)
    return archive.id


async def _setup_kp3_mcp_server(
    client: AsyncLetta,
    agent_id: str,
    agent_name: str,
) -> None:
    """Set up or update the KP3 MCP server for this agent.

    Creates an MCP server with X-Agent-ID header baked in, so the agent's
    searches are automatically scoped to its own passages.

    Args:
        client: Letta client.
        agent_id: The agent ID to scope searches to.
        agent_name: The agent name (for MCP server naming).
    """
    from letta_client.types.create_sse_mcp_server_param import CreateSseMcpServerParam
    from letta_client.types.update_sse_mcp_server_param import UpdateSseMcpServerParam

    kp3_url = Config.KP3_URL.value
    mcp_server_name = f"kp3_{agent_name.lower()}"
    mcp_url = f"{kp3_url}/mcp/sse"

    logger.info("Setting up KP3 MCP server for agent %s...", agent_id)

    # Check if MCP server already exists for this agent
    existing_server_id: str | None = None
    servers_response = await client.mcp_servers.list()
    for server in servers_response:
        if server.server_name == mcp_server_name:
            existing_server_id = server.id
            logger.info("  Found existing MCP server: %s (%s)", mcp_server_name, server.id)
            break

    if existing_server_id:
        # Update existing server with current agent_id header
        logger.info("  Updating MCP server with X-Agent-ID header...")
        update_config: UpdateSseMcpServerParam = {
            "server_url": mcp_url,
            "mcp_server_type": "sse",
            "custom_headers": {"X-Agent-ID": agent_id},
        }
        await client.mcp_servers.update(
            mcp_server_id=existing_server_id,
            config=update_config,
        )
    else:
        # Create new MCP server
        logger.info("  Creating MCP server: %s -> %s", mcp_server_name, mcp_url)
        create_config: CreateSseMcpServerParam = {
            "server_url": mcp_url,
            "mcp_server_type": "sse",
            "custom_headers": {"X-Agent-ID": agent_id},
        }
        server = await client.mcp_servers.create(
            server_name=mcp_server_name,
            config=create_config,
        )
        existing_server_id = server.id
        logger.info("  Created MCP server: %s", server.id)

    # Refresh to discover tools
    if existing_server_id:
        logger.info("  Refreshing MCP server to discover tools...")
        await client.mcp_servers.refresh(mcp_server_id=existing_server_id)

    logger.info("  KP3 MCP server setup complete")


async def _run_provisioning(
    client: AsyncLetta,
    base_name: str,
) -> int:
    """Run agent provisioning logic.

    Args:
        client: Letta client.
        base_name: Base name for the agent.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    # Load agent definition from database
    logger.info("Loading agent definition for conversational from database...")
    try:
        definition = await get_agent_definition("conversational")
        logger.info(
            "  Loaded definition (prompt: %d chars, universal: %s, subagent: %s)",
            len(definition.system_prompt),
            definition.universal_block_labels,
            definition.subagent_block_labels,
        )
    except ValueError as e:
        logger.error("Failed to load agent definition: %s", e)
        return 1

    # Get all existing blocks for reuse
    existing_blocks: dict[str, BlockResponse] = {}
    async for block in client.blocks.list():
        if block.label:
            existing_blocks[block.label] = block

    # Get all existing archives for reuse
    existing_archives: dict[str, Archive] = {}
    async for archive in client.archives.list():
        if archive.name:
            existing_archives[archive.name] = archive

    # Create spec using factory method with DB-loaded config
    spec = create_conversational_agent(
        base_name,
        definition.system_prompt,
        definition.universal_block_labels,
        definition.subagent_block_labels,
    )

    # Create a new archive with the agent's name
    logger.info("Setting up archive...")
    archive_id = await find_or_create_archive(client, base_name, existing_archives)

    agent_id = await provision_agent(
        client,
        spec,
        existing_blocks,
        archive_id,
        universal_block_ids=None,
        is_conversational=True,
    )

    # Create or update MCP server for KP3 search with agent-scoped headers
    await _setup_kp3_mcp_server(client, agent_id, base_name)

    logger.info("Done! Agent ID: %s", agent_id)

    return 0


async def main() -> int:
    """Main entry point for provisioning CLI."""
    parser = argparse.ArgumentParser(description="Provision Kairix agents")
    parser.add_argument(
        "--name",
        required=False,
        help="Agent name (required when provisioning)",
    )
    parser.add_argument(
        "--list-blocks",
        action="store_true",
        help="List all existing blocks",
    )
    parser.add_argument(
        "--list-agents",
        action="store_true",
        help="List all existing agents",
    )
    parser.add_argument(
        "--list-archives",
        action="store_true",
        help="List all existing archives",
    )
    parser.add_argument(
        "--letta-url",
        default=Config.LETTA_BASE_URL.value,
        help="Letta server URL",
    )

    args = parser.parse_args()

    client = AsyncLetta(base_url=args.letta_url)

    if args.list_blocks:
        await list_blocks(client)
        return 0

    if args.list_agents:
        await list_agents(client)
        return 0

    if args.list_archives:
        await list_archives(client)
        return 0

    if not args.name:
        parser.error("--name is required when provisioning an agent")

    return await _run_provisioning(client, args.name)


def cli() -> None:
    """Entry point for the CLI."""
    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    cli()
