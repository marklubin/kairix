"""Manual test runners for background jobs - bypasses SAQ for direct testing."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from typing import Any

from letta_client import AsyncLetta

from kairix_agent.agent_config import get_agent_config
from kairix_agent.config import Config
from kairix_agent.llm import BlockManagerAgent
from kairix_agent.llm.configs import INSIGHTS_CONFIG
from kairix_agent.llm.tools import handle_search_kp3
from kairix_agent.worker.jobs.insights import _check_agent_insights
from kairix_agent.worker.jobs.transcript import format_transcript

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

RECENT_MESSAGE_COUNT = 10


async def _run_insights(agent_id: str, letta_url: str, *, force: bool = False) -> dict[str, Any]:
    """Run insights job for a specific agent."""
    logger.info("Running insights job for agent %s (force=%s)", agent_id, force)

    # Just verify the agent exists
    _ = await get_agent_config(agent_id=agent_id, letta_url=letta_url)

    client = AsyncLetta(base_url=letta_url)

    if force:
        # Bypass activity check - run directly
        logger.info("Force mode: bypassing activity check")

        all_messages: list[Any] = [
            msg
            async for msg in client.agents.messages.list(
                agent_id=agent_id,
                order="asc",
                order_by="created_at",
            )
        ]
        messages = all_messages[-RECENT_MESSAGE_COUNT:] if all_messages else []

        if not messages:
            logger.info("No messages found")
            return {"status": "skipped", "reason": "no_messages"}

        logger.info("Got %d messages (from %d total)", len(messages), len(all_messages))

        # Format transcript
        conversation_text = format_transcript(messages)
        logger.info("Transcript:\n%s", conversation_text[:500])

        # Create insights agent with search tool
        insights_agent = BlockManagerAgent(INSIGHTS_CONFIG)
        insights_agent.register_tool_handler("search_kp3", handle_search_kp3)

        # Run
        response = await insights_agent.run(
            input_text=conversation_text,
            agent_id=agent_id,
            letta_client=client,
            template_vars={"conversation": conversation_text},
        )

        logger.info("Response (%d chars): %s", len(response), response)
        return {"status": "ok", "response": response, "forced": True}
    else:
        result = await _check_agent_insights(
            client=client,
            agent_id=agent_id,
            letta_url=letta_url,
        )
        logger.info("Result: %s", result)
        return dict(result)


def run_insights() -> None:
    """CLI entry point for test-insights."""
    parser = argparse.ArgumentParser(description="Run insights job for an agent")
    parser.add_argument("--agent-id", required=True, help="Conversational agent ID")
    parser.add_argument("--letta-url", default=Config.LETTA_BASE_URL.value, help="Letta server URL")
    parser.add_argument("--force", action="store_true", help="Bypass activity check and run directly")
    args = parser.parse_args()

    result = asyncio.run(_run_insights(args.agent_id, args.letta_url, force=args.force))
    sys.exit(0 if result.get("status") in ("ok", "skipped") else 1)


def run_summarize() -> None:
    """CLI entry point for test-summarize.

    NOTE: This is now a no-op placeholder. Session summarization is triggered
    automatically via session_boundary job when a session ends.
    """
    logger.info("test-summarize is deprecated - use session boundary detection instead")
    sys.exit(0)
