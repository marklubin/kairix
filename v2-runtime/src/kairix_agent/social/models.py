"""SQLAlchemy models for social agents.

Defines tables for:
- social_channels: Per-agent social platform configurations with encrypted credentials
- social_triggers: Custom triggers that wake agents (mentions, keywords, etc.)
- social_interactions: Log of all social activity for episodic memory
- approval_queue: Pending engagements awaiting user approval
- notification_preferences: Per-agent notification routing configuration
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kairix_agent.events.models import Base

# =============================================================================
# Enums
# =============================================================================


class SocialChannelType(str, Enum):
    """Supported social platform types."""

    BLUESKY = "bluesky"
    # Future: MASTODON = "mastodon", X = "x", etc.


class TrustLevel(str, Enum):
    """Trust levels determining approval requirements.

    - learning: All content-creating actions need approval
    - trusted: Only high-impact actions (block, unfollow) need approval
    - autonomous: No approvals (future, requires explicit opt-in)
    """

    LEARNING = "learning"
    TRUSTED = "trusted"
    AUTONOMOUS = "autonomous"


class EngagementLevel(str, Enum):
    """How actively the agent engages on social platforms.

    - conservative: Reply when mentioned, rare original posts
    - moderate: Reply to interesting threads, occasional posts
    - active: Engage frequently, post regularly
    """

    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    ACTIVE = "active"


class InteractionType(str, Enum):
    """Types of social interactions tracked."""

    TIMELINE_VIEW = "timeline_view"       # Saw a post on timeline
    MENTION_RECEIVED = "mention_received"  # Was mentioned/replied to
    DRAFT_REPLY = "draft_reply"           # Drafted a reply (pending approval)
    DRAFT_POST = "draft_post"             # Drafted original post
    APPROVED_SENT = "approved_sent"       # Approved and sent
    REJECTED = "rejected"                 # User rejected draft
    LIKE = "like"                         # Liked a post
    REPOST = "repost"                     # Reposted
    FOLLOW = "follow"                     # Followed an account
    UNFOLLOW = "unfollow"                 # Unfollowed an account


class TriggerType(str, Enum):
    """Types of triggers that can wake an agent."""

    DIRECT_MENTION = "direct_mention"        # Someone @mentions the agent
    REPLY_TO_POST = "reply_to_post"          # Someone replies to agent's post
    NEW_FOLLOWER = "new_follower"            # Someone follows the agent
    DM_RECEIVED = "dm_received"              # Direct message received
    KEYWORD = "keyword"                       # Keyword pattern match
    ACCOUNT_POST = "account_post"            # Watched account posts
    ENGAGEMENT_THRESHOLD = "engagement_threshold"  # Post reaches like threshold


class TriggerAction(str, Enum):
    """Actions to take when a trigger fires."""

    WAKE_AND_EVALUATE = "wake_and_evaluate"  # Wake agent, evaluate for response
    SURFACE_TO_USER = "surface_to_user"      # Notify user without engaging
    LOG_ONLY = "log_only"                    # Just log the event


class ApprovalStatus(str, Enum):
    """Status of items in the approval queue."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ActionType(str, Enum):
    """Types of actions that can be approved."""

    REPLY = "reply"
    POST = "post"
    REPOST = "repost"
    QUOTE = "quote"
    LIKE = "like"
    FOLLOW = "follow"
    UNFOLLOW = "unfollow"
    BLOCK = "block"
    MUTE = "mute"
    LIST_ADD = "list_add"


class NotificationChannel(str, Enum):
    """Available notification channels."""

    EVENT_STREAM = "event_stream"      # WebSocket /events endpoint
    VOICE_MENTION = "voice_mention"    # Proactive mention in voice conversation
    EMAIL_DIGEST = "email_digest"      # Email summary


# =============================================================================
# Models
# =============================================================================


