"""Agent discovery for worker jobs."""

from __future__ import annotations

import logging
from typing import Any

from letta_client import Letta

from kairix_agent.config import Config

logger = logging.getLogger(__name__)


def get_all_agents() -> list[dict[str, Any]]:
    """Fetch all agents from Letta API.

    Returns:
        List of agent configs with agent_id and letta_url.
    """
    letta_url = Config.LETTA_BASE_URL.value
    try:
        client = Letta(base_url=letta_url)
        agents = [{"agent_id": agent.id, "letta_url": letta_url} for agent in client.agents.list()]
    except Exception:
        logger.exception("Failed to fetch agents from Letta API")
        return []
    else:
        logger.info("Discovered %d agents from Letta API", len(agents))
        return agents
