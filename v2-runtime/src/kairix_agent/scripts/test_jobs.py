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
from kairix_agent.worker.jobs.summarize import summarize_session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def _run_insights(agent_id: str, letta_url: str) -> dict[str, Any]:
    """Run insights job for a specific agent."""
    logger.info("Running insights job for agent %s", agent_id)

    config = await get_agent_config(agent_id=agent_id, letta_url=letta_url)

    if not config.insights_agent_id:
        logger.error("No insights agent configured for %s", agent_id)
        return {"status": "error", "reason": "no_insights_agent"}

    client = AsyncLetta(base_url=letta_url)
    result = await _check_agent_insights(
        client=client,
        agent_id=agent_id,
        insights_agent_id=config.insights_agent_id,
    )

    logger.info("Result: %s", result)
    return result


async def _run_summarize(
    agent_id: str,
    letta_url: str,
    message_ids: list[str],
    period_start: str,
    period_end: str,
) -> dict[str, Any]:
    """Run summarization for a specific agent."""
    logger.info("Running summarization for agent %s", agent_id)

    config = await get_agent_config(agent_id=agent_id, letta_url=letta_url)

    if not config.reflector_agent_id:
        logger.error("No reflector agent configured for %s", agent_id)
        return {"status": "error", "reason": "no_reflector_agent"}

    if not config.archive_id:
        logger.error("No archive configured for %s", agent_id)
        return {"status": "error", "reason": "no_archive"}

    result = await summarize_session(
        None,  # type: ignore[arg-type]
        agent_id=agent_id,
        letta_url=letta_url,
        archive_id=config.archive_id,
        reflector_agent_id=config.reflector_agent_id,
        message_ids=message_ids,
        period_start=period_start,
        period_end=period_end,
    )

    logger.info("Result: %s", result)
    return result


def run_insights() -> None:
    """CLI entry point for test-insights."""
    parser = argparse.ArgumentParser(description="Run insights job for an agent")
    parser.add_argument("--agent-id", required=True, help="Conversational agent ID")
    parser.add_argument("--letta-url", default=Config.LETTA_BASE_URL.value, help="Letta server URL")
    args = parser.parse_args()

    result = asyncio.run(_run_insights(args.agent_id, args.letta_url))
    sys.exit(0 if result.get("status") in ("ok", "skipped") else 1)


def run_summarize() -> None:
    """CLI entry point for test-summarize."""
    parser = argparse.ArgumentParser(description="Run summarization for an agent")
    parser.add_argument("--agent-id", required=True, help="Conversational agent ID")
    parser.add_argument("--letta-url", default=Config.LETTA_BASE_URL.value, help="Letta server URL")
    parser.add_argument("--message-ids", required=True, help="Comma-separated message IDs")
    parser.add_argument("--period-start", required=True, help="ISO timestamp of period start")
    parser.add_argument("--period-end", required=True, help="ISO timestamp of period end")
    args = parser.parse_args()

    message_ids = [m.strip() for m in args.message_ids.split(",")]

    result = asyncio.run(_run_summarize(
        args.agent_id,
        args.letta_url,
        message_ids,
        args.period_start,
        args.period_end,
    ))
    sys.exit(0 if result.get("status") in ("ok", "skipped") else 1)
