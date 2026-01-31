"""Rename embedding_qwen3 to embedding_openai.

Revision ID: h3c4d5e6f789
Revises: g2b3c4d5e678
Create Date: 2025-01-30

The embedding field was originally for qwen3 embeddings but now uses
OpenAI text-embedding-3-large. Rename for clarity.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "h3c4d5e6f789"
down_revision = "g2b3c4d5e678"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename column in passages table
    op.alter_column("passages", "embedding_qwen3", new_column_name="embedding_openai")

    # Rename column in passages_archive table
    op.alter_column("passages_archive", "embedding_qwen3", new_column_name="embedding_openai")

    # Drop old index and create new one with correct name
    op.drop_index("idx_passages_embedding", table_name="passages")
    op.create_index(
        "idx_passages_embedding_openai",
        "passages",
        ["embedding_openai"],
        postgresql_using="ivfflat",
        postgresql_ops={"embedding_openai": "vector_cosine_ops"},
    )


def downgrade() -> None:
    # Rename back
    op.alter_column("passages", "embedding_openai", new_column_name="embedding_qwen3")
    op.alter_column("passages_archive", "embedding_openai", new_column_name="embedding_qwen3")

    # Restore old index name
    op.drop_index("idx_passages_embedding_openai", table_name="passages")
    op.create_index(
        "idx_passages_embedding",
        "passages",
        ["embedding_qwen3"],
        postgresql_using="ivfflat",
        postgresql_ops={"embedding_qwen3": "vector_cosine_ops"},
    )
