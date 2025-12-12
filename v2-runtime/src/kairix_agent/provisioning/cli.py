"""CLI for provisioning Kairix agents.

Usage:
    uv run provision-agent --type conversational --name Corindel
    uv run provision-agent --type reflector --name Corindel
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
    create_background_insights_agent,
    create_conversational_agent,
    create_reflector_agent,
)
from kairix_agent.provisioning.blocks import BlockDefinition  # noqa: TC001
from kairix_agent.provisioning.prompts import get_system_prompt

if TYPE_CHECKING:
    from letta_client.types import BlockResponse
    from letta_client.types.archive import Archive

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def find_or_create_block(
    client: AsyncLetta,
    block_def: BlockDefinition,
    existing_blocks: dict[str, BlockResponse],
) -> str:
    """Find existing block by label or create new one. Returns block ID."""
    if block_def.label in existing_blocks:
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
            async for block in client.agents.blocks.list(agent_id=agent.id):
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
    shared_block_ids: dict[str, str] | None = None,
) -> str:
    """Provision an agent based on its spec. Returns agent ID.

    If an agent with the same name exists, validates and remediates its configuration
    instead of creating a duplicate.

    Args:
        client: Letta client.
        spec: Agent specification.
        existing_blocks: Dict of label -> BlockResponse for all existing blocks.
        archive_id: Optional archive ID to attach.
        shared_block_ids: Optional dict of label -> block_id for shared blocks.
            Used by reflector agents to attach the same blocks as the conversational agent.
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
            shared_block_ids,
        )

    # Agent doesn't exist - create new
    return await _create_new_agent(client, spec, existing_blocks, archive_id, shared_block_ids)


