"""Service layer for social channel operations."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from kairix_agent.config import Config
from kairix_agent.social.crypto import decrypt_credentials, encrypt_credentials
from kairix_agent.social.models import (
    EngagementLevel,
    NotificationChannel,
    NotificationPreference,
    SocialChannel,
    SocialChannelType,
    SocialInteraction,
    SocialTrigger,
    TriggerAction,
    TriggerType,
    TrustLevel,
)

_engine = create_async_engine(Config.DATABASE_URL.value, echo=False)
_async_session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


# =============================================================================
# Channel CRUD
# =============================================================================


async def list_channels(agent_id: str | None = None) -> list[SocialChannel]:
    """List social channels, optionally filtered by agent.

    Args:
        agent_id: Optional agent ID to filter by.

    Returns:
        List of social channels.
    """
    async with _async_session() as db:
        query = select(SocialChannel).order_by(SocialChannel.created_at.desc())
        if agent_id:
            query = query.where(SocialChannel.agent_id == agent_id)
        result = await db.execute(query)
        return list(result.scalars().all())


async def get_channel(channel_id: str) -> SocialChannel | None:
    """Get a channel by ID.

    Args:
        channel_id: Channel UUID.

    Returns:
        Channel if found, None otherwise.
    """
    async with _async_session() as db:
        result = await db.execute(
            select(SocialChannel)
            .options(selectinload(SocialChannel.triggers))
            .where(SocialChannel.id == channel_id)
        )
        return result.scalar_one_or_none()


async def get_agent_channel(
    agent_id: str, channel_type: SocialChannelType
) -> SocialChannel | None:
    """Get an agent's channel by type.

    Args:
        agent_id: Agent ID.
        channel_type: Type of social channel.

    Returns:
        Channel if found, None otherwise.
    """
    async with _async_session() as db:
        result = await db.execute(
            select(SocialChannel)
            .where(SocialChannel.agent_id == agent_id)
            .where(SocialChannel.channel_type == channel_type.value)
        )
        return result.scalar_one_or_none()


async def create_channel(
    agent_id: str,
    channel_type: SocialChannelType,
    handle: str,
    credentials: dict[str, Any],
    engagement_level: EngagementLevel = EngagementLevel.CONSERVATIVE,
    trust_level: TrustLevel = TrustLevel.LEARNING,
) -> SocialChannel:
    """Create a new social channel for an agent.

    Args:
        agent_id: Agent ID.
        channel_type: Type of social platform.
        handle: Social handle (e.g., @user.bsky.social).
        credentials: Platform credentials (will be encrypted).
        engagement_level: How actively to engage.
        trust_level: Approval requirements.

    Returns:
        Created channel.

    Raises:
        ValueError: If agent already has a channel of this type.
    """
    async with _async_session() as db:
        # Check for existing channel
        existing = await db.execute(
            select(SocialChannel)
            .where(SocialChannel.agent_id == agent_id)
            .where(SocialChannel.channel_type == channel_type.value)
        )
        if existing.scalar_one_or_none():
            msg = f"Agent {agent_id} already has a {channel_type.value} channel"
            raise ValueError(msg)

        channel = SocialChannel(
            agent_id=agent_id,
            channel_type=channel_type.value,
            handle=handle,
            credentials_encrypted=encrypt_credentials(credentials),
            engagement_level=engagement_level.value,
            trust_level=trust_level.value,
        )
        db.add(channel)

        # Create default triggers for this channel
        await _create_default_triggers(db, channel)

        await db.commit()
        await db.refresh(channel)
        return channel


async def _create_default_triggers(db: AsyncSession, channel: SocialChannel) -> None:
    """Create default triggers for a new channel."""
    # Direct mention trigger - always enabled
    mention_trigger = SocialTrigger(
        channel_id=channel.id,
        trigger_type=TriggerType.DIRECT_MENTION.value,
        config={},
        action=TriggerAction.WAKE_AND_EVALUATE.value,
        cooldown_minutes=5,
    )
    db.add(mention_trigger)

    # Reply to post trigger
    reply_trigger = SocialTrigger(
        channel_id=channel.id,
        trigger_type=TriggerType.REPLY_TO_POST.value,
        config={},
        action=TriggerAction.WAKE_AND_EVALUATE.value,
        cooldown_minutes=5,
    )
    db.add(reply_trigger)


async def update_channel(
    channel_id: str,
    *,
    handle: str | None = None,
    credentials: dict[str, Any] | None = None,
    engagement_level: EngagementLevel | None = None,
    trust_level: TrustLevel | None = None,
    enabled: bool | None = None,
) -> SocialChannel | None:
    """Update a social channel.

    Args:
        channel_id: Channel UUID.
        handle: New handle (optional).
        credentials: New credentials (optional, will be encrypted).
        engagement_level: New engagement level (optional).
        trust_level: New trust level (optional).
        enabled: Enable/disable channel (optional).

    Returns:
        Updated channel if found, None otherwise.
    """
    async with _async_session() as db:
        result = await db.execute(
            select(SocialChannel).where(SocialChannel.id == channel_id)
        )
        channel = result.scalar_one_or_none()
        if channel is None:
            return None

        if handle is not None:
            channel.handle = handle
        if credentials is not None:
            channel.credentials_encrypted = encrypt_credentials(credentials)
        if engagement_level is not None:
            channel.engagement_level = engagement_level.value
        if trust_level is not None:
            channel.trust_level = trust_level.value
        if enabled is not None:
            channel.enabled = enabled

        await db.commit()
        await db.refresh(channel)
        return channel


async def delete_channel(channel_id: str) -> bool:
    """Delete a social channel.

    Args:
        channel_id: Channel UUID.

    Returns:
        True if deleted, False if not found.
    """
    async with _async_session() as db:
        result = await db.execute(
            select(SocialChannel).where(SocialChannel.id == channel_id)
        )
        channel = result.scalar_one_or_none()
        if channel is None:
            return False
        await db.delete(channel)
        await db.commit()
        return True


def get_decrypted_credentials(channel: SocialChannel) -> dict[str, Any]:
    """Decrypt and return credentials for a channel.

    Args:
        channel: Social channel with encrypted credentials.

    Returns:
        Decrypted credentials dictionary.
    """
    return decrypt_credentials(channel.credentials_encrypted)


# =============================================================================
# Trigger CRUD
# =============================================================================


async def list_triggers(channel_id: str) -> list[SocialTrigger]:
    """List triggers for a channel.

    Args:
        channel_id: Channel UUID.

    Returns:
        List of triggers.
    """
    async with _async_session() as db:
        result = await db.execute(
            select(SocialTrigger)
            .where(SocialTrigger.channel_id == channel_id)
            .order_by(SocialTrigger.created_at)
        )
        return list(result.scalars().all())


async def create_trigger(
    channel_id: str,
    trigger_type: TriggerType,
    action: TriggerAction,
    config: dict[str, Any] | None = None,
    cooldown_minutes: int = 30,
) -> SocialTrigger:
    """Create a new trigger for a channel.

    Args:
        channel_id: Channel UUID.
        trigger_type: Type of trigger.
        action: Action to take when fired.
        config: Trigger-specific configuration.
        cooldown_minutes: Minimum time between firings.

    Returns:
        Created trigger.
    """
    async with _async_session() as db:
        trigger = SocialTrigger(
            channel_id=channel_id,
            trigger_type=trigger_type.value,
            action=action.value,
            config=config or {},
            cooldown_minutes=cooldown_minutes,
        )
        db.add(trigger)
        await db.commit()
        await db.refresh(trigger)
        return trigger


async def update_trigger(
    trigger_id: str,
    *,
    config: dict[str, Any] | None = None,
    action: TriggerAction | None = None,
    cooldown_minutes: int | None = None,
    enabled: bool | None = None,
) -> SocialTrigger | None:
    """Update a trigger.

    Args:
        trigger_id: Trigger UUID.
        config: New configuration (optional).
        action: New action (optional).
        cooldown_minutes: New cooldown (optional).
        enabled: Enable/disable (optional).

    Returns:
        Updated trigger if found, None otherwise.
    """
    async with _async_session() as db:
        result = await db.execute(
            select(SocialTrigger).where(SocialTrigger.id == trigger_id)
        )
        trigger = result.scalar_one_or_none()
        if trigger is None:
            return None

        if config is not None:
            trigger.config = config
        if action is not None:
            trigger.action = action.value
        if cooldown_minutes is not None:
            trigger.cooldown_minutes = cooldown_minutes
        if enabled is not None:
            trigger.enabled = enabled

        await db.commit()
        await db.refresh(trigger)
        return trigger


async def delete_trigger(trigger_id: str) -> bool:
    """Delete a trigger.

    Args:
        trigger_id: Trigger UUID.

    Returns:
        True if deleted, False if not found.
    """
    async with _async_session() as db:
        result = await db.execute(
            select(SocialTrigger).where(SocialTrigger.id == trigger_id)
        )
        trigger = result.scalar_one_or_none()
        if trigger is None:
            return False
        await db.delete(trigger)
        await db.commit()
        return True


# =============================================================================
# Interaction Queries
# =============================================================================


async def list_interactions(
    channel_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[SocialInteraction]:
    """List interactions for a channel.

    Args:
        channel_id: Channel UUID.
        limit: Maximum number to return.
        offset: Number to skip.

    Returns:
        List of interactions.
    """
    async with _async_session() as db:
        result = await db.execute(
            select(SocialInteraction)
            .where(SocialInteraction.channel_id == channel_id)
            .order_by(SocialInteraction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())


async def get_interaction(interaction_id: str) -> SocialInteraction | None:
    """Get an interaction by ID.

    Args:
        interaction_id: Interaction UUID.

    Returns:
        Interaction if found, None otherwise.
    """
    async with _async_session() as db:
        result = await db.execute(
            select(SocialInteraction).where(SocialInteraction.id == interaction_id)
        )
        return result.scalar_one_or_none()


# =============================================================================
# Notification Preferences
# =============================================================================


async def get_notification_preferences(agent_id: str) -> NotificationPreference | None:
    """Get notification preferences for an agent.

    Args:
        agent_id: Agent ID.

    Returns:
        Preferences if found, None otherwise.
    """
    async with _async_session() as db:
        result = await db.execute(
            select(NotificationPreference).where(
                NotificationPreference.agent_id == agent_id
            )
        )
        return result.scalar_one_or_none()


async def set_notification_preferences(
    agent_id: str,
    *,
    channels_enabled: list[NotificationChannel] | None = None,
    digest_email: str | None = None,
    digest_frequency: str | None = None,
    mention_threshold: float | None = None,
) -> NotificationPreference:
    """Set or update notification preferences for an agent.

    Args:
        agent_id: Agent ID.
        channels_enabled: Enabled notification channels.
        digest_email: Email for digests.
        digest_frequency: Digest frequency (daily, weekly, etc.).
        mention_threshold: Importance threshold for voice mentions.

    Returns:
        Updated preferences.
    """
    async with _async_session() as db:
        result = await db.execute(
            select(NotificationPreference).where(
                NotificationPreference.agent_id == agent_id
            )
        )
        prefs = result.scalar_one_or_none()

        if prefs is None:
            prefs = NotificationPreference(agent_id=agent_id)
            db.add(prefs)

        if channels_enabled is not None:
            prefs.channels_enabled = [c.value for c in channels_enabled]
        if digest_email is not None:
            prefs.digest_email = digest_email
        if digest_frequency is not None:
            prefs.digest_frequency = digest_frequency
        if mention_threshold is not None:
            prefs.mention_threshold = mention_threshold

        await db.commit()
        await db.refresh(prefs)
        return prefs
