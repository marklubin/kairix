"""create social tables

Revision ID: g1h2i3j4k5l6
Revises: f042e3249dd2
Create Date: 2026-01-13

Creates tables for social agents functionality:
- social_channels: Per-agent social platform configurations
- social_triggers: Custom triggers that wake agents
- social_interactions: Log of all social activity
- approval_queue: Pending engagements awaiting user approval
- notification_preferences: Per-agent notification routing
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "g1h2i3j4k5l6"
down_revision: str | Sequence[str] | None = "f042e3249dd2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create social agent tables."""
    # ==========================================================================
    # social_channels - Per-agent social platform configurations
    # ==========================================================================
    op.create_table(
        "social_channels",
        sa.Column("id", UUID(as_uuid=False), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("channel_type", sa.String(length=32), nullable=False),
        sa.Column("handle", sa.String(length=256), nullable=False),
        sa.Column("credentials_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column(
            "engagement_level",
            sa.String(length=32),
            nullable=False,
            server_default="conservative",
        ),
        sa.Column(
            "trust_level",
            sa.String(length=32),
            nullable=False,
            server_default="learning",
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_explored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_mention_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_social_channels_agent_id", "social_channels", ["agent_id"])
    op.create_index(
        "ix_social_channels_agent_type",
        "social_channels",
        ["agent_id", "channel_type"],
        unique=True,
    )

    # ==========================================================================
    # social_triggers - Custom triggers that wake agents
    # ==========================================================================
    op.create_table(
        "social_triggers",
        sa.Column("id", UUID(as_uuid=False), nullable=False),
        sa.Column("channel_id", UUID(as_uuid=False), nullable=False),
        sa.Column("trigger_type", sa.String(length=32), nullable=False),
        sa.Column("config", JSONB(), nullable=False, server_default="{}"),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("cooldown_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("last_fired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["channel_id"], ["social_channels.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_social_triggers_channel_id", "social_triggers", ["channel_id"])
    op.create_index(
        "ix_social_triggers_channel_enabled",
        "social_triggers",
        ["channel_id", "enabled"],
    )

    # ==========================================================================
    # social_interactions - Log of all social activity
    # ==========================================================================
    op.create_table(
        "social_interactions",
        sa.Column("id", UUID(as_uuid=False), nullable=False),
        sa.Column("channel_id", UUID(as_uuid=False), nullable=False),
        sa.Column("interaction_type", sa.String(length=32), nullable=False),
        sa.Column("external_post_id", sa.String(length=256), nullable=True),
        sa.Column("external_author", sa.String(length=256), nullable=True),
        sa.Column("external_author_did", sa.String(length=256), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("parent_post_id", sa.String(length=256), nullable=True),
        sa.Column("thread_root_id", sa.String(length=256), nullable=True),
        sa.Column("extra_data", JSONB(), nullable=False, server_default="{}"),
        # Episodic pipeline tracking - links to KP3 passages
        sa.Column("episode_passage_id", sa.String(length=128), nullable=True),
        sa.Column("summary_passage_id", sa.String(length=128), nullable=True),
        sa.Column("reflection_passage_id", sa.String(length=128), nullable=True),
        sa.Column(
            "entity_model_updated", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["channel_id"], ["social_channels.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_social_interactions_channel_id", "social_interactions", ["channel_id"]
    )
    op.create_index(
        "ix_social_interactions_channel_created",
        "social_interactions",
        ["channel_id", "created_at"],
    )
    op.create_index(
        "ix_social_interactions_author_did",
        "social_interactions",
        ["external_author_did"],
    )

    # ==========================================================================
    # approval_queue - Pending engagements awaiting user approval
    # ==========================================================================
    op.create_table(
        "approval_queue",
        sa.Column("id", UUID(as_uuid=False), nullable=False),
        sa.Column("interaction_id", UUID(as_uuid=False), nullable=True),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("channel_type", sa.String(length=32), nullable=False),
        sa.Column("action_type", sa.String(length=32), nullable=False),
        sa.Column("draft_content", sa.Text(), nullable=True),
        sa.Column("target_entity", sa.String(length=256), nullable=True),
        sa.Column("context_summary", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("entity_model_used", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default="'pending'"
        ),
        sa.Column("user_feedback", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["interaction_id"], ["social_interactions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_queue_agent_id", "approval_queue", ["agent_id"])
    op.create_index(
        "ix_approval_queue_agent_status", "approval_queue", ["agent_id", "status"]
    )

    # ==========================================================================
    # notification_preferences - Per-agent notification routing
    # ==========================================================================
    op.create_table(
        "notification_preferences",
        sa.Column("id", UUID(as_uuid=False), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column(
            "channels_enabled",
            ARRAY(sa.String(length=32)),
            nullable=False,
            server_default="'{event_stream}'",
        ),
        sa.Column("digest_email", sa.String(length=256), nullable=True),
        sa.Column(
            "digest_frequency",
            sa.String(length=32),
            nullable=False,
            server_default="'daily'",
        ),
        sa.Column(
            "mention_threshold", sa.Float(), nullable=False, server_default="0.8"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id"),
    )
    op.create_index(
        "ix_notification_preferences_agent_id",
        "notification_preferences",
        ["agent_id"],
        unique=True,
    )


def downgrade() -> None:
    """Drop social agent tables."""
    # Drop in reverse order of creation (respecting FK constraints)
    op.drop_index(
        "ix_notification_preferences_agent_id", table_name="notification_preferences"
    )
    op.drop_table("notification_preferences")

    op.drop_index("ix_approval_queue_agent_status", table_name="approval_queue")
    op.drop_index("ix_approval_queue_agent_id", table_name="approval_queue")
    op.drop_table("approval_queue")

    op.drop_index(
        "ix_social_interactions_author_did", table_name="social_interactions"
    )
    op.drop_index(
        "ix_social_interactions_channel_created", table_name="social_interactions"
    )
    op.drop_index(
        "ix_social_interactions_channel_id", table_name="social_interactions"
    )
    op.drop_table("social_interactions")

    op.drop_index("ix_social_triggers_channel_enabled", table_name="social_triggers")
    op.drop_index("ix_social_triggers_channel_id", table_name="social_triggers")
    op.drop_table("social_triggers")

    op.drop_index("ix_social_channels_agent_type", table_name="social_channels")
    op.drop_index("ix_social_channels_agent_id", table_name="social_channels")
    op.drop_table("social_channels")
