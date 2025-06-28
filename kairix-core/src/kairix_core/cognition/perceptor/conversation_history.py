from __future__ import annotations

import logging

from neomodel import db
from rich import pretty

from kairix_core.cognition import Perceptor
from kairix_core.types.cognition import Perception, Stimulus, StimulusType

logger = logging.getLogger(__name__)


class ConversationHistoryPerceptor(Perceptor):
    """
    A perceptor that stores conversation history in Neo4j.

    It processes two types of stimuli:
    - user_message: Stores the user's input
    - action_reflection: Stores the assistant's response

    This creates a rolling conversation history in the database.
    """

    def __init__(self, agent_id: str = "default", window_size: int = 50):
        self.agent_id = agent_id
        self.window_size = window_size
        self.transient_user_msg_buffer = ""
        self._cached_history: list[dict[str, str]] | None = None

    async def perceive(self, stimulus: Stimulus) -> list[Perception]:
        # Load history from DB only on first access
        if self._cached_history is None:
            self._cached_history = await self._load_history_from_db()

        if stimulus.type == StimulusType.user_message:
            if self.transient_user_msg_buffer:
                logger.warning("Invocation of additional user message with transient outstanding,"
                           " ambiguous behavior. Assuming additivity.")
            self.transient_user_msg_buffer += stimulus.content

        elif stimulus.type == StimulusType.self_perception:
            if self.transient_user_msg_buffer:
                user_message = self.transient_user_msg_buffer
                self.transient_user_msg_buffer = ""  # Clear buffer after use
                await self._store_conversation_pair(user_message, stimulus.content)
                # Update cache with new pair
                self._cached_history.append({
                    "user": user_message,
                    "assistant": stimulus.content
                })
                # Keep only window_size most recent items
                if len(self._cached_history) > self.window_size:
                    self._cached_history = self._cached_history[-self.window_size:]
            else:
                logger.warning("Transient user message unexpectedly empty upon receipt of self reflection.")

        else:
            logger.info(f"No action for Conversation History on stimulus of type {stimulus.type}")

        return [Perception("conversation-history.v1",
                           pretty.pretty_repr(self._cached_history))]




    async def _store_conversation_pair(
        self, user_message: str, assistant_message: str
    ) -> None:
        """Store a conversation pair in Neo4j."""

        query = """
        // Create new conversation pair
        CREATE (m:ConversationPair {
            agent_id: $agent_id,
            user_message: $user_message,
            assistant_message: $assistant_message,
            timestamp: datetime()
        })
        
        // Count total pairs for this agent
        WITH m
        MATCH (cp:ConversationPair {agent_id: $agent_id})
        RETURN count(cp) as total_pairs
        """

        results, _ = db.cypher_query(
            query,
            {
                "agent_id": self.agent_id,
                "user_message": user_message,
                "assistant_message": assistant_message,
            },
        )

        if results:
            total = results[0][0]
            logger.info(f"Stored conversation pair. Total pairs: {total}")

    async def _load_history_from_db(self) -> list[dict[str, str]]:
        """Load conversation history from database on first access."""
        query = """
        MATCH (cp:ConversationPair {agent_id: $agent_id})
        RETURN cp.user_message as user, cp.assistant_message as assistant
        ORDER BY cp.timestamp DESC
        LIMIT $limit
        """

        results, _ = db.cypher_query(
            query, {"agent_id": self.agent_id, "limit": self.window_size}
        )

        # Convert results to dict format and return in chronological order
        pairs = [{"user": row[0], "assistant": row[1]} for row in results]
        return list(reversed(pairs))

    async def get_recent_context(
        self, limit: int | None = None
    ) -> list[dict[str, str]]:
        """Retrieve recent conversation pairs from cache."""
        if self._cached_history is None:
            self._cached_history = await self._load_history_from_db()
        
        if limit is None:
            return self._cached_history
        else:
            return self._cached_history[-limit:]
