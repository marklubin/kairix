"""
SQLite-based conversation history perceptor.

This module replaces the Neo4j-based ConversationHistoryPerceptor with a SQLite implementation
that properly handles sequential message storage with ACID guarantees.
"""
from __future__ import annotations

import logging
from typing import Optional

from rich import pretty
from sqlalchemy.exc import IntegrityError

from kairix_core.cognition import Perceptor
from kairix_core.runtime.storage import StorageRuntime
from kairix_core.types.cognition import Perception, Stimulus, StimulusType
from kairix_core.types.db import Agent, ConversationMessage

logger = logging.getLogger(__name__)


class SQLiteConversationHistoryPerceptor(Perceptor):
    """
    A perceptor that stores conversation history in SQLite.

    It processes two types of stimuli:
    - user_message: Stores the user's input
    - self_perception: Stores the assistant's response paired with the user message

    This creates a rolling conversation history in the database with proper
    sequence ordering per thread.
    """

    def __init__(
        self, 
        agent_id: str = "default",
        user_id: str = "default_user", 
        window_size: int = 25,
        storage: Optional[StorageRuntime] = None
    ):
        self.agent_name = agent_id
        self.user_id = user_id
        self.window_size = window_size
        self.storage = storage or StorageRuntime()
        self.transient_user_msg_buffer = ""
        self._cached_history: list[dict[str, str]] | None = None
        self._agent_id: Optional[int] = None
        self._thread_id: Optional[str] = None
        
        # Initialize agent and thread
        self._init_agent_and_thread()

    def _init_agent_and_thread(self):
        """Initialize or get the agent ID and set thread ID."""
        with self.storage.session() as session:
            agent_dao = self.storage.get_dao(Agent, session)
            
            # Get or create agent
            agent = agent_dao.find_one_by(name=self.agent_name)
            if not agent:
                agent = agent_dao.create(name=self.agent_name)
                session.commit()
            
            self._agent_id = agent.id
            self._thread_id = f"{self.agent_name}_{self.user_id}"

    async def perceive(self, stimulus: Stimulus) -> list[Perception]:
        # Load history from DB only on first access
        if self._cached_history is None:
            self._cached_history = await self._load_history_from_db()

        if stimulus.type == StimulusType.user_message:
            if self.transient_user_msg_buffer:
                logger.warning(
                    "Invocation of additional user message with transient outstanding, "
                    "ambiguous behavior. Assuming additivity."
                )
            self.transient_user_msg_buffer += stimulus.content

        elif stimulus.type == StimulusType.self_perception:
            if self.transient_user_msg_buffer:
                user_message = self.transient_user_msg_buffer
                self.transient_user_msg_buffer = ""  # Clear buffer after use
                await self._store_conversation_pair(user_message, stimulus.content)
                
                # Update cache with new messages
                self._cached_history.extend([
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": stimulus.content}
                ])
                
                # Keep only window_size most recent items
                if len(self._cached_history) > self.window_size:
                    self._cached_history = self._cached_history[-self.window_size:]
            else:
                logger.warning(
                    "Transient user message unexpectedly empty upon receipt of self reflection."
                )

        else:
            logger.info(f"No action for Conversation History on stimulus of type {stimulus.type}")

        return [
            Perception("conversation-history.v1", pretty.pretty_repr(self._cached_history))
        ]

    async def _store_conversation_pair(
        self, user_message: str, assistant_message: str
    ) -> None:
        """Store a conversation pair in SQLite with proper sequencing."""
        with self.storage.session() as session:
            msg_dao = self.storage.get_dao(ConversationMessage, session)
            
            # Get the last sequence number for this thread
            last_msg = session.query(ConversationMessage).filter_by(
                thread_id=self._thread_id
            ).order_by(ConversationMessage.sequence_number.desc()).first()
            
            next_seq = 1 if not last_msg else last_msg.sequence_number + 1
            
            try:
                # Store user message
                msg_dao.create(
                    agent_id=self._agent_id,
                    user_id=self.user_id,
                    thread_id=self._thread_id,
                    sequence_number=next_seq,
                    role="user",
                    content=user_message
                )
                
                # Store assistant message
                msg_dao.create(
                    agent_id=self._agent_id,
                    user_id=self.user_id,
                    thread_id=self._thread_id,
                    sequence_number=next_seq + 1,
                    role="assistant",
                    content=assistant_message
                )
                
                session.commit()
                logger.info(f"Stored conversation pair. Sequence: {next_seq}, {next_seq + 1}")
                
            except IntegrityError as e:
                session.rollback()
                logger.error(f"Failed to store conversation pair: {e}")
                raise

    async def _load_history_from_db(self) -> list[dict[str, str]]:
        """Load conversation history from database on first access."""
        with self.storage.session() as session:
            # Query messages for this thread ordered by sequence
            messages = session.query(ConversationMessage).filter_by(
                thread_id=self._thread_id
            ).order_by(
                ConversationMessage.sequence_number.desc()
            ).limit(self.window_size).all()
            
            # Convert to dict format and return in chronological order
            history = [
                {"role": msg.role, "content": msg.content}
                for msg in reversed(messages)
            ]
            
            return history

    async def get_recent_context(
        self, limit: int | None = None
    ) -> list[dict[str, str]]:
        """Retrieve recent conversation messages from cache."""
        if self._cached_history is None:
            self._cached_history = await self._load_history_from_db()
        
        if limit is None:
            return self._cached_history
        else:
            return self._cached_history[-limit:]