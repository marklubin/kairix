"""add world model branches table

Revision ID: d0e1f2a3b456
Revises: c9d8e7f6a012
Create Date: 2025-12-26

Branches group the 3 world model refs (human/persona/world) as a unit.
They enable experimentation without firing hooks on production agents.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d0e1f2a3b456"
down_revision: Union[str, Sequence[str], None] = "c9d8e7f6a012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add world_model_branches table."""
    op.create_table(
        "world_model_branches",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        # Branch identity
        sa.Column("name", sa.Text(), nullable=False),  # e.g., "corindel/exp-1"
        sa.Column("ref_prefix", sa.Text(), nullable=False),  # e.g., "corindel"
        sa.Column("branch_name", sa.Text(), nullable=False),  # e.g., "exp-1" or "HEAD"
        # The 3 ref names this branch manages
        sa.Column("human_ref", sa.Text(), nullable=False),
        sa.Column("persona_ref", sa.Text(), nullable=False),
        sa.Column("world_ref", sa.Text(), nullable=False),
        # Lineage
        sa.Column("parent_branch_id", sa.UUID(), nullable=True),
        # Config
        sa.Column("is_main", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("hooks_enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("ref_prefix", "branch_name", name="uq_world_model_branches_prefix_name"),
        sa.ForeignKeyConstraint(
            ["parent_branch_id"],
            ["world_model_branches.id"],
            name="fk_world_model_branches_parent",
        ),
    )
    op.create_index("idx_world_model_branches_prefix", "world_model_branches", ["ref_prefix"])


def downgrade() -> None:
    """Remove world_model_branches table."""
    op.drop_index("idx_world_model_branches_prefix", table_name="world_model_branches")
    op.drop_table("world_model_branches")
