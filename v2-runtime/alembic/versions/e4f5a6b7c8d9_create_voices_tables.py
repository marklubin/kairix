"""create voices tables

Revision ID: e4f5a6b7c8d9
Revises: d8e9f0a1b2c3
Create Date: 2025-12-19

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4f5a6b7c8d9"
down_revision: str | Sequence[str] | None = "d8e9f0a1b2c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create voices and agent_voice_settings tables."""
    # Create voices table
    op.create_table(
        "voices",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("provider_voice_id", sa.String(length=256), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_voices_name", "voices", ["name"], unique=True)
    op.create_index("ix_voices_provider", "voices", ["provider"], unique=False)

    # Create agent_voice_settings table
    op.create_table(
        "agent_voice_settings",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("voice_id", sa.UUID(as_uuid=False), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["voice_id"], ["voices.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id"),
    )
    op.create_index(
        "ix_agent_voice_settings_agent_id",
        "agent_voice_settings",
        ["agent_id"],
        unique=True,
    )
    op.create_index(
        "ix_agent_voice_settings_voice_id",
        "agent_voice_settings",
        ["voice_id"],
        unique=False,
    )

    # Seed default Cartesia voices
    op.execute("""
        INSERT INTO voices (id, name, provider_voice_id, provider, description, created_at)
        VALUES
            (gen_random_uuid(), 'Friendly Female', 'a0e99841-438c-4a64-b679-ae501e7d6091', 'cartesia', 'Warm and approachable voice', NOW()),
            (gen_random_uuid(), 'Professional Male', '79a125e8-cd45-4c13-8a67-188112f4dd22', 'cartesia', 'Clear and authoritative voice', NOW())
    """)


def downgrade() -> None:
    """Drop voices and agent_voice_settings tables."""
    op.drop_index("ix_agent_voice_settings_voice_id", table_name="agent_voice_settings")
    op.drop_index("ix_agent_voice_settings_agent_id", table_name="agent_voice_settings")
    op.drop_table("agent_voice_settings")
    op.drop_index("ix_voices_provider", table_name="voices")
    op.drop_index("ix_voices_name", table_name="voices")
    op.drop_table("voices")
