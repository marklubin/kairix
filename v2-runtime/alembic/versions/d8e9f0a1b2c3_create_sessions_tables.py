"""create sessions tables

Revision ID: d8e9f0a1b2c3
Revises: 5a625f728d28
Create Date: 2025-12-18

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d8e9f0a1b2c3"
down_revision: str | Sequence[str] | None = "5a625f728d28"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create sessions and session_messages tables."""
    # Create sessions table
    op.create_table(
        "sessions",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("message_count", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("summary_passage_id", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("summarized_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessions_agent_id", "sessions", ["agent_id"], unique=False)
    op.create_index("ix_sessions_status", "sessions", ["status"], unique=False)
    op.create_index(
        "ix_sessions_agent_period",
        "sessions",
        ["agent_id", "period_start", "period_end"],
        unique=True,
    )

    # Create session_messages join table
    op.create_table(
        "session_messages",
        sa.Column("session_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("message_id", sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("session_id", "message_id"),
    )
    op.create_index(
        "ix_session_messages_message_id",
        "session_messages",
        ["message_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop sessions and session_messages tables."""
    op.drop_index("ix_session_messages_message_id", table_name="session_messages")
    op.drop_table("session_messages")
    op.drop_index("ix_sessions_agent_period", table_name="sessions")
    op.drop_index("ix_sessions_status", table_name="sessions")
    op.drop_index("ix_sessions_agent_id", table_name="sessions")
    op.drop_table("sessions")
