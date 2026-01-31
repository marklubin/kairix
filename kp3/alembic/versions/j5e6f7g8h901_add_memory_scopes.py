"""Add memory_scopes table.

Revision ID: j5e6f7g8h901
Revises: i4d5e6f7g890
Create Date: 2025-01-31

Adds memory_scopes table for defining dynamic search closures using refs.
Scope definitions are stored as passages (type="scope_definition").
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "j5e6f7g8h901"
down_revision = "i4d5e6f7g890"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create memory_scopes table
    op.create_table(
        "memory_scopes",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("agent_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("head_ref", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
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
        sa.UniqueConstraint("agent_id", "name", name="uq_memory_scopes_agent_name"),
    )

    # Create index on agent_id for efficient listing
    op.create_index("idx_memory_scopes_agent_id", "memory_scopes", ["agent_id"])


def downgrade() -> None:
    op.drop_index("idx_memory_scopes_agent_id", table_name="memory_scopes")
    op.drop_table("memory_scopes")