async def _remediate_existing_agent(
    client: AsyncLetta,
    agent_id: str,
    spec: AgentSpec,
    existing_blocks: dict[str, BlockResponse],
    existing_agent_blocks: dict[str, str],
    existing_archive_ids: set[str],
    archive_id: str | None,
    shared_block_ids: dict[str, str] | None = None,
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
        shared_block_ids: Optional dict of label -> block_id for shared blocks.
    """
    # Use no-retry client for archive/tool attach operations (409 Conflict is expected, not retryable)
    no_retry_client = client.with_options(max_retries=0)

    # Always update system prompt to ensure it matches DB definition
    logger.info("Updating system prompt for agent %s...", agent_id)
    await client.agents.update(agent_id=agent_id, system=spec.system_prompt)
    logger.info("  System prompt updated")

    # Check blocks - both missing AND incorrect (wrong ID for shared blocks)
    shared_labels = {b.label for b in spec.shared_blocks}
    blocks_need_fixing = False

    for block_def in [*spec.shared_blocks, *spec.unique_blocks]:
        label = block_def.label
        current_block_id = existing_agent_blocks.get(label)

        # Determine the correct block ID for this label
        correct_block_id: str | None = None
        if label in shared_labels and shared_block_ids and label in shared_block_ids:
            # Shared block - must use the exact ID from conversational agent
            correct_block_id = shared_block_ids[label]
        elif current_block_id:
            # Block exists and it's not a shared block requiring specific ID - keep it
            continue
        elif label in existing_blocks:
            # Use existing block from system
            correct_block_id = existing_blocks[label].id
        else:
            # Need to create new block
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
    shared_block_ids: dict[str, str] | None = None,
) -> str:
    """Create a new agent from scratch."""
    logger.info("Provisioning new agent: %s", spec.name)

    # Collect block IDs
    block_ids: list[str] = []

    # Shared blocks - use explicit IDs if provided, otherwise reuse existing or create
    logger.info("Setting up shared blocks...")
    for block_def in spec.shared_blocks:
        if shared_block_ids and block_def.label in shared_block_ids:
            # Use the exact block ID from the conversational agent
            block_id = shared_block_ids[block_def.label]
            logger.info("  Using shared block: %s (%s)", block_def.label, block_id)
        else:
            block_id = await find_or_create_block(client, block_def, existing_blocks)
        block_ids.append(block_id)

    # Unique blocks - always create fresh
    logger.info("Setting up unique blocks...")
    for block_def in spec.unique_blocks:
        block = await client.blocks.create(
            label=block_def.label,
            value=block_def.initial_value,
            description=block_def.description,
            limit=block_def.limit,
            read_only=block_def.read_only,
        )
        logger.info("  Created unique block: %s (%s)", block_def.label, block.id)
        block_ids.append(block.id)

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


async def find_conversational_agent_archive(
    client: AsyncLetta,
    base_name: str,
) -> str | None:
    """Find the archive attached to the conversational agent.

    Args:
        client: Letta client.
        base_name: The base agent name (e.g., "Corindel").

    Returns:
        Archive ID if found, None otherwise.
    """
    # Find the conversational agent by name
    async for agent in client.agents.list(name=base_name):
        # Get archives attached to this agent
        async for archive in client.archives.list(agent_id=agent.id):
            logger.info(
                "  Found archive %s (%s) from conversational agent %s",
                archive.name,
                archive.id,
                agent.name,
            )
            return archive.id
    return None


async def get_conversational_agent_shared_blocks(
    client: AsyncLetta,
    base_name: str,
    shared_block_labels: set[str],
) -> dict[str, str]:
    """Get the block IDs for shared blocks from the conversational agent.

    For reflector agents, we need to attach the SAME blocks (by ID) that the
    conversational agent uses, not just blocks with the same label.

    Args:
        client: Letta client.
        base_name: The base agent name (e.g., "Corindel").
        shared_block_labels: Set of labels to look for (e.g., {"persona", "human"}).

    Returns:
        Dict mapping label -> block_id for the shared blocks.
    """
    # Find the conversational agent by name
    async for agent in client.agents.list(name=base_name):
        if agent.name == base_name:
            shared_blocks: dict[str, str] = {}
            async for block in client.agents.blocks.list(agent_id=agent.id):
                if block.label in shared_block_labels:
                    shared_blocks[block.label] = block.id
                    logger.info(
                        "  Found shared block %s (%s) from conversational agent",
                        block.label,
                        block.id,
                    )
            return shared_blocks
    return {}


async def _run_provisioning(
    client: AsyncLetta,
    agent_type: str,
    base_name: str,
) -> int:
    """Run agent provisioning logic.

    Args:
        client: Letta client.
        agent_type: Type of agent ("conversational", "reflector", or "insights").
        base_name: Base name for the agent.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    # Load system prompt from database
    logger.info("Loading system prompt for %s from database...", agent_type)
    try:
        system_prompt = await get_system_prompt(agent_type)
        logger.info("  Loaded prompt (%d chars)", len(system_prompt))
    except ValueError as e:
        logger.error("Failed to load system prompt: %s", e)
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

    # Create spec using factory methods with DB-loaded prompt
    if agent_type == "conversational":
        spec = create_conversational_agent(base_name, system_prompt)
    elif agent_type == "insights":
        spec = create_background_insights_agent(base_name, system_prompt)
    else:
        spec = create_reflector_agent(base_name, system_prompt)

    # Handle archive and shared blocks based on agent type
    archive_id: str | None = None
    shared_block_ids: dict[str, str] | None = None

    if agent_type == "conversational":
        # For conversational agent: create a new archive with the agent's name
        logger.info("Setting up shared archive...")
        archive_id = await find_or_create_archive(client, base_name, existing_archives)
    else:
        # For subsidiary agents: find and attach the conversational agent's archive and blocks
        logger.info("Looking for conversational agent's archive...")
        archive_id = await find_conversational_agent_archive(client, base_name)
        if not archive_id:
            logger.error(
                "Cannot provision %s agent: conversational agent '%s' not found "
                "or has no archive. Provision the conversational agent first.",
                agent_type,
                base_name,
            )
            return 1

        # Get the shared block IDs from the conversational agent
        logger.info("Looking for conversational agent's shared blocks...")
        shared_labels = {b.label for b in spec.shared_blocks}
        shared_block_ids = await get_conversational_agent_shared_blocks(
            client, base_name, shared_labels
        )
        if not shared_block_ids:
            logger.error(
                "Cannot provision %s agent: conversational agent '%s' has no shared blocks.",
                agent_type,
                base_name,
            )
            return 1

    agent_id = await provision_agent(
        client, spec, existing_blocks, archive_id, shared_block_ids
    )

    # For insights agent: attach its background_insights block to the conversational agent
    if agent_type == "insights":
        logger.info("Attaching background_insights block to conversational agent...")
        await _attach_block_to_conversational_agent(
            client, base_name, agent_id, "background_insights"
        )

    logger.info("Done! Agent ID: %s", agent_id)

    return 0


async def _attach_block_to_conversational_agent(
    client: AsyncLetta,
    base_name: str,
    source_agent_id: str,
    block_label: str,
) -> None:
    """Attach a block from a subsidiary agent to the conversational agent.

    This enables the conversational agent to see blocks managed by other agents.
    If the conversational agent has a different block with the same label,
    it will be detached and replaced with the correct one.

    Args:
        client: Letta client.
        base_name: The base agent name (e.g., "Corindel").
        source_agent_id: Agent ID that owns the block.
        block_label: Label of the block to attach.
    """
    # Find the block on the source agent
    block_id: str | None = None
    async for block in client.agents.blocks.list(agent_id=source_agent_id):
        if block.label == block_label:
            block_id = block.id
            break

    if not block_id:
        logger.warning("  Block '%s' not found on agent %s", block_label, source_agent_id)
        return

    # Find the conversational agent and check for existing block with same label
    conv_agent_id: str | None = None
    existing_block_id: str | None = None
    async for agent in client.agents.list(name=base_name):
        if agent.name == base_name:
            conv_agent_id = agent.id
            # Check if conversational agent already has a block with this label
            async for existing_block in client.agents.blocks.list(agent_id=agent.id):
                if existing_block.label == block_label:
                    existing_block_id = existing_block.id
                    break
            break

    if not conv_agent_id:
        logger.warning("  Conversational agent '%s' not found", base_name)
        return

    # Check if the correct block is already attached
    if existing_block_id == block_id:
        logger.info("  Block '%s' (%s) already correctly attached to conversational agent", block_label, block_id)
        return

    # If a different block with the same label exists, detach it first
    if existing_block_id:
        logger.info("  Detaching incorrect block '%s' (%s) from conversational agent", block_label, existing_block_id)
        await client.agents.blocks.detach(agent_id=conv_agent_id, block_id=existing_block_id)

    # Attach the correct block
    await client.agents.blocks.attach(agent_id=conv_agent_id, block_id=block_id)
    logger.info("  Attached block '%s' (%s) to conversational agent", block_label, block_id)


async def main() -> int:
    """Main entry point for provisioning CLI."""
    parser = argparse.ArgumentParser(description="Provision Kairix agents")
    parser.add_argument(
        "--type",
        choices=["conversational", "reflector", "insights"],
        help="Type of agent to provision",
    )
    parser.add_argument(
        "--name",
        required=False,
        help="Base agent name (required when provisioning)",
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

    if not args.type:
        parser.error("--type is required when provisioning an agent")

    if not args.name:
        parser.error("--name is required when provisioning an agent")

    return await _run_provisioning(client, args.type, args.name)


def cli() -> None:
    """Entry point for the CLI."""
    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    cli()
