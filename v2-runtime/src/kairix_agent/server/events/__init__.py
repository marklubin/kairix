"""Server-side event streaming components.

Note: start_event_listener is intentionally not re-exported here to avoid
circular imports. Import directly from kairix_agent.server.events.listener.
"""

from kairix_agent.server.events.connection_manager import ConnectionManager, connection_manager

__all__ = [
    "ConnectionManager",
    "connection_manager",
]
