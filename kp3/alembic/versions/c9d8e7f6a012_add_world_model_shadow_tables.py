"""add world model shadow tables

Revision ID: c9d8e7f6a012
Revises: b8c7d4e5f123
Create Date: 2025-12-25

Shadow tables for world model entities with:
- agent_id: Letta agent segmentation
- canonical_key: Normalized key for dedup (lowercase, trimmed)
- name: Original display name
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9d8e7f6a012"
down_revision: Union[str, Sequence[str], None] = "b8c7d4e5f123"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add shadow tables for world model entities."""
    # Create world_model_projects table
    op.create_table(
        "world_model_projects",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("agent_id", sa.Text(), nullable=False),
        sa.Column("canonical_key", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=False),
        sa.Column(
            "last_occurrence",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("occurrence_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "canonical_key", name="uq_world_model_projects_agent_key"),
    )
    op.create_index("idx_world_model_projects_agent", "world_model_projects", ["agent_id"])
    op.create_index(
        "idx_world_model_projects_last_occurrence",
        "world_model_projects",
        ["last_occurrence"],
    )

    # Create world_model_entities table
    op.create_table(
        "world_model_entities",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("agent_id", sa.Text(), nullable=False),
        sa.Column("canonical_key", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("relevance", sa.Text(), nullable=False),
        sa.Column(
            "last_occurrence",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("occurrence_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "canonical_key", name="uq_world_model_entities_agent_key"),
    )
    op.create_index("idx_world_model_entities_agent", "world_model_entities", ["agent_id"])
    op.create_index(
        "idx_world_model_entities_last_occurrence",
        "world_model_entities",
        ["last_occurrence"],
    )

    # Create world_model_themes table
    op.create_table(
        "world_model_themes",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("agent_id", sa.Text(), nullable=False),
        sa.Column("canonical_key", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "last_occurrence",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("occurrence_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "canonical_key", name="uq_world_model_themes_agent_key"),
    )
    op.create_index("idx_world_model_themes_agent", "world_model_themes", ["agent_id"])
    op.create_index(
        "idx_world_model_themes_last_occurrence",
        "world_model_themes",
        ["last_occurrence"],
    )


def downgrade() -> None:
    """Remove world model shadow tables."""
    op.drop_index("idx_world_model_themes_agent", table_name="world_model_themes")
    op.drop_index("idx_world_model_themes_last_occurrence", table_name="world_model_themes")
    op.drop_table("world_model_themes")
    op.drop_index("idx_world_model_entities_agent", table_name="world_model_entities")
    op.drop_index("idx_world_model_entities_last_occurrence", table_name="world_model_entities")
    op.drop_table("world_model_entities")
    op.drop_index("idx_world_model_projects_agent", table_name="world_model_projects")
    op.drop_index("idx_world_model_projects_last_occurrence", table_name="world_model_projects")
    op.drop_table("world_model_projects")
