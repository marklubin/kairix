"""System prompt loader from database."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from kairix_agent.config import Config
from kairix_agent.provisioning.models import AgentDefinition

logger = logging.getLogger(__name__)

# Async engine and session factory (lazy initialized)
_engine = create_async_engine(Config.DATABASE_URL.value, echo=False)
_async_session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def get_agent_definition(agent_type: str) -> AgentDefinition:
    """Load agent definition from database by agent type.

    Args:
        agent_type: The type of agent ("conversational", "reflector", "insights").

    Returns:
        The AgentDefinition containing system_prompt and block labels.

    Raises:
        ValueError: If no config exists for the given agent type.
    """
    async with _async_session() as session:
        result = await session.execute(
            select(AgentDefinition).where(AgentDefinition.agent_type == agent_type)
        )
        config = result.scalar_one_or_none()

        if config is None:
            msg = f"No agent definition for agent_type: {agent_type}"
            raise ValueError(msg)

        logger.debug(
            "Loaded agent definition for %s (prompt: %d chars, universal: %s, subagent: %s)",
            agent_type,
            len(config.system_prompt),
            config.universal_block_labels,
            config.subagent_block_labels,
        )
        return config


async def get_system_prompt(agent_type: str) -> str:
    """Load system prompt from database by agent type.

    Args:
        agent_type: The type of agent ("conversational", "reflector", "insights").

    Returns:
        The system prompt text.

    Raises:
        ValueError: If no prompt config exists for the given agent type.
    """
    definition = await get_agent_definition(agent_type)
    return definition.system_prompt
