"""Pydantic schemas for social API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# =============================================================================
# Channel Schemas
# =============================================================================


class ChannelCreate(BaseModel):
    """Schema for creating a social channel."""

    channel_type: str = Field(description="Platform type (e.g., 'bluesky')")
    handle: str = Field(description="Social handle (e.g., '@user.bsky.social')")
    credentials: dict[str, Any] = Field(description="Platform credentials")
    engagement_level: str = Field(
        default="conservative",
        description="Engagement level: conservative, moderate, active",
    )
    trust_level: str = Field(
        default="learning",
        description="Trust level: learning, trusted, autonomous",
    )


class ChannelUpdate(BaseModel):
    """Schema for updating a social channel."""

    handle: str | None = None
    credentials: dict[str, Any] | None = None
    engagement_level: str | None = None
    trust_level: str | None = None
    enabled: bool | None = None


class ChannelResponse(BaseModel):
    """Schema for channel response (excludes credentials)."""

    id: str
    agent_id: str
    channel_type: str
    handle: str
    engagement_level: str
    trust_level: str
    enabled: bool
    last_explored_at: datetime | None
    last_mention_check_at: datetime | None
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


# =============================================================================
# Trigger Schemas
# =============================================================================


class TriggerCreate(BaseModel):
    """Schema for creating a trigger."""

    trigger_type: str = Field(
        description="Trigger type: direct_mention, keyword, account_post, etc."
    )
    action: str = Field(
        description="Action: wake_and_evaluate, surface_to_user, log_only"
    )
    config: dict[str, Any] = Field(
        default_factory=dict, description="Trigger-specific configuration"
    )
    cooldown_minutes: int = Field(default=30, description="Cooldown between firings")


class TriggerUpdate(BaseModel):
    """Schema for updating a trigger."""

    config: dict[str, Any] | None = None
    action: str | None = None
    cooldown_minutes: int | None = None
    enabled: bool | None = None


class TriggerResponse(BaseModel):
    """Schema for trigger response."""

    id: str
    channel_id: str
    trigger_type: str
    config: dict[str, Any]
    action: str
    cooldown_minutes: int
    enabled: bool
    last_fired_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# =============================================================================
# Interaction Schemas
# =============================================================================


class InteractionResponse(BaseModel):
    """Schema for interaction response."""

    id: str
    channel_id: str
    interaction_type: str
    external_post_id: str | None
    external_author: str | None
    external_author_did: str | None
    content_text: str | None
    parent_post_id: str | None
    thread_root_id: str | None
    extra_data: dict[str, Any]
    episode_passage_id: str | None
    summary_passage_id: str | None
    reflection_passage_id: str | None
    entity_model_updated: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# =============================================================================
# Approval Queue Schemas
# =============================================================================


class ApprovalItemResponse(BaseModel):
    """Schema for approval queue item response."""

    id: str
    interaction_id: str | None
    agent_id: str
    channel_type: str
    action_type: str
    draft_content: str | None
    target_entity: str | None
    context_summary: str | None
    confidence_score: float
    entity_model_used: str | None
    status: str
    user_feedback: str | None
    created_at: datetime
    reviewed_at: datetime | None
    expires_at: datetime | None

    model_config = {"from_attributes": True}


class ApproveRequest(BaseModel):
    """Request to approve an item."""

    modified_content: str | None = Field(
        default=None, description="Optional modified content (user edits)"
    )


class RejectRequest(BaseModel):
    """Request to reject an item."""

    feedback: str | None = Field(
        default=None, description="Optional feedback explaining rejection"
    )


class QueueStatsResponse(BaseModel):
    """Response for queue statistics."""

    pending: int
    approved: int
    rejected: int
    expired: int
    total: int
    approval_rate: float


# =============================================================================
# Notification Preference Schemas
# =============================================================================


class NotificationPreferenceUpdate(BaseModel):
    """Schema for updating notification preferences."""

    channels_enabled: list[str] | None = Field(
        default=None, description="Enabled notification channels"
    )
    digest_email: str | None = None
    digest_frequency: str | None = None
    mention_threshold: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Importance threshold for voice mentions"
    )


class NotificationPreferenceResponse(BaseModel):
    """Schema for notification preference response."""

    id: str
    agent_id: str
    channels_enabled: list[str]
    digest_email: str | None
    digest_frequency: str
    mention_threshold: float
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}
