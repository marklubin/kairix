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
from kairix_agent.worker.jobs.insights import _check_agent_insights

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def _run_insights(agent_id: str, letta_url: str) -> dict[str, Any]:
    """Run insights job for a specific agent."""
    logger.info("Running insights job for agent %s", agent_id)

    # Just verify the agent exists
    _ = await get_agent_config(agent_id=agent_id, letta_url=letta_url)

    client = AsyncLetta(base_url=letta_url)
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
    args = parser.parse_args()

    result = asyncio.run(_run_insights(args.agent_id, args.letta_url))
    sys.exit(0 if result.get("status") in ("ok", "skipped") else 1)


def run_summarize() -> None:
    """CLI entry point for test-summarize.

    NOTE: This is now a no-op placeholder. Session summarization is triggered
    automatically via session_boundary job when a session ends.
    """
    logger.info("test-summarize is deprecated - use session boundary detection instead")
    sys.exit(0)
