"""Letta sync hook for pushing world model state to Letta core memory.

Uses the Letta Python SDK to update agent memory blocks.
Blocks must be pre-provisioned - this module will not auto-create them.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from letta import Letta  # type: ignore[import-untyped]

from kp3.config import get_settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Lazily initialized Letta client
_client: Any = None


def _get_client() -> Any:  # noqa: ANN401
    """Get or create the Letta client."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = Letta(base_url=settings.LETTA_BASE_URL)
    return _client


class LettaSyncError(Exception):
    """Error during Letta sync operation."""

    pass


async def update_letta_block(
    agent_id: str,
    block_label: str,
    content: str,
) -> None:
    """Update a Letta core memory block.

    Args:
        agent_id: Letta agent ID
        block_label: Block label (human, persona, world)
        content: New content for the block

    Raises:
        LettaSyncError: If the block doesn't exist or update fails.
            Blocks must be pre-provisioned; this function will not create them.
    """
    client = _get_client()

    try:
        # Get the agent's memory blocks to find the block ID
        # The Letta SDK's agent.memory.blocks gives us access to blocks
        agent = client.agents.retrieve(agent_id)
        if not agent:
            raise LettaSyncError(f"Agent {agent_id} not found")

        # Find the block with matching label
        block_id = None
        for block in agent.memory.blocks:
            if block.label == block_label:
                block_id = block.id
                break

        if block_id is None:
            raise LettaSyncError(
                f"Block '{block_label}' not found for agent {agent_id}. "
                f"Blocks must be pre-provisioned before sync can occur."
            )

        # Update the block value
        client.blocks.modify(block_id=block_id, value=content)
        logger.info("Updated Letta block %s for agent %s", block_label, agent_id)

    except LettaSyncError:
        raise
    except Exception as e:
        raise LettaSyncError(f"Failed to update Letta block: {e}") from e
