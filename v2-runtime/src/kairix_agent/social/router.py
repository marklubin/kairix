"""FastAPI router for social agent endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from kairix_agent.social import approval_service, service
from kairix_agent.social.models import (
    ApprovalStatus,
    EngagementLevel,
    NotificationChannel,
    SocialChannelType,
    TriggerAction,
    TriggerType,
    TrustLevel,
)
from kairix_agent.social.schemas import (
    ApprovalItemResponse,
    ApproveRequest,
    ChannelCreate,
    ChannelResponse,
    ChannelUpdate,
    InteractionResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    QueueStatsResponse,
    RejectRequest,
    TriggerCreate,
    TriggerResponse,
    TriggerUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/social", tags=["social"])


# =============================================================================
# Channel Endpoints
# =============================================================================


@router.get("/channels", response_model=list[ChannelResponse])
async def list_channels(agent_id: str | None = None) -> list[ChannelResponse]:
    """List social channels, optionally filtered by agent."""
    channels = await service.list_channels(agent_id)
    return [ChannelResponse.model_validate(c) for c in channels]


@router.get("/channels/{channel_id}", response_model=ChannelResponse)
async def get_channel(channel_id: str) -> ChannelResponse:
    """Get a social channel by ID."""
    channel = await service.get_channel(channel_id)
    if channel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found"
        )
    return ChannelResponse.model_validate(channel)


@router.post(
    "/channels/{agent_id}",
    response_model=ChannelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_channel(agent_id: str, body: ChannelCreate) -> ChannelResponse:
    """Create a new social channel for an agent."""
    try:
        channel_type = SocialChannelType(body.channel_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid channel type: {body.channel_type}",
        )

    try:
        engagement_level = EngagementLevel(body.engagement_level)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid engagement level: {body.engagement_level}",
        )

    try:
        trust_level = TrustLevel(body.trust_level)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid trust level: {body.trust_level}",
        )

    try:
        channel = await service.create_channel(
            agent_id=agent_id,
            channel_type=channel_type,
            handle=body.handle,
            credentials=body.credentials,
            engagement_level=engagement_level,
            trust_level=trust_level,
        )
        return ChannelResponse.model_validate(channel)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.patch("/channels/{channel_id}", response_model=ChannelResponse)
async def update_channel(channel_id: str, body: ChannelUpdate) -> ChannelResponse:
    """Update a social channel."""
    engagement_level = None
    if body.engagement_level:
        try:
            engagement_level = EngagementLevel(body.engagement_level)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid engagement level: {body.engagement_level}",
            )

    trust_level = None
    if body.trust_level:
        try:
            trust_level = TrustLevel(body.trust_level)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid trust level: {body.trust_level}",
            )

    channel = await service.update_channel(
        channel_id,
        handle=body.handle,
        credentials=body.credentials,
        engagement_level=engagement_level,
        trust_level=trust_level,
        enabled=body.enabled,
    )
    if channel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found"
        )
    return ChannelResponse.model_validate(channel)


@router.delete("/channels/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(channel_id: str) -> None:
    """Delete a social channel."""
    deleted = await service.delete_channel(channel_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found"
        )


# =============================================================================
# Trigger Endpoints
# =============================================================================


@router.get("/channels/{channel_id}/triggers", response_model=list[TriggerResponse])
async def list_triggers(channel_id: str) -> list[TriggerResponse]:
    """List triggers for a channel."""
    triggers = await service.list_triggers(channel_id)
    return [TriggerResponse.model_validate(t) for t in triggers]


@router.post(
    "/channels/{channel_id}/triggers",
    response_model=TriggerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_trigger(channel_id: str, body: TriggerCreate) -> TriggerResponse:
    """Create a new trigger for a channel."""
    try:
        trigger_type = TriggerType(body.trigger_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid trigger type: {body.trigger_type}",
        )

    try:
        action = TriggerAction(body.action)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action: {body.action}",
        )

    trigger = await service.create_trigger(
        channel_id=channel_id,
        trigger_type=trigger_type,
        action=action,
        config=body.config,
        cooldown_minutes=body.cooldown_minutes,
    )
    return TriggerResponse.model_validate(trigger)


@router.patch("/triggers/{trigger_id}", response_model=TriggerResponse)
async def update_trigger(trigger_id: str, body: TriggerUpdate) -> TriggerResponse:
    """Update a trigger."""
    action = None
    if body.action:
        try:
            action = TriggerAction(body.action)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {body.action}",
            )

    trigger = await service.update_trigger(
        trigger_id,
        config=body.config,
        action=action,
        cooldown_minutes=body.cooldown_minutes,
        enabled=body.enabled,
    )
    if trigger is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trigger not found"
        )
    return TriggerResponse.model_validate(trigger)


@router.delete("/triggers/{trigger_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trigger(trigger_id: str) -> None:
    """Delete a trigger."""
    deleted = await service.delete_trigger(trigger_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trigger not found"
        )


# =============================================================================
# Interaction Endpoints
# =============================================================================


@router.get(
    "/channels/{channel_id}/interactions", response_model=list[InteractionResponse]
)
async def list_interactions(
    channel_id: str, limit: int = 50, offset: int = 0
) -> list[InteractionResponse]:
    """List interactions for a channel."""
    interactions = await service.list_interactions(channel_id, limit, offset)
    return [InteractionResponse.model_validate(i) for i in interactions]


@router.get("/interactions/{interaction_id}", response_model=InteractionResponse)
async def get_interaction(interaction_id: str) -> InteractionResponse:
    """Get an interaction by ID."""
    interaction = await service.get_interaction(interaction_id)
    if interaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Interaction not found"
        )
    return InteractionResponse.model_validate(interaction)


# =============================================================================
# Approval Queue Endpoints
# =============================================================================


@router.get("/approval-queue", response_model=list[ApprovalItemResponse])
async def list_pending_approvals(
    agent_id: str | None = None, limit: int = 50, offset: int = 0
) -> list[ApprovalItemResponse]:
    """List pending approval items."""
    items = await approval_service.list_pending_items(agent_id, limit, offset)
    return [ApprovalItemResponse.model_validate(i) for i in items]


@router.get("/approval-queue/by-status/{status_value}", response_model=list[ApprovalItemResponse])
async def list_approvals_by_status(
    status_value: str,
    agent_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ApprovalItemResponse]:
    """List approval items by status."""
    try:
        approval_status = ApprovalStatus(status_value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {status_value}",
        )

    items = await approval_service.list_items_by_status(
        approval_status, agent_id, limit, offset
    )
    return [ApprovalItemResponse.model_validate(i) for i in items]


@router.get("/approval-queue/{item_id}", response_model=ApprovalItemResponse)
async def get_approval_item(item_id: str) -> ApprovalItemResponse:
    """Get an approval item by ID."""
    item = await approval_service.get_approval_item(item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Approval item not found"
        )
    return ApprovalItemResponse.model_validate(item)


@router.post("/approval-queue/{item_id}/approve", response_model=ApprovalItemResponse)
async def approve_item(item_id: str, body: ApproveRequest) -> ApprovalItemResponse:
    """Approve an item in the queue."""
    item = await approval_service.approve_item(
        item_id, modified_content=body.modified_content
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Approval item not found"
        )
    return ApprovalItemResponse.model_validate(item)


@router.post("/approval-queue/{item_id}/reject", response_model=ApprovalItemResponse)
async def reject_item(item_id: str, body: RejectRequest) -> ApprovalItemResponse:
    """Reject an item in the queue."""
    item = await approval_service.reject_item(item_id, feedback=body.feedback)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Approval item not found"
        )
    return ApprovalItemResponse.model_validate(item)


@router.get(
    "/approval-queue/stats/{agent_id}", response_model=QueueStatsResponse
)
async def get_queue_stats(agent_id: str) -> QueueStatsResponse:
    """Get approval queue statistics for an agent."""
    stats = await approval_service.get_queue_stats(agent_id)
    return QueueStatsResponse(**stats)


# =============================================================================
# Notification Preference Endpoints
# =============================================================================


@router.get(
    "/notifications/{agent_id}",
    response_model=NotificationPreferenceResponse | None,
)
async def get_notification_preferences(
    agent_id: str,
) -> NotificationPreferenceResponse | None:
    """Get notification preferences for an agent."""
    prefs = await service.get_notification_preferences(agent_id)
    return NotificationPreferenceResponse.model_validate(prefs) if prefs else None


@router.put(
    "/notifications/{agent_id}", response_model=NotificationPreferenceResponse
)
async def set_notification_preferences(
    agent_id: str, body: NotificationPreferenceUpdate
) -> NotificationPreferenceResponse:
    """Set notification preferences for an agent."""
    channels_enabled = None
    if body.channels_enabled:
        try:
            channels_enabled = [NotificationChannel(c) for c in body.channels_enabled]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid notification channel: {e}",
            )

    prefs = await service.set_notification_preferences(
        agent_id,
        channels_enabled=channels_enabled,
        digest_email=body.digest_email,
        digest_frequency=body.digest_frequency,
        mention_threshold=body.mention_threshold,
    )
    return NotificationPreferenceResponse.model_validate(prefs)
