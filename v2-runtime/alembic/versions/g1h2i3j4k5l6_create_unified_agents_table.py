"""Create unified agents table.

Revision ID: g1h2i3j4k5l6
Revises: f042e3249dd2
Create Date: 2026-01-06 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "g1h2i3j4k5l6"
down_revision: str | None = "f042e3249dd2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the unified agents table."""
    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        # Primary LLM Config
        sa.Column("inference_model", sa.String(256), nullable=False),
        sa.Column("inference_provider_url", sa.String(512), nullable=True),
        sa.Column(
            "embedding_model",
            sa.String(256),
            nullable=False,
            server_default="openai/text-embedding-3-small",
        ),
        sa.Column("context_window", sa.Integer(), nullable=False, server_default="25000"),
        sa.Column("max_tokens", sa.Integer(), nullable=False, server_default="4096"),
        sa.Column("enable_reasoner", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("max_reasoning_tokens", sa.Integer(), nullable=True, server_default="1024"),
        # Background LLM Config
        sa.Column(
            "background_llm_model",
            sa.String(256),
            nullable=False,
            server_default="deepseek-chat",
        ),
        sa.Column(
            "background_llm_url",
            sa.String(512),
            nullable=False,
            server_default="https://api.deepseek.com",
        ),
        # Block Schema
        sa.Column("block_schema", postgresql.JSONB(), nullable=False, server_default="[]"),
        # Tools
        sa.Column(
            "tools", postgresql.ARRAY(sa.String(128)), nullable=False, server_default="{}"
        ),
        sa.Column("include_base_tools", sa.Boolean(), nullable=False, server_default="true"),
        # Voice
        sa.Column("voice_id", postgresql.UUID(as_uuid=False), nullable=True),
        # KP3 Integration
        sa.Column("kp3_ref_prefix", sa.String(128), nullable=True),
        sa.Column("kp3_hooks_enabled", sa.Boolean(), nullable=False, server_default="true"),
        # Letta Sync State
        sa.Column("letta_agent_id", sa.String(64), nullable=True),
        sa.Column("letta_archive_id", sa.String(64), nullable=True),
        sa.Column("letta_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("letta_sync_hash", sa.String(64), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.ForeignKeyConstraint(
            ["voice_id"],
            ["voices.id"],
            ondelete="SET NULL",
        ),
    )

    # Create indexes
    op.create_index("ix_agents_name", "agents", ["name"])
    op.create_index("ix_agents_letta_agent_id", "agents", ["letta_agent_id"])
    op.create_index("ix_agents_voice_id", "agents", ["voice_id"])


def downgrade() -> None:
    """Drop the unified agents table."""
    op.drop_index("ix_agents_voice_id", table_name="agents")
    op.drop_index("ix_agents_letta_agent_id", table_name="agents")
    op.drop_index("ix_agents_name", table_name="agents")
    op.drop_table("agents")
