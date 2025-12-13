"""add_block_labels_to_agent_definitions

Revision ID: 5a625f728d28
Revises: c3d4e5f6a7b8
Create Date: 2025-12-12 16:04:13.122079

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5a625f728d28'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add universal_block_labels and subagent_block_labels columns to agent_definitions.

    - universal_block_labels: Blocks attached to conversational agent + ALL subagents
    - subagent_block_labels: Blocks attached to declaring subagent + conversational agent only
    """
    op.add_column(
        "agent_definitions",
        sa.Column(
            "universal_block_labels",
            sa.ARRAY(sa.String(64)),
            server_default="{}",
            nullable=False,
        ),
    )
    op.add_column(
        "agent_definitions",
        sa.Column(
            "subagent_block_labels",
            sa.ARRAY(sa.String(64)),
            server_default="{}",
            nullable=False,
        ),
    )

    # Seed initial values based on agent type
    op.execute("""
        UPDATE agent_definitions SET
            universal_block_labels = ARRAY['persona', 'human'],
            subagent_block_labels = ARRAY['focus']
        WHERE agent_type = 'conversational'
    """)
    op.execute("""
        UPDATE agent_definitions SET
            universal_block_labels = ARRAY['persona', 'human'],
            subagent_block_labels = ARRAY['last_session_summary']
        WHERE agent_type = 'reflector'
    """)
    op.execute("""
        UPDATE agent_definitions SET
            universal_block_labels = ARRAY['persona', 'human'],
            subagent_block_labels = ARRAY['background_insights']
        WHERE agent_type = 'insights'
    """)


def downgrade() -> None:
    """Remove universal_block_labels and subagent_block_labels columns."""
    op.drop_column("agent_definitions", "subagent_block_labels")
    op.drop_column("agent_definitions", "universal_block_labels")
