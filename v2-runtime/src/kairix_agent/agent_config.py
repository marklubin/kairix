"""Cached agent configuration loaded from Letta on first access.

This module provides a per-agent cache for agent configuration that is
loaded from Letta on first access. The cache is keyed by agent_id so
multiple agents can be monitored simultaneously.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from letta_client import AsyncLetta

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentConfig:
    """Cached configuration for an agent."""

    agent_id: str
    agent_name: str
    letta_url: str
    archive_id: str | None
    reflector_agent_id: str | None
    insights_agent_id: str | None


# Module-level cache keyed by agent_id
_agent_configs: dict[str, AgentConfig] = {}
_config_lock = asyncio.Lock()


async def get_agent_config(*, agent_id: str, letta_url: str) -> AgentConfig:
    """Get the cached agent configuration, loading from Letta on first access.

    Args:
        agent_id: The agent ID to load configuration for.
        letta_url: The Letta server URL.

    Returns:
        AgentConfig with agent details including archive ID.
    """
    # Check cache first (no lock needed for read)
    if agent_id in _agent_configs:
        return _agent_configs[agent_id]

    async with _config_lock:
        # Double-check after acquiring lock
        if agent_id in _agent_configs:
            return _agent_configs[agent_id]

        logger.info("Loading agent configuration from Letta for agent %s...", agent_id)

        client = AsyncLetta(base_url=letta_url)

        # Get agent details
        agent = await client.agents.retrieve(agent_id=agent_id)
        agent_name = agent.name

        # Find attached archive
        archive_id: str | None = None
        async for archive in client.archives.list(agent_id=agent_id):
            archive_id = archive.id
            logger.info("  Found archive: %s (%s)", archive.name, archive.id)
            break  # Just need the first one

        # Find reflector agent (name pattern: "{agent_name}-Reflector")
        reflector_name = f"{agent_name}-Reflector"
        reflector_agent_id: str | None = None
        async for reflector in client.agents.list(name=reflector_name):
            if reflector.name == reflector_name:
                reflector_agent_id = reflector.id
                logger.info(
                    "  Found reflector agent: %s (%s)",
                    reflector.name,
                    reflector.id,
                )
                break

        # Find insights agent (name pattern: "{agent_name}-BackgroundInsights")
        insights_name = f"{agent_name}-BackgroundInsights"
        insights_agent_id: str | None = None
        async for insights_agent in client.agents.list(name=insights_name):
            if insights_agent.name == insights_name:
                insights_agent_id = insights_agent.id
                logger.info(
                    "  Found insights agent: %s (%s)",
                    insights_agent.name,
                    insights_agent.id,
                )
                break

        config = AgentConfig(
            agent_id=agent_id,
            agent_name=agent_name,
            letta_url=letta_url,
            archive_id=archive_id,
            reflector_agent_id=reflector_agent_id,
            insights_agent_id=insights_agent_id,
        )

        _agent_configs[agent_id] = config

        logger.info(
            "Agent config loaded: name=%s, archive=%s, reflector=%s, insights=%s",
            config.agent_name,
            config.archive_id,
            config.reflector_agent_id,
            config.insights_agent_id,
        )

        return config


def clear_agent_config(agent_id: str | None = None) -> None:
    """Clear the cached agent config.

    Args:
        agent_id: Specific agent to clear, or None to clear all.
    """
    if agent_id is None:
        _agent_configs.clear()
    elif agent_id in _agent_configs:
        del _agent_configs[agent_id]
