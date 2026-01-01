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

# Log truncation constants
LOG_PREVIEW_LENGTH = 300
LOG_RESPONSE_LENGTH = 500


@dataclass
class StepResult:
    """Result of a single block step operation."""

    block_label: str
    updated: bool
    new_value: str | None
    rationale: str | None  # Reasoning for update or non-update
    passage_id: str | None
    searched_kp3: bool
    error: str | None = None


def _parse_step_response(response: str) -> tuple[bool, str | None, str | None]:
    """Parse step agent response to extract update status, rationale, and new value.

    Expected formats:
    - "UPDATING: <rationale>\\n\\n<new block content>"
    - "NO_UPDATE_NEEDED: <rationale>"

    Returns:
        Tuple of (updated, rationale, new_value)
    """
    response = response.strip()

    if response.upper().startswith("UPDATING:"):
        # Extract rationale and new value
        content = response[len("UPDATING:") :].strip()
        # Split on double newline to separate rationale from new block content
        parts = content.split("\n\n", 1)
        expected_parts = 2
        if len(parts) == expected_parts:
            rationale = parts[0].strip()
            new_value = parts[1].strip()
        else:
            # No clear separation - treat entire content as new value
            rationale = "Update triggered"
            new_value = content
        return True, rationale, new_value

    if response.upper().startswith("NO_UPDATE_NEEDED:"):
        # Extract rationale
        rationale = response[len("NO_UPDATE_NEEDED:") :].strip()
        return False, rationale, None

    # Legacy format - just NO_UPDATE_NEEDED without colon
    if response.upper().startswith("NO_UPDATE_NEEDED"):
        return False, "No rationale provided", None

    # Treat as update if no prefix (legacy format)
    return True, "Update triggered (legacy format)", response


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

    logger.info(
        "[%s] Starting step agent for block '%s'",
        agent_id,
        block_label,
    )
    logger.debug(
        "[%s] Current %s block: %d chars",
        agent_id,
        block_label,
        len(blocks.get(block_label, "")),
    )

    try:
        # Create agent and register search tool
        agent = BlockManagerAgent(config)

        # Wrap search handler to track usage and log
        # Captures agent_id from outer scope to scope searches to this agent
        async def tracked_search(query: str, limit: int = 5) -> str:
            nonlocal searched_kp3
            searched_kp3 = True
            logger.info(
                "[%s] %s agent searching KP3: query='%s', limit=%d",
                agent_id,
                block_label,
                query,
                limit,
            )
            result = await handle_search_kp3(query, limit, agent_id=agent_id)
            logger.debug(
                "[%s] %s agent search returned %d chars",
                agent_id,
                block_label,
                len(result),
            )
            return result

        agent.register_tool_handler("search_kp3", tracked_search)

        # Build template vars with all 3 blocks
        template_vars = {
            "persona_block": blocks.get("persona", ""),
            "human_block": blocks.get("human", ""),
            "world_block": blocks.get("world", ""),
            "session_summary": session_summary,
        }

        logger.debug(
            "[%s] %s agent template vars: persona=%d chars, human=%d chars, world=%d chars",
            agent_id,
            block_label,
            len(template_vars["persona_block"]),
            len(template_vars["human_block"]),
            len(template_vars["world_block"]),
        )

        # Run the agent
        logger.info("[%s] Running %s step agent...", agent_id, block_label)
        result = await agent.run(
            input_text=session_summary,
            agent_id=agent_id,
            letta_client=client,
            template_vars=template_vars,
            metadata=metadata,
        )

        logger.debug(
            "[%s] %s agent raw response (%d chars): %s",
            agent_id,
            block_label,
            len(result),
            result[:LOG_RESPONSE_LENGTH] + "..."
            if len(result) > LOG_RESPONSE_LENGTH
            else result,
        )

        # Parse response to extract update status, rationale, and new value
        updated, rationale, new_value = _parse_step_response(result)

        # Log the decision with rationale
        if updated:
            logger.info(
                "[%s] %s block UPDATING - Rationale: %s",
                agent_id,
                block_label.upper(),
                rationale,
            )
            logger.info(
                "[%s] %s new value: %d chars",
                agent_id,
                block_label.upper(),
                len(new_value) if new_value else 0,
            )
        else:
            logger.info(
                "[%s] %s block NO UPDATE - Rationale: %s",
                agent_id,
                block_label.upper(),
                rationale,
            )

        return StepResult(
            block_label=block_label,
            updated=updated,
            new_value=new_value,
            rationale=rationale,
            passage_id=None,  # TODO: capture from _store_to_kp3 if needed
            searched_kp3=searched_kp3,
        )

    except Exception as e:
        logger.exception(
            "[%s] Error running step agent for %s",
            agent_id,
            block_label,
        )
        return StepResult(
            block_label=block_label,
            updated=False,
            new_value=None,
            rationale=None,
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
    4. Each agent decides: update needed or NO_UPDATE_NEEDED (with rationale)
    5. Publishes events for each block result (including rationale)
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
        "[%s] ========== STARTING STEP_MEMORY_BLOCKS ==========",
        agent_id,
    )
    logger.info(
        "[%s] Session period: %s to %s",
        agent_id,
        period_start,
        period_end,
    )
    logger.info(
        "[%s] Summary length: %d chars",
        agent_id,
        len(session_summary),
    )
    logger.debug(
        "[%s] Summary preview: %s",
        agent_id,
        session_summary[:LOG_PREVIEW_LENGTH] + "..."
        if len(session_summary) > LOG_PREVIEW_LENGTH
        else session_summary,
    )

    try:
        client = AsyncLetta(base_url=letta_url)

        # 1. Fetch all current blocks
        logger.info("[%s] Fetching current memory blocks...", agent_id)
        blocks = await _fetch_blocks(client, agent_id)
        logger.info(
            "[%s] Fetched %d blocks: %s",
            agent_id,
            len(blocks),
            list(blocks.keys()),
        )
        for label, value in blocks.items():
            logger.debug("[%s] Block '%s': %d chars", agent_id, label, len(value))

        # 2. Build metadata for KP3 storage
        metadata = {
            "period_start": period_start,
            "period_end": period_end,
        }

        # 3. Run all 3 step agents in parallel
        logger.info("[%s] Running 3 step agents in parallel...", agent_id)
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
        logger.info("[%s] All 3 step agents completed", agent_id)

        # 4. Publish events for each result
        event_mapping = {
            "persona": EventType.PERSONA_STEP_COMPLETE,
            "human": EventType.HUMAN_STEP_COMPLETE,
            "world": EventType.WORLD_STEP_COMPLETE,
        }

        blocks_output: dict[str, object] = {}
        output: dict[str, object] = {"status": "ok", "blocks": blocks_output}

        updates_count = 0
        errors_count = 0

        for result in results:
            if isinstance(result, BaseException):
                logger.error(
                    "[%s] Step agent raised exception: %s",
                    agent_id,
                    result,
                )
                errors_count += 1
                continue

            # Type narrowed: result is StepResult
            step_result: StepResult = result

            if step_result.error:
                errors_count += 1
            elif step_result.updated:
                updates_count += 1

            event_type = event_mapping.get(step_result.block_label)
            if event_type:
                await publish_event(
                    agent_id=agent_id,
                    event_type=event_type,
                    payload={
                        "updated": step_result.updated,
                        "block_label": step_result.block_label,
                        "new_value": step_result.new_value,
                        "rationale": step_result.rationale,
                        "passage_id": step_result.passage_id,
                        "searched_kp3": step_result.searched_kp3,
                    },
                )
                logger.info(
                    "[%s] Published %s event: updated=%s, searched_kp3=%s",
                    agent_id,
                    event_type.value,
                    step_result.updated,
                    step_result.searched_kp3,
                )

            blocks_output[step_result.block_label] = {
                "updated": step_result.updated,
                "rationale": step_result.rationale,
                "searched_kp3": step_result.searched_kp3,
                "error": step_result.error,
            }

        # 5. Emit context state update (blocks may have changed)
        logger.info("[%s] Emitting context state update...", agent_id)
        await emit_context_state(agent_id=agent_id, letta_url=letta_url)

        logger.info(
            "[%s] ========== STEP_MEMORY_BLOCKS COMPLETE ==========",
            agent_id,
        )
        logger.info(
            "[%s] Results: %d updates, %d no-updates, %d errors",
            agent_id,
            updates_count,
            3 - updates_count - errors_count,
            errors_count,
        )

    except Exception as e:
        logger.exception(
            "[%s] Error in step_memory_blocks",
            agent_id,
        )
        return {"status": "error", "error": str(e)}

    else:
        return output
