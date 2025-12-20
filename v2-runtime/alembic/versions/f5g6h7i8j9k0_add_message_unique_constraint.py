"""Add unique constraint on session_messages.message_id.

Prevents the same Letta message from being in multiple sessions,
which could cause duplicate summarization.

Revision ID: f5g6h7i8j9k0
Revises: e4f5a6b7c8d9
Create Date: 2025-12-20
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f5g6h7i8j9k0"
down_revision: str | None = "e4f5a6b7c8d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add unique constraint on message_id to prevent duplicate session assignments
    # This ensures each Letta message can only belong to one session
    op.create_unique_constraint(
        "uq_session_messages_message_id",
        "session_messages",
        ["message_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_session_messages_message_id",
        "session_messages",
        type_="unique",
    )
