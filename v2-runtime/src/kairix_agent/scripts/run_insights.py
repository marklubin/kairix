"""Manual runner for insights job - for testing."""

from __future__ import annotations

import asyncio
import logging

from kairix_agent.worker.jobs.insights import check_insights_relevance
from kairix_agent.worker.settings import MONITORED_AGENTS

logging.basicConfig(level=logging.DEBUG)


async def _run() -> None:
    result = await check_insights_relevance(
        None,  # type: ignore[arg-type]
        agents=MONITORED_AGENTS,
    )
    print(f"\nResult: {result}")  # noqa: T201


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
