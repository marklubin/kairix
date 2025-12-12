"""WebSocket connection manager for event streaming."""

import asyncio
import json
import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for agent event streams.

    Tracks active connections per agent_id and dispatches events
    to all connected clients for a given agent.
    """

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def register(self, agent_id: str, websocket: WebSocket) -> None:
        """Register a WebSocket connection for an agent."""
        async with self._lock:
            self._connections[agent_id].add(websocket)
            logger.info(
                "Registered event connection for agent %s (total: %d)",
                agent_id,
                len(self._connections[agent_id]),
            )

    async def unregister(self, agent_id: str, websocket: WebSocket) -> None:
        """Unregister a WebSocket connection for an agent."""
        async with self._lock:
            self._connections[agent_id].discard(websocket)
            if not self._connections[agent_id]:
                del self._connections[agent_id]
            logger.info("Unregistered event connection for agent %s", agent_id)

    async def dispatch(self, agent_id: str, event_data: dict) -> None:  # type: ignore[type-arg]
        """Push event to all connected clients for this agent.

        Args:
            agent_id: The agent whose clients should receive the event.
            event_data: The event payload to send as JSON.
        """
        async with self._lock:
            sockets = list(self._connections.get(agent_id, []))

        if not sockets:
            logger.debug("No active connections for agent %s, skipping dispatch", agent_id)
            return

        message = json.dumps(event_data)
        for ws in sockets:
            try:
                await ws.send_text(message)
            except Exception:  # noqa: BLE001
                # Client disconnected, will be cleaned up on next unregister
                logger.debug("Failed to send event to client, connection may be closed")


# Singleton instance
connection_manager = ConnectionManager()
