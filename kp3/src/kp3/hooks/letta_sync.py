"""Letta sync hook for pushing world model state to Letta core memory.

Uses the Letta Python SDK to update agent memory blocks.
Blocks must be pre-provisioned - this module will not auto-create them.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from letta_client import Letta  # type: ignore[import-untyped]

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
        # Use agents.blocks.update which takes label and agent_id directly
        # This will raise an error if the block doesn't exist
        client.agents.blocks.update(
            block_label,
            agent_id=agent_id,
            value=content,
        )
        logger.info("Updated Letta block %s for agent %s", block_label, agent_id)

    except Exception as e:
        # Check if this is a "not found" error
        error_msg = str(e).lower()
        if "not found" in error_msg or "404" in error_msg:
            raise LettaSyncError(
                f"Block '{block_label}' not found for agent {agent_id}. "
                f"Blocks must be pre-provisioned before sync can occur."
            ) from e
        raise LettaSyncError(f"Failed to update Letta block: {e}") from e
