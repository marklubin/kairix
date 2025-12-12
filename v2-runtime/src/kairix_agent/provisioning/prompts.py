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


async def get_system_prompt(agent_type: str) -> str:
    """Load system prompt from database by agent type.

    Args:
        agent_type: The type of agent ("conversational", "reflector", "insights").

    Returns:
        The system prompt text.

    Raises:
        ValueError: If no prompt config exists for the given agent type.
    """
    async with _async_session() as session:
        result = await session.execute(
            select(AgentDefinition).where(AgentDefinition.agent_type == agent_type)
        )
        config = result.scalar_one_or_none()

        if config is None:
            msg = f"No prompt config for agent_type: {agent_type}"
            raise ValueError(msg)

        logger.debug("Loaded system prompt for %s (%d chars)", agent_type, len(config.system_prompt))
        return config.system_prompt