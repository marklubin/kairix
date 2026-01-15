"""Service layer for social approval queue operations."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from kairix_agent.config import Config
from kairix_agent.social.models import (
    ActionType,
    ApprovalQueueItem,
    ApprovalStatus,
    SocialInteraction,
)

_engine = create_async_engine(Config.DATABASE_URL.value, echo=False)
_async_session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

# Default expiration for approval items
DEFAULT_EXPIRATION_HOURS = 24


# =============================================================================
# Queue Item CRUD
# =============================================================================


async def create_approval_item(
    agent_id: str,
    channel_type: str,
    action_type: ActionType,
    *,
    interaction_id: str | None = None,
    draft_content: str | None = None,
    target_entity: str | None = None,
    context_summary: str | None = None,
    confidence_score: float = 0.5,
    entity_model_used: str | None = None,
    expiration_hours: int = DEFAULT_EXPIRATION_HOURS,
) -> ApprovalQueueItem:
    """Create a new item in the approval queue.

    Args:
        agent_id: Agent ID.
        channel_type: Type of social channel.
        action_type: Type of action to approve.
        interaction_id: Related interaction ID (optional).
        draft_content: Draft content for post/reply (optional).
        target_entity: Target of the action (optional).
        context_summary: Context explaining the action.
        confidence_score: Agent's confidence in this action.
        entity_model_used: Snapshot of entity model used for context.
        expiration_hours: Hours until item expires.

    Returns:
        Created approval item.
    """
    async with _async_session() as db:
        expires_at = datetime.now(UTC) + timedelta(hours=expiration_hours)

        item = ApprovalQueueItem(
            agent_id=agent_id,
            channel_type=channel_type,
            action_type=action_type.value,
            interaction_id=interaction_id,
            draft_content=draft_content,
            target_entity=target_entity,
            context_summary=context_summary,
            confidence_score=confidence_score,
            entity_model_used=entity_model_used,
            expires_at=expires_at,
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item


async def get_approval_item(item_id: str) -> ApprovalQueueItem | None:
    """Get an approval item by ID.

    Args:
        item_id: Item UUID.

    Returns:
        Item if found, None otherwise.
    """
    async with _async_session() as db:
        result = await db.execute(
            select(ApprovalQueueItem)
            .options(selectinload(ApprovalQueueItem.interaction))
            .where(ApprovalQueueItem.id == item_id)
        )
        return result.scalar_one_or_none()


async def list_pending_items(
    agent_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ApprovalQueueItem]:
    """List pending approval items.

    Args:
        agent_id: Optional agent ID to filter by.
        limit: Maximum number to return.
        offset: Number to skip.

    Returns:
        List of pending items.
    """
    async with _async_session() as db:
        query = (
            select(ApprovalQueueItem)
            .options(selectinload(ApprovalQueueItem.interaction))
            .where(ApprovalQueueItem.status == ApprovalStatus.PENDING.value)
            .order_by(ApprovalQueueItem.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if agent_id:
            query = query.where(ApprovalQueueItem.agent_id == agent_id)

        result = await db.execute(query)
        return list(result.scalars().all())


async def list_items_by_status(
    status: ApprovalStatus,
    agent_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ApprovalQueueItem]:
    """List approval items by status.

    Args:
        status: Status to filter by.
        agent_id: Optional agent ID to filter by.
        limit: Maximum number to return.
        offset: Number to skip.

    Returns:
        List of items.
    """
    async with _async_session() as db:
        query = (
            select(ApprovalQueueItem)
            .options(selectinload(ApprovalQueueItem.interaction))
            .where(ApprovalQueueItem.status == status.value)
            .order_by(ApprovalQueueItem.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if agent_id:
            query = query.where(ApprovalQueueItem.agent_id == agent_id)

        result = await db.execute(query)
        return list(result.scalars().all())


# =============================================================================
# Approval Actions
# =============================================================================


async def approve_item(
    item_id: str,
    *,
    modified_content: str | None = None,
) -> ApprovalQueueItem | None:
    """Approve an item in the queue.

    Args:
        item_id: Item UUID.
        modified_content: Optional modified content (user edits).

    Returns:
        Updated item if found and was pending, None otherwise.
    """
    async with _async_session() as db:
        result = await db.execute(
            select(ApprovalQueueItem).where(ApprovalQueueItem.id == item_id)
        )
        item = result.scalar_one_or_none()

        if item is None:
            return None

        if item.status != ApprovalStatus.PENDING.value:
            return item  # Already processed

        item.status = ApprovalStatus.APPROVED.value
        item.reviewed_at = datetime.now(UTC)

        if modified_content is not None:
            item.draft_content = modified_content

        await db.commit()
        await db.refresh(item)
        return item


async def reject_item(
    item_id: str,
    feedback: str | None = None,
) -> ApprovalQueueItem | None:
    """Reject an item in the queue.

    Args:
        item_id: Item UUID.
        feedback: Optional user feedback explaining rejection.

    Returns:
        Updated item if found and was pending, None otherwise.
    """
    async with _async_session() as db:
        result = await db.execute(
            select(ApprovalQueueItem).where(ApprovalQueueItem.id == item_id)
        )
        item = result.scalar_one_or_none()

        if item is None:
            return None

        if item.status != ApprovalStatus.PENDING.value:
            return item  # Already processed

        item.status = ApprovalStatus.REJECTED.value
        item.reviewed_at = datetime.now(UTC)
        item.user_feedback = feedback

        await db.commit()
        await db.refresh(item)
        return item


async def expire_old_items() -> int:
    """Mark expired items as expired.

    Returns:
        Number of items expired.
    """
    async with _async_session() as db:
        result = await db.execute(
            update(ApprovalQueueItem)
            .where(ApprovalQueueItem.status == ApprovalStatus.PENDING.value)
            .where(ApprovalQueueItem.expires_at < datetime.now(UTC))
            .values(status=ApprovalStatus.EXPIRED.value, reviewed_at=datetime.now(UTC))
        )
        await db.commit()
        return result.rowcount  # type: ignore[return-value]


# =============================================================================
# Statistics
# =============================================================================


async def get_queue_stats(agent_id: str) -> dict[str, Any]:
    """Get approval queue statistics for an agent.

    Args:
        agent_id: Agent ID.

    Returns:
        Dictionary with queue statistics.
    """
    async with _async_session() as db:
        # Count by status
        pending_result = await db.execute(
            select(ApprovalQueueItem)
            .where(ApprovalQueueItem.agent_id == agent_id)
            .where(ApprovalQueueItem.status == ApprovalStatus.PENDING.value)
        )
        pending_count = len(list(pending_result.scalars().all()))

        approved_result = await db.execute(
            select(ApprovalQueueItem)
            .where(ApprovalQueueItem.agent_id == agent_id)
            .where(ApprovalQueueItem.status == ApprovalStatus.APPROVED.value)
        )
        approved_count = len(list(approved_result.scalars().all()))

        rejected_result = await db.execute(
            select(ApprovalQueueItem)
            .where(ApprovalQueueItem.agent_id == agent_id)
            .where(ApprovalQueueItem.status == ApprovalStatus.REJECTED.value)
        )
        rejected_count = len(list(rejected_result.scalars().all()))

        expired_result = await db.execute(
            select(ApprovalQueueItem)
            .where(ApprovalQueueItem.agent_id == agent_id)
            .where(ApprovalQueueItem.status == ApprovalStatus.EXPIRED.value)
        )
        expired_count = len(list(expired_result.scalars().all()))

        total = pending_count + approved_count + rejected_count + expired_count
        approval_rate = approved_count / (approved_count + rejected_count) if (approved_count + rejected_count) > 0 else 0.0

        return {
            "pending": pending_count,
            "approved": approved_count,
            "rejected": rejected_count,
            "expired": expired_count,
            "total": total,
            "approval_rate": approval_rate,
        }


# =============================================================================
# Helper for interaction updates
# =============================================================================


async def mark_interaction_sent(
    interaction_id: str,
    external_post_id: str,
) -> SocialInteraction | None:
    """Update an interaction after it has been sent.

    Args:
        interaction_id: Interaction UUID.
        external_post_id: The external post ID from the platform.

    Returns:
        Updated interaction if found, None otherwise.
    """
    async with _async_session() as db:
        result = await db.execute(
            select(SocialInteraction).where(SocialInteraction.id == interaction_id)
        )
        interaction = result.scalar_one_or_none()

        if interaction is None:
            return None

        interaction.external_post_id = external_post_id
        interaction.extra_data = {
            **interaction.extra_data,
            "sent_at": datetime.now(UTC).isoformat(),
        }

        await db.commit()
        await db.refresh(interaction)
        return interaction
