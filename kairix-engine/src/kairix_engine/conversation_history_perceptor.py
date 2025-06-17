from __future__ import annotations

import logging

from cognition_engine import Perception, Perceptor, Stimulus, StimulusType
from neomodel import config as neomodel_config
from neomodel import db

logger = logging.getLogger(__name__)


class ConversationHistoryPerceptor(Perceptor):
    """
    A perceptor that stores conversation history in Neo4j.
    
    It processes two types of stimuli:
    - user_message: Stores the user's input
    - action_reflection: Stores the assistant's response
    
    This creates a rolling conversation history in the database.
    """
    
    def __init__(self, store_url: str, agent_id: str = "default", max_pairs: int = 10):
        neomodel_config.DATABASE_URL = store_url
        db.set_connection(store_url)
        self.agent_id = agent_id
        self.max_pairs = max_pairs
        self._pending_user_message: str | None = None
    
    async def perceive(self, stimulus: Stimulus) -> list[Perception]:
        """Process conversation stimuli and store in database."""
        
        if stimulus.type == StimulusType.user_message:
            # Store user message temporarily
            self._pending_user_message = stimulus.content
            logger.debug(f"Stored pending user message: {stimulus.content[:50]}...")
            
        elif stimulus.type.value == "action_reflection":
            # Store the conversation pair when we get the assistant response
            if self._pending_user_message:
                await self._store_conversation_pair(
                    self._pending_user_message, 
                    stimulus.content
                )
                self._pending_user_message = None
            else:
                logger.warning(
                    "Received action_reflection without pending user message"
                )
        
        # This perceptor doesn't generate perceptions, it just stores data
        return []
    
    async def _store_conversation_pair(
        self, user_message: str, assistant_message: str
    ) -> None:
        """Store a conversation pair in Neo4j and maintain rolling window."""
        
        query = """
        // Create new conversation pair
        CREATE (m:ConversationPair {
            agent_id: $agent_id,
            user_message: $user_message,
            assistant_message: $assistant_message,
            timestamp: datetime()
        })
        
        WITH m
        
        // Get all conversation pairs for this agent
        MATCH (cp:ConversationPair {agent_id: $agent_id})
        WITH cp ORDER BY cp.timestamp DESC
        WITH collect(cp) as allPairs
        
        // Delete old pairs beyond max_pairs limit
        FOREACH (oldPair IN allPairs[$max_pairs..] | DELETE oldPair)
        
        RETURN size(allPairs) as total_pairs
        """
        
        results, _ = db.cypher_query(
            query,
            {
                "agent_id": self.agent_id,
                "user_message": user_message,
                "assistant_message": assistant_message,
                "max_pairs": self.max_pairs
            }
        )
        
        if results:
            total = results[0][0]
            logger.info(f"Stored conversation pair. Total pairs: {total}")
    
    async def get_recent_context(
        self, limit: int | None = None
    ) -> list[dict[str, str]]:
        """Retrieve recent conversation pairs from the database."""
        
        query = """
        MATCH (cp:ConversationPair {agent_id: $agent_id})
        RETURN cp.user_message as user, cp.assistant_message as assistant
        ORDER BY cp.timestamp DESC
        LIMIT $limit
        """
        
        results, _ = db.cypher_query(
            query,
            {
                "agent_id": self.agent_id,
                "limit": limit or self.max_pairs
            }
        )
        
        # Convert results to dict format and return in chronological order
        pairs = [{"user": row[0], "assistant": row[1]} for row in results]
        return list(reversed(pairs))