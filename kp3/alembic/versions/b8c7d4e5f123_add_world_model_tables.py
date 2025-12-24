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
    """Add passage_refs and extraction_prompts tables."""
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
    """Remove passage_refs and extraction_prompts tables."""
    op.drop_index("idx_extraction_prompts_active", table_name="extraction_prompts")
    op.drop_index("idx_extraction_prompts_name", table_name="extraction_prompts")
    op.drop_table("extraction_prompts")
    op.drop_index("idx_passage_refs_passage_id", table_name="passage_refs")
    op.drop_table("passage_refs")