class SocialChannel(Base):
    """Social media channel configuration with encrypted credentials.

    Each agent can have one channel per platform type.
    Credentials are encrypted using Fernet symmetric encryption.
    """

    __tablename__ = "social_channels"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    channel_type: Mapped[str] = mapped_column(String(32))  # SocialChannelType
    handle: Mapped[str] = mapped_column(String(256))  # @user.bsky.social
    credentials_encrypted: Mapped[bytes] = mapped_column(LargeBinary)

    # Behavior configuration
    engagement_level: Mapped[str] = mapped_column(
        String(32), default=EngagementLevel.CONSERVATIVE.value
    )
    trust_level: Mapped[str] = mapped_column(
        String(32), default=TrustLevel.LEARNING.value
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Polling state
    last_explored_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_mention_check_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=lambda: datetime.now(UTC),
        nullable=True,
    )

    # Relationships
    interactions: Mapped[list[SocialInteraction]] = relationship(
        "SocialInteraction",
        back_populates="channel",
        cascade="all, delete-orphan",
    )
    triggers: Mapped[list[SocialTrigger]] = relationship(
        "SocialTrigger",
        back_populates="channel",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_social_channels_agent_type", "agent_id", "channel_type", unique=True),
    )


class SocialTrigger(Base):
    """Custom triggers that wake agents based on social activity.

    Triggers are evaluated during polling and can fire jobs or notifications.
    """

    __tablename__ = "social_triggers"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    channel_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("social_channels.id", ondelete="CASCADE"),
        index=True,
    )
    trigger_type: Mapped[str] = mapped_column(String(32))  # TriggerType
    config: Mapped[dict] = mapped_column(JSONB, default=dict)  # type: ignore[type-arg]
    action: Mapped[str] = mapped_column(String(32))  # TriggerAction

    # Rate limiting
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=30)
    last_fired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    # Relationship
    channel: Mapped[SocialChannel] = relationship(
        "SocialChannel",
        back_populates="triggers",
    )

    __table_args__ = (
        Index("ix_social_triggers_channel_enabled", "channel_id", "enabled"),
    )


class SocialInteraction(Base):
    """Record of a social interaction on any channel.

    Tracks all activity for episodic memory and summarization.
    Links to KP3 passages for episode, summary, and reflection storage.
    """

    __tablename__ = "social_interactions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    channel_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("social_channels.id", ondelete="CASCADE"),
        index=True,
    )
    interaction_type: Mapped[str] = mapped_column(String(32))  # InteractionType

    # External platform identifiers
    external_post_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    external_author: Mapped[str | None] = mapped_column(String(256), nullable=True)
    external_author_did: Mapped[str | None] = mapped_column(
        String(256), nullable=True, index=True
    )  # Stable DID for entity lookup

    # Content
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_post_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    thread_root_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict)  # type: ignore[type-arg]

    # Episodic pipeline tracking - links to KP3 passages
    episode_passage_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    summary_passage_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reflection_passage_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    entity_model_updated: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    # Relationship
    channel: Mapped[SocialChannel] = relationship(
        "SocialChannel",
        back_populates="interactions",
    )

    __table_args__ = (
        Index("ix_social_interactions_channel_created", "channel_id", "created_at"),
    )


class ApprovalQueueItem(Base):
    """Pending social engagement awaiting user approval.

    Created when agent drafts a post/reply but needs human approval.
    Includes context about why agent wants to engage and entity model snapshot.
    """

    __tablename__ = "approval_queue"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    interaction_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("social_interactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    channel_type: Mapped[str] = mapped_column(String(32))

    # Action details
    action_type: Mapped[str] = mapped_column(String(32))  # ActionType
    draft_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_entity: Mapped[str | None] = mapped_column(
        String(256), nullable=True
    )  # Who/what is target

    # Context for approval decision
    context_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.5)
    entity_model_used: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Snapshot of entity model

    # Status
    status: Mapped[str] = mapped_column(
        String(32), default=ApprovalStatus.PENDING.value, index=True
    )
    user_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationship
    interaction: Mapped[SocialInteraction | None] = relationship("SocialInteraction")

    __table_args__ = (
        Index("ix_approval_queue_agent_status", "agent_id", "status"),
    )


class NotificationPreference(Base):
    """Per-agent notification preferences for social activity.

    Controls how social events are surfaced to the user.
    """

    __tablename__ = "notification_preferences"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    agent_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    # Enabled notification channels
    channels_enabled: Mapped[list[str]] = mapped_column(
        ARRAY(String(32)),
        default=lambda: [NotificationChannel.EVENT_STREAM.value],
    )

    # Email digest settings
    digest_email: Mapped[str | None] = mapped_column(String(256), nullable=True)
    digest_frequency: Mapped[str] = mapped_column(String(32), default="daily")

    # Voice mention settings
    mention_threshold: Mapped[float] = mapped_column(
        Float, default=0.8
    )  # Importance threshold for voice mentions

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=lambda: datetime.now(UTC),
        nullable=True,
    )
