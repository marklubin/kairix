"""Social exploration job.

Fetches timeline and mentions from social platforms, stores interactions,
and triggers engagement evaluation for interesting posts.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from kairix_agent.config import Config
from kairix_agent.events import EventType, publish_event
from kairix_agent.social.channels import create_channel
from kairix_agent.social.models import (
    InteractionType,
    SocialChannel,
    SocialInteraction,
    SocialTrigger,
    TriggerAction,
    TriggerType,
)
from kairix_agent.worker.metrics import instrument_job

# Database session factory
_engine = create_async_engine(Config.DATABASE_URL.value, echo=False)
_async_session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

if TYPE_CHECKING:
    from saq.queue import Queue
    from saq.types import Context

    from kairix_agent.social.channels.base import SocialPost

logger = logging.getLogger(__name__)

# Job name constants for enqueuing
SOCIAL_EXPLORE_JOB = "social_explore"
SOCIAL_EVALUATE_JOB = "social_evaluate"

# Limits
TIMELINE_FETCH_LIMIT = 50
MENTION_FETCH_LIMIT = 20


async def _get_enabled_channels(db: AsyncSession) -> list[SocialChannel]:
    """Get all enabled social channels."""
    result = await db.execute(
        select(SocialChannel).where(SocialChannel.enabled == True)  # noqa: E712
    )
    return list(result.scalars().all())


async def _get_channel_triggers(
    db: AsyncSession, channel_id: str
) -> list[SocialTrigger]:
    """Get enabled triggers for a channel."""
    result = await db.execute(
        select(SocialTrigger)
        .where(SocialTrigger.channel_id == channel_id)
        .where(SocialTrigger.enabled == True)  # noqa: E712
    )
    return list(result.scalars().all())


async def _store_interaction(
    db: AsyncSession,
    channel_id: str,
    interaction_type: InteractionType,
    post: SocialPost,
) -> SocialInteraction:
    """Store a social interaction in the database."""
    interaction = SocialInteraction(
        channel_id=channel_id,
        interaction_type=interaction_type.value,
        external_post_id=post.external_id,
        external_author=post.author_handle,
        external_author_did=post.author_did,
        content_text=post.content,
        parent_post_id=post.parent_id,
        thread_root_id=post.root_id,
        extra_data={
            "reply_count": post.reply_count,
            "repost_count": post.repost_count,
            "like_count": post.like_count,
            "has_media": post.has_media,
            "created_at": post.created_at.isoformat(),
        },
    )
    db.add(interaction)
    await db.flush()
    return interaction


def _evaluate_triggers(
    triggers: list[SocialTrigger],
    post: SocialPost,
    is_mention: bool,
) -> list[tuple[SocialTrigger, str]]:
    """Evaluate which triggers match a post.

    Returns list of (trigger, reason) tuples.
    """
    matches: list[tuple[SocialTrigger, str]] = []

    for trigger in triggers:
        trigger_type = TriggerType(trigger.trigger_type)
        config = trigger.config or {}

        # Check cooldown
        if trigger.last_fired_at:
            cooldown = trigger.cooldown_minutes or 30
            elapsed = (datetime.now(UTC) - trigger.last_fired_at).total_seconds() / 60
            if elapsed < cooldown:
                continue

        # Evaluate by trigger type
        if trigger_type == TriggerType.DIRECT_MENTION and is_mention:
            matches.append((trigger, "direct_mention"))

        elif trigger_type == TriggerType.KEYWORD:
            pattern = config.get("pattern", "").lower()
            if pattern and pattern in post.content.lower():
                matches.append((trigger, f"keyword:{pattern}"))

        elif trigger_type == TriggerType.ACCOUNT_POST:
            watched = config.get("watched_handles", [])
            if post.author_handle in watched:
                matches.append((trigger, f"watched_account:{post.author_handle}"))

        elif trigger_type == TriggerType.ENGAGEMENT_THRESHOLD:
            min_likes = config.get("min_likes", 0)
            if post.like_count >= min_likes:
                matches.append((trigger, f"engagement:{post.like_count}_likes"))

    return matches


async def _explore_channel(
    db: AsyncSession,
    queue: Queue,
    channel: SocialChannel,
) -> dict[str, Any]:
    """Explore a single social channel.

    Args:
        db: Database session.
        queue: SAQ queue for enqueueing follow-up jobs.
        channel: Social channel to explore.

    Returns:
        Status dict with exploration results.
    """
    logger.info(
        "Exploring channel %s (%s) for agent %s",
        channel.handle,
        channel.channel_type,
        channel.agent_id,
    )

    # Create and authenticate channel
    try:
        social_channel = create_channel(channel)
        authenticated = await social_channel.authenticate()
        if not authenticated:
            logger.error("Failed to authenticate channel %s", channel.handle)
            return {"status": "auth_failed", "channel_id": channel.id}
    except Exception:
        logger.exception("Error creating channel %s", channel.handle)
        return {"status": "channel_error", "channel_id": channel.id}

    # Load triggers for this channel
    triggers = await _get_channel_triggers(db, channel.id)
    logger.info("Loaded %d triggers for channel %s", len(triggers), channel.handle)

    # Fetch timeline
    timeline_posts: list[SocialPost] = []
    try:
        posts, _cursor = await social_channel.get_timeline(limit=TIMELINE_FETCH_LIMIT)
        timeline_posts = posts
        logger.info("Fetched %d timeline posts", len(posts))
    except Exception:
        logger.exception("Error fetching timeline for %s", channel.handle)

    # Fetch mentions (since last check)
    mentions: list[SocialPost] = []
    try:
        mentions = await social_channel.get_mentions(
            since=channel.last_mention_check_at,
            limit=MENTION_FETCH_LIMIT,
        )
        logger.info("Fetched %d mentions since %s", len(mentions), channel.last_mention_check_at)
    except Exception:
        logger.exception("Error fetching mentions for %s", channel.handle)

    # Process and store interactions
    interactions_stored = 0
    triggers_fired = 0
    evaluate_jobs_enqueued = 0

    # Process timeline posts
    for post in timeline_posts:
        interaction = await _store_interaction(
            db, channel.id, InteractionType.TIMELINE_VIEW, post
        )
        interactions_stored += 1

        # Evaluate triggers
        matched_triggers = _evaluate_triggers(triggers, post, is_mention=False)
        for trigger, reason in matched_triggers:
            await _fire_trigger(db, queue, channel, trigger, interaction, reason)
            triggers_fired += 1

    # Process mentions (higher priority)
    for post in mentions:
        interaction = await _store_interaction(
            db, channel.id, InteractionType.MENTION_RECEIVED, post
        )
        interactions_stored += 1

        # Evaluate triggers - mentions get special treatment
        matched_triggers = _evaluate_triggers(triggers, post, is_mention=True)

        if matched_triggers:
            for trigger, reason in matched_triggers:
                await _fire_trigger(db, queue, channel, trigger, interaction, reason)
                triggers_fired += 1
        else:
            # Even without explicit triggers, mentions should be evaluated
            await queue.enqueue(
                SOCIAL_EVALUATE_JOB,
                agent_id=channel.agent_id,
                channel_id=channel.id,
                interaction_id=interaction.id,
                is_mention=True,
            )
            evaluate_jobs_enqueued += 1

    # Update channel timestamps
    channel.last_explored_at = datetime.now(UTC)
    if mentions:
        channel.last_mention_check_at = datetime.now(UTC)

    await db.commit()

    # Publish exploration complete event
    await publish_event(
        agent_id=channel.agent_id,
        event_type=EventType.SOCIAL_EXPLORE_COMPLETE,
        payload={
            "channel_type": channel.channel_type,
            "handle": channel.handle,
            "timeline_posts": len(timeline_posts),
            "mentions": len(mentions),
            "interactions_stored": interactions_stored,
            "triggers_fired": triggers_fired,
        },
    )

    return {
        "status": "ok",
        "channel_id": channel.id,
        "timeline_posts": len(timeline_posts),
        "mentions": len(mentions),
        "interactions_stored": interactions_stored,
        "triggers_fired": triggers_fired,
        "evaluate_jobs_enqueued": evaluate_jobs_enqueued,
    }


async def _fire_trigger(
    db: AsyncSession,
    queue: Queue,
    channel: SocialChannel,
    trigger: SocialTrigger,
    interaction: SocialInteraction,
    reason: str,
) -> None:
    """Fire a trigger and take appropriate action."""
    logger.info(
        "Trigger fired: %s (%s) for interaction %s - reason: %s",
        trigger.trigger_type,
        trigger.action,
        interaction.id,
        reason,
    )

    # Update trigger last_fired_at
    trigger.last_fired_at = datetime.now(UTC)

    action = TriggerAction(trigger.action)

    if action == TriggerAction.WAKE_AND_EVALUATE:
        # Enqueue evaluation job
        await queue.enqueue(
            SOCIAL_EVALUATE_JOB,
            agent_id=channel.agent_id,
            channel_id=channel.id,
            interaction_id=interaction.id,
            trigger_id=trigger.id,
            is_mention=interaction.interaction_type == InteractionType.MENTION_RECEIVED.value,
        )

        # Publish wake event
        await publish_event(
            agent_id=channel.agent_id,
            event_type=EventType.SOCIAL_WAKE,
            payload={
                "trigger_type": trigger.trigger_type,
                "reason": reason,
                "interaction_id": interaction.id,
            },
        )

    elif action == TriggerAction.SURFACE_TO_USER:
        # Just publish an event for the user
        await publish_event(
            agent_id=channel.agent_id,
            event_type=EventType.SOCIAL_TRIGGER_FIRED,
            payload={
                "trigger_type": trigger.trigger_type,
                "reason": reason,
                "content_preview": (interaction.content_text or "")[:280],
                "author": interaction.external_author,
            },
        )

    # LOG_ONLY is the default - we already logged above


@instrument_job("social_explore")
async def social_explore(
    ctx: Context,
    *,
    channel_id: str | None = None,
) -> dict[str, object]:
    """Explore social channels for new content.

    This job can be run:
    - For all enabled channels (cron, channel_id=None)
    - For a specific channel (on-demand, channel_id specified)

    Args:
        ctx: SAQ job context.
        channel_id: Optional specific channel to explore.

    Returns:
        Status dict with results per channel.
    """
    queue: Queue = ctx["queue"]

    async with _async_session() as db:
        if channel_id:
            # Single channel
            result = await db.execute(
                select(SocialChannel).where(SocialChannel.id == channel_id)
            )
            channel = result.scalar_one_or_none()
            if not channel:
                logger.warning("Channel not found: %s", channel_id)
                return {"status": "not_found", "channel_id": channel_id}

            if not channel.enabled:
                logger.info("Channel disabled: %s", channel_id)
                return {"status": "disabled", "channel_id": channel_id}

            channel_result = await _explore_channel(db, queue, channel)
            return {"status": "ok", "channels": {channel_id: channel_result}}
        else:
            # All enabled channels
            channels = await _get_enabled_channels(db)
            logger.info("Exploring %d enabled social channels", len(channels))

            if not channels:
                return {"status": "skipped", "reason": "no_enabled_channels"}

            results: dict[str, Any] = {}
            for channel in channels:
                try:
                    results[channel.id] = await _explore_channel(db, queue, channel)
                except Exception:
                    logger.exception("Error exploring channel %s", channel.id)
                    results[channel.id] = {"status": "error"}

            return {"status": "ok", "channels": results}
