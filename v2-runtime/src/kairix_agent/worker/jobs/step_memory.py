"""Step memory blocks job.

After session summarization, this job runs BlockManagerAgents in parallel
to consider updates to persona, human, and world blocks. Each agent sees
all 3 blocks but only updates its designated target.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from letta_client import AsyncLetta

from kairix_agent.events import EventType, emit_context_state, publish_event
from kairix_agent.llm import BlockManagerAgent
from kairix_agent.llm.configs import (
    HUMAN_STEP_CONFIG,
    PERSONA_STEP_CONFIG,
    WORLD_STEP_CONFIG,
)
from kairix_agent.llm.tools import handle_search_kp3

if TYPE_CHECKING:
    from saq.types import Context

    from kairix_agent.llm.block_manager import BlockManagerConfig

logger = logging.getLogger(__name__)

# Job name constant for enqueuing
STEP_MEMORY_JOB = "step_memory_blocks"


@dataclass
class StepResult:
    """Result of a single block step operation."""

    block_label: str
    updated: bool
    new_value: str | None
    passage_id: str | None
    searched_kp3: bool
    error: str | None = None


async def _fetch_blocks(
    client: AsyncLetta,
    agent_id: str,
) -> dict[str, str]:
    """Fetch all memory blocks from Letta.

    Returns:
        Dict mapping block label to block value.
    """
    blocks: dict[str, str] = {}
    async for block in client.agents.blocks.list(agent_id=agent_id, order="asc"):
        label = block.label or "unknown"
        value = block.value or ""
        blocks[label] = value
        logger.debug("Fetched block %s: %d chars", label, len(value))

    return blocks


async def _run_step_agent(
    config: BlockManagerConfig,
    agent_id: str,
    client: AsyncLetta,
    blocks: dict[str, str],
    session_summary: str,
    metadata: dict[str, Any],
) -> StepResult:
    """Run a single step agent.

    Args:
        config: BlockManagerConfig for this agent.
        agent_id: Letta agent ID.
        client: Letta client.
        blocks: Dict of current block values.
        session_summary: The session summary to process.
        metadata: Extra metadata for KP3 storage.

    Returns:
        StepResult with outcome.
    """
    block_label = config.target_block
    searched_kp3 = False

    try:
        # Create agent and register search tool
        agent = BlockManagerAgent(config)

        # Wrap search handler to track usage
        async def tracked_search(query: str, limit: int = 5) -> str:
            nonlocal searched_kp3
            searched_kp3 = True
            return await handle_search_kp3(query, limit)

        agent.register_tool_handler("search_kp3", tracked_search)

        # Build template vars with all 3 blocks
        template_vars = {
            "persona_block": blocks.get("persona", ""),
            "human_block": blocks.get("human", ""),
            "world_block": blocks.get("world", ""),
            "session_summary": session_summary,
        }

        # Run the agent
        result = await agent.run(
            input_text=session_summary,
            agent_id=agent_id,
            letta_client=client,
            template_vars=template_vars,
            metadata=metadata,
        )

        # Check if update was needed
        no_update = result.upper().startswith("NO_UPDATE_NEEDED")

        return StepResult(
            block_label=block_label,
            updated=not no_update,
            new_value=result if not no_update else None,
            passage_id=None,  # TODO: capture from _store_to_kp3 if needed
            searched_kp3=searched_kp3,
        )

    except Exception as e:
        logger.exception("Error running step agent for %s", block_label)
        return StepResult(
            block_label=block_label,
            updated=False,
            new_value=None,
            passage_id=None,
            searched_kp3=searched_kp3,
            error=str(e),
        )


async def step_memory_blocks(
    _ctx: Context,
    *,
    agent_id: str,
    letta_url: str,
    session_summary: str,
    period_start: str,
    period_end: str,
) -> dict[str, object]:
    """Step session summary into persona, human, and world blocks.

    This job runs after session summarization. It:
    1. Fetches all 3 current blocks from Letta
    2. Runs 3 BlockManagerAgents in parallel (persona, human, world)
    3. Each agent sees all 3 blocks + summary + has search_kp3 tool
    4. Each agent decides: update needed or NO_UPDATE_NEEDED
    5. Publishes events for each block result
    6. Emits CONTEXT_STATE at end

    Args:
        ctx: SAQ job context.
        agent_id: The Letta agent ID.
        letta_url: The Letta server URL.
        session_summary: The session summary text to process.
        period_start: ISO timestamp of session start.
        period_end: ISO timestamp of session end.

    Returns:
        Status dict with results for each block.
    """
    logger.info(
        "Starting step_memory_blocks for agent %s (summary: %d chars)",
        agent_id,
        len(session_summary),
    )

    try:
        client = AsyncLetta(base_url=letta_url)

        # 1. Fetch all current blocks
        blocks = await _fetch_blocks(client, agent_id)
        logger.info(
            "Fetched %d blocks: %s",
            len(blocks),
            list(blocks.keys()),
        )

        # 2. Build metadata for KP3 storage
        metadata = {
            "period_start": period_start,
            "period_end": period_end,
        }

        # 3. Run all 3 step agents in parallel
        results = await asyncio.gather(
            _run_step_agent(
                PERSONA_STEP_CONFIG, agent_id, client, blocks, session_summary, metadata
            ),
            _run_step_agent(
                HUMAN_STEP_CONFIG, agent_id, client, blocks, session_summary, metadata
            ),
            _run_step_agent(
                WORLD_STEP_CONFIG, agent_id, client, blocks, session_summary, metadata
            ),
            return_exceptions=True,
        )

        # 4. Publish events for each result
        event_mapping = {
            "persona": EventType.PERSONA_STEP_COMPLETE,
            "human": EventType.HUMAN_STEP_COMPLETE,
            "world": EventType.WORLD_STEP_COMPLETE,
        }

        blocks_output: dict[str, object] = {}
        output: dict[str, object] = {"status": "ok", "blocks": blocks_output}

        for result in results:
            if isinstance(result, BaseException):
                logger.exception("Step agent raised exception: %s", result)
                continue

            # Type narrowed: result is StepResult
            step_result: StepResult = result
            event_type = event_mapping.get(step_result.block_label)
            if event_type:
                await publish_event(
                    agent_id=agent_id,
                    event_type=event_type,
                    payload={
                        "updated": step_result.updated,
                        "block_label": step_result.block_label,
                        "new_value": step_result.new_value,
                        "passage_id": step_result.passage_id,
                        "searched_kp3": step_result.searched_kp3,
                    },
                )
                logger.info(
                    "Published %s event: updated=%s, searched_kp3=%s",
                    event_type.value,
                    step_result.updated,
                    step_result.searched_kp3,
                )

            blocks_output[step_result.block_label] = {
                "updated": step_result.updated,
                "searched_kp3": step_result.searched_kp3,
                "error": step_result.error,
            }

        # 5. Emit context state update (blocks may have changed)
        await emit_context_state(agent_id=agent_id, letta_url=letta_url)

    except Exception as e:
        logger.exception("Error in step_memory_blocks for agent %s", agent_id)
        return {"status": "error", "error": str(e)}

    else:
        return output
