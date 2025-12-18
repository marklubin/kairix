"""Context state event emission helpers.

Provides functions to fetch agent memory blocks from Letta and emit
context_state events to connected WebSocket clients.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from letta_client import AsyncLetta

from kairix_agent.events.models import EventType
from kairix_agent.events.publisher import publish_event
from kairix_agent.server.events.connection_manager import connection_manager

logger = logging.getLogger(__name__)


async def fetch_agent_blocks(client: AsyncLetta, agent_id: str) -> list[dict[str, Any]]:
    """Fetch all memory blocks for an agent from Letta.

    Args:
        client: Letta client instance.
        agent_id: The agent ID to fetch blocks for.

    Returns:
        List of block dictionaries with label, value, and updated_at fields.
    """
    blocks: list[dict[str, Any]] = []
    async for block in client.agents.blocks.list(agent_id=agent_id):
        block_data: dict[str, Any] = {
            "label": block.label,
            "value": block.value,
        }

        # Include updated_at if available (not in SDK types but may exist at runtime)
        updated_at = getattr(block, "updated_at", None) or getattr(block, "last_updated", None)
        if updated_at is not None:
            block_data["updated_at"] = (
                updated_at.isoformat() if hasattr(updated_at, "isoformat") else str(updated_at)
            )
        else:
            block_data["updated_at"] = None

        blocks.append(block_data)

    return blocks


async def emit_context_state(
    agent_id: str,
    letta_url: str,
    *,
    persist: bool = True,
) -> None:
    """Fetch blocks from Letta and emit context_state event.

    For persisted events, only lightweight metadata (block_count) is stored
    in the database. The event listener will fetch fresh block data when
    dispatching to clients.

    For ephemeral events (persist=False), the full block data is sent directly
    to connected clients without database storage.

    Args:
        agent_id: The conversational agent ID.
        letta_url: Letta server URL.
        persist: If True, store lightweight event in DB. If False, send directly.
    """
    client = AsyncLetta(base_url=letta_url)
    blocks = await fetch_agent_blocks(client, agent_id)

    logger.info(
        "Fetched %d memory blocks for agent %s",
        len(blocks),
        agent_id,
    )

    full_payload = {"blocks": blocks}

    if persist:
        # Store lightweight metadata in DB
        # The listener will fetch fresh blocks when dispatching
        await publish_event(
            agent_id=agent_id,
            event_type=EventType.CONTEXT_STATE,
            payload={"block_count": len(blocks)},
        )
        logger.info("Published CONTEXT_STATE event for agent %s", agent_id)
    else:
        # Direct dispatch without DB storage (for on-connect)
        event_data = {
            "id": str(uuid4()),
            "agent_id": agent_id,
            "event_type": "context_state",
            "payload": full_payload,
            "created_at": datetime.now(UTC).isoformat(),
        }
        await connection_manager.dispatch(agent_id, event_data)
        logger.info("Dispatched ephemeral context_state to agent %s clients", agent_id)
