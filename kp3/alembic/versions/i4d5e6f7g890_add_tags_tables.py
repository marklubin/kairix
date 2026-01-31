"""Add tags and passage_tags tables.

Revision ID: i4d5e6f7g890
Revises: h3c4d5e6f789
Create Date: 2025-01-30

Adds tagging system for passages:
- tags table with embeddings and FTS support
- passage_tags junction table for many-to-many relationships
"""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

# revision identifiers, used by Alembic.
revision = "i4d5e6f7g890"
down_revision = "h3c4d5e6f789"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tags table
    op.create_table(
        "tags",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("agent_id", sa.Text(), nullable=False),
        sa.Column("canonical_key", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "name_tsv",
            sa.Computed(
                "to_tsvector('english', name || ' ' || coalesce(description, ''))",
                persisted=True,
            ),
            nullable=True,
        ),
        sa.Column("embedding_openai", Vector(1024), nullable=True),
        sa.Column("passage_count", sa.Integer(), server_default="0", nullable=False),
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
        sa.UniqueConstraint("agent_id", "canonical_key", name="uq_tags_agent_canonical_key"),
    )

    # Create indexes on tags table
    op.create_index("idx_tags_agent_id", "tags", ["agent_id"])
    op.create_index("idx_tags_name_tsv", "tags", ["name_tsv"], postgresql_using="gin")
    op.create_index(
        "idx_tags_embedding_openai",
        "tags",
        ["embedding_openai"],
        postgresql_using="ivfflat",
        postgresql_ops={"embedding_openai": "vector_cosine_ops"},
    )

    # Create passage_tags junction table
    op.create_table(
        "passage_tags",
        sa.Column("passage_id", sa.UUID(), nullable=False),
        sa.Column("tag_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["passage_id"], ["passages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("passage_id", "tag_id"),
    )

    # Create indexes on passage_tags
    op.create_index("idx_passage_tags_passage_id", "passage_tags", ["passage_id"])
    op.create_index("idx_passage_tags_tag_id", "passage_tags", ["tag_id"])


def downgrade() -> None:
    # Drop passage_tags table and indexes
    op.drop_index("idx_passage_tags_tag_id", table_name="passage_tags")
    op.drop_index("idx_passage_tags_passage_id", table_name="passage_tags")
    op.drop_table("passage_tags")

    # Drop tags table and indexes
    op.drop_index("idx_tags_embedding_openai", table_name="tags")
    op.drop_index("idx_tags_name_tsv", table_name="tags")
    op.drop_index("idx_tags_agent_id", table_name="tags")
    op.drop_table("tags")
