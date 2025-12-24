"""add world model tables (passage_refs, extraction_prompts)

Revision ID: b8c7d4e5f123
Revises: e935a08a6245
Create Date: 2025-12-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8c7d4e5f123"
down_revision: Union[str, Sequence[str], None] = "e935a08a6245"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add passage_refs, passage_ref_history, passage_ref_hooks, and extraction_prompts tables."""
    # Create passage_refs table
    op.create_table(
        "passage_refs",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("passage_id", sa.UUID(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["passage_id"], ["passages.id"]),
        sa.PrimaryKeyConstraint("name"),
    )
    op.create_index("idx_passage_refs_passage_id", "passage_refs", ["passage_id"], unique=False)

    # Create passage_ref_history table to track ref changes over time
    op.create_table(
        "passage_ref_history",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("ref_name", sa.Text(), nullable=False),
        sa.Column("passage_id", sa.UUID(), nullable=False),
        sa.Column("previous_passage_id", sa.UUID(), nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["passage_id"], ["passages.id"]),
        sa.ForeignKeyConstraint(["previous_passage_id"], ["passages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_passage_ref_history_ref_name", "passage_ref_history", ["ref_name"])
    op.create_index("idx_passage_ref_history_changed_at", "passage_ref_history", ["changed_at"])

    # Create passage_ref_hooks table for extensible hook actions
    op.create_table(
        "passage_ref_hooks",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("ref_name", sa.Text(), nullable=False),
        sa.Column("action_type", sa.Text(), nullable=False),  # e.g., "letta_agent_block_update"
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),  # action-specific config (agent_id, block_label, etc.)
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_passage_ref_hooks_ref_name", "passage_ref_hooks", ["ref_name"])
    op.create_index(
        "idx_passage_ref_hooks_enabled",
        "passage_ref_hooks",
        ["ref_name", "enabled"],
        postgresql_where=sa.text("enabled = true"),
    )

    # Create extraction_prompts table
    op.create_table(
        "extraction_prompts",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("user_prompt_template", sa.Text(), nullable=False),
        sa.Column(
            "field_descriptions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "version", name="uq_extraction_prompts_name_version"),
    )
    op.create_index("idx_extraction_prompts_name", "extraction_prompts", ["name"], unique=False)
    op.create_index(
        "idx_extraction_prompts_active",
        "extraction_prompts",
        ["name", "is_active"],
        unique=False,
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    """Remove all world model tables."""
    op.drop_index("idx_extraction_prompts_active", table_name="extraction_prompts")
    op.drop_index("idx_extraction_prompts_name", table_name="extraction_prompts")
    op.drop_table("extraction_prompts")
    op.drop_index("idx_passage_ref_hooks_enabled", table_name="passage_ref_hooks")
    op.drop_index("idx_passage_ref_hooks_ref_name", table_name="passage_ref_hooks")
    op.drop_table("passage_ref_hooks")
    op.drop_index("idx_passage_ref_history_changed_at", table_name="passage_ref_history")
    op.drop_index("idx_passage_ref_history_ref_name", table_name="passage_ref_history")
    op.drop_table("passage_ref_history")
    op.drop_index("idx_passage_refs_passage_id", table_name="passage_refs")
    op.drop_table("passage_refs")
