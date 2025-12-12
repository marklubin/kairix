"""Drop pg_notify trigger (replaced by Redis pub/sub).

Revision ID: a1b2c3d4e5f6
Revises: fb0df2b9147c
Create Date: 2025-12-07

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'fb0df2b9147c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the pg_notify trigger and function."""
    op.execute("DROP TRIGGER IF EXISTS agent_event_notify ON agent_events")
    op.execute("DROP FUNCTION IF EXISTS notify_agent_event")


def downgrade() -> None:
    """Recreate the pg_notify trigger and function."""
    op.execute("""
        CREATE OR REPLACE FUNCTION notify_agent_event() RETURNS trigger AS $$
        BEGIN
            PERFORM pg_notify('agent_events', jsonb_build_object(
                'id', NEW.id::text,
                'agent_id', NEW.agent_id,
                'event_type', NEW.event_type,
                'payload', NEW.payload,
                'created_at', NEW.created_at::text
            )::text);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER agent_event_notify
            AFTER INSERT ON agent_events
            FOR EACH ROW EXECUTE FUNCTION notify_agent_event();
    """)