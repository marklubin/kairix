"""Service layer for voice configuration operations."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from kairix_agent.config import Config
from kairix_agent.voices.models import AgentVoiceSettings, Voice

logger = logging.getLogger(__name__)

_engine = create_async_engine(Config.DATABASE_URL.value, echo=False)
_async_session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


# --- Voice CRUD ---


async def list_voices() -> list[Voice]:
    """List all available voices."""
    async with _async_session() as db:
        result = await db.execute(select(Voice).order_by(Voice.name))
        return list(result.scalars().all())


async def get_voice(voice_id: str) -> Voice | None:
    """Get a voice by ID."""
    async with _async_session() as db:
        result = await db.execute(select(Voice).where(Voice.id == voice_id))
        return result.scalar_one_or_none()


async def create_voice(
    name: str,
    provider_voice_id: str,
    provider: str = "cartesia",
    description: str | None = None,
) -> Voice:
    """Create a new voice."""
    async with _async_session() as db:
        voice = Voice(
            name=name,
            provider_voice_id=provider_voice_id,
            provider=provider,
            description=description,
        )
        db.add(voice)
        await db.commit()
        await db.refresh(voice)
        return voice


async def update_voice(voice_id: str, **kwargs: object) -> Voice | None:
    """Update a voice."""
    async with _async_session() as db:
        result = await db.execute(select(Voice).where(Voice.id == voice_id))
        voice = result.scalar_one_or_none()
        if voice is None:
            return None
        for key, value in kwargs.items():
            if value is not None:
                setattr(voice, key, value)
        await db.commit()
        await db.refresh(voice)
        return voice


async def delete_voice(voice_id: str) -> bool:
    """Delete a voice."""
    async with _async_session() as db:
        result = await db.execute(select(Voice).where(Voice.id == voice_id))
        voice = result.scalar_one_or_none()
        if voice is None:
            return False
        await db.delete(voice)
        await db.commit()
        return True


# --- Agent Voice Settings ---


async def get_agent_voice(agent_id: str) -> Voice | None:
    """Get the voice configured for an agent.

    Checks in order:
    1. Legacy agent_voice_settings table (for backward compatibility)
    2. New unified agents table (if agent has voice_id set)
    """
    async with _async_session() as db:
        # First check legacy table
        result = await db.execute(
            select(AgentVoiceSettings)
            .options(selectinload(AgentVoiceSettings.voice))
            .where(AgentVoiceSettings.agent_id == agent_id)
        )
        settings = result.scalar_one_or_none()
        if settings and settings.voice:
            return settings.voice

        # Fall back to unified agents table
        from kairix_agent.agents.models import Agent

        result = await db.execute(
            select(Agent).where(Agent.letta_agent_id == agent_id)
        )
        agent = result.scalar_one_or_none()
        if agent and agent.voice_id:
            voice_result = await db.execute(
                select(Voice).where(Voice.id == agent.voice_id)
            )
            voice = voice_result.scalar_one_or_none()
            if voice:
                logger.debug("Voice lookup from agents table: agent_id=%s, voice=%s", agent_id, voice.name)
                return voice

        return None


async def set_agent_voice(agent_id: str, voice_id: str) -> AgentVoiceSettings:
    """Set or update the voice for an agent."""
    async with _async_session() as db:
        result = await db.execute(
            select(AgentVoiceSettings).where(AgentVoiceSettings.agent_id == agent_id)
        )
        settings = result.scalar_one_or_none()
        if settings:
            settings.voice_id = voice_id
        else:
            settings = AgentVoiceSettings(agent_id=agent_id, voice_id=voice_id)
            db.add(settings)
        await db.commit()
        await db.refresh(settings)
        return settings
