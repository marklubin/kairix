"""add_agent_id_to_passages

Revision ID: g2b3c4d5e678
Revises: f1a2b3c4d567
Create Date: 2025-12-31 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "g2b3c4d5e678"
down_revision: str | Sequence[str] | None = "f1a2b3c4d567"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add agent_id column to passages table for agent-scoped searches."""
    op.add_column("passages", sa.Column("agent_id", sa.Text(), nullable=True))
    op.create_index("idx_passages_agent_id", "passages", ["agent_id"])


def downgrade() -> None:
    """Remove agent_id column from passages table."""
    op.drop_index("idx_passages_agent_id", table_name="passages")
    op.drop_column("passages", "agent_id")
