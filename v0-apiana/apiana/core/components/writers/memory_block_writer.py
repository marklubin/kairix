"""
MemoryBlockWriter component for persisting memory blocks to agent-specific storage.

This component stores processed data (summaries + embeddings + fragments) as
experiential memories in the AgentMemoryStore for a specific agent.
"""

from typing import List, Any, Type, Optional

from apiana.core.components.common import ComponentResult
from apiana.core.components.writers.base import Writer
from apiana.stores import AgentMemoryStore
from apiana.types.chat_fragment import ChatFragment
from apiana.types.configuration import Neo4jConfig


class MemoryBlockWriter(Writer):
    """
    Writer component for persisting memory blocks to agent-specific storage.
    
    This component accepts processed data containing summaries, embeddings, and
    ChatFragments, then stores them as experiential memories in the agent's
    dedicated database.
    
    Expected input format:
    - Single dict: {"summary": str, "embedding": List[float], "fragment": ChatFragment}
    - List of such dicts
    
    Key features:
    - Agent-specific memory storage
    - Configurable memory tags
    - Pass-through operation for pipeline chaining
    - Robust error handling
    """
    
    # Type specifications - expects processed memory data
    input_types: List[Type] = [List[dict], dict]
    output_types: List[Type] = [List[dict], dict]
    
    def __init__(
        self, 
        store: AgentMemoryStore, 
        agent_id: str,
        tags: Optional[List[str]] = None, 
        name: str = "MemoryBlockWriter",
        **kwargs
    ):
        """
        Initialize the MemoryBlockWriter.
        
        Args:
            store: AgentMemoryStore instance for data persistence
            agent_id: Agent identifier for memory storage
            tags: Optional tags to apply to stored memories
            name: Component name for identification
            **kwargs: Additional component configuration
        """
        super().__init__(name=name, **kwargs)
        self.store = store
        self.agent_id = agent_id
        self.tags = tags or ["memory", "conversation", "experience"]
        
        # Initialize logger
        import logging
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    @classmethod
    def from_config(
        cls, 
        config: Neo4jConfig, 
        agent_id: str,
        tags: Optional[List[str]] = None, 
        **kwargs
    ):
        """
        Create MemoryBlockWriter from Neo4j configuration.
        
        Args:
            config: Neo4j configuration
            agent_id: Agent identifier for memory storage
            tags: Optional tags to apply to stored memories
            **kwargs: Additional component configuration
            
        Returns:
            MemoryBlockWriter instance
        """
        store = AgentMemoryStore(config, agent_id)
        return cls(store=store, agent_id=agent_id, tags=tags, **kwargs)
    
    def validate_input(self, input_data: Any) -> ComponentResult:
        """Validate that input contains the expected structure for memory storage."""
        result = ComponentResult(data=input_data)
        
        if isinstance(input_data, dict):
            if not self._is_valid_memory_dict(input_data):
                result.add_error(
                    "Dictionary must contain 'summary', 'embedding', and 'fragment' keys. "
                    f"Found keys: {list(input_data.keys())}"
                )
        elif isinstance(input_data, list):
            if not input_data:
                result.add_warning("Empty list provided - nothing to store")
                return result
            
            for i, item in enumerate(input_data):
                if not isinstance(item, dict):
                    result.add_error(f"Item {i} must be a dictionary, got {type(item)}")
                elif not self._is_valid_memory_dict(item):
                    result.add_error(
                        f"Item {i} must contain 'summary', 'embedding', and 'fragment' keys. "
                        f"Found keys: {list(item.keys())}"
                    )
        else:
            result.add_error(f"Input must be dict or List[dict], got {type(input_data)}")
        
        return result
    
    def _is_valid_memory_dict(self, item: dict) -> bool:
        """Check if a dictionary has the required structure for memory storage."""
        required_keys = {'summary', 'embedding', 'fragment'}
        return all(key in item for key in required_keys)
    
    def _validate_memory_item(self, item: dict) -> List[str]:
        """Validate individual memory item structure and return error messages."""
        errors = []
        
        # Check fragment type
        fragment = item.get('fragment')
        if not isinstance(fragment, ChatFragment):
            errors.append(f"Fragment must be ChatFragment instance, got {type(fragment)}")
        
        # Check summary type
        summary = item.get('summary')
        if not isinstance(summary, str):
            errors.append(f"Summary must be string, got {type(summary)}")
        elif not summary.strip():
            errors.append("Summary cannot be empty")
        
        # Check embedding type
        embedding = item.get('embedding')
        if not isinstance(embedding, list):
            errors.append(f"Embedding must be list, got {type(embedding)}")
        elif not all(isinstance(x, (int, float)) for x in embedding):
            errors.append("Embedding must be list of numbers")
        elif not embedding:
            errors.append("Embedding cannot be empty")
        
        return errors
    
    def process(self, input_data: Any) -> ComponentResult:
        """
        Process and store memory blocks while passing them through.
        
        Args:
            input_data: Dict or List[Dict] containing memory data
            
        Returns:
            ComponentResult with the original input data (pass-through)
        """
        result = self.validate_input(input_data)
        if not result.success:
            return result
        
        # Handle empty list case
        if isinstance(input_data, list) and not input_data:
            result.data = input_data
            return result
        
        try:
            # Normalize to list for processing
            memory_items = input_data if isinstance(input_data, list) else [input_data]
            stored_count = 0
            failed_count = 0
            
            # Store each memory item
            for i, item in enumerate(memory_items):
                try:
                    # Validate individual item structure
                    validation_errors = self._validate_memory_item(item)
                    if validation_errors:
                        for error in validation_errors:
                            result.add_warning(f"Memory item {i}: {error}")
                        failed_count += 1
                        continue
                    
                    fragment = item['fragment']
                    summary = item['summary']
                    embedding = item['embedding']
                    
                    # Store in agent memory
                    self.store.store_fragment(
                        fragment=fragment,
                        summary=summary,
                        embeddings=embedding,
                        tags=self.tags
                    )
                    
                    stored_count += 1
                    
                except Exception as e:
                    failed_count += 1
                    result.add_warning(f"Failed to store memory item {i}: {str(e)}")
            
            # Add metadata about storage operation
            result.metadata.update({
                "memories_stored": stored_count,
                "memories_failed": failed_count,
                "total_memories": len(memory_items),
                "agent_id": self.agent_id,
                "tags_applied": self.tags,
                "entity_type": "memory_block",
                "database_name": self.store.get_database_name()
            })
            
            # Always pass through the original data unchanged
            result.data = input_data
            
            if stored_count > 0:
                self.logger.info(
                    f"Stored {stored_count} memory blocks for agent '{self.agent_id}' "
                    f"in database '{self.store.get_database_name()}'"
                )
            if failed_count > 0:
                self.logger.warning(f"Failed to store {failed_count} memory blocks")
            
        except Exception as e:
            # Even on failure, pass through the data but log the error
            result.add_warning(f"MemoryBlockWriter processing failed: {str(e)}")
            result.data = input_data
        
        return result
    
    def write(self, data: Any, destination: str = "default") -> ComponentResult:
        """
        Write method for Writer interface compatibility.
        
        Args:
            data: Memory data to store
            destination: Agent ID (overrides instance agent_id if provided and different)
            
        Returns:
            ComponentResult with stored data
        """
        # If destination is provided and different from instance agent_id, log warning
        if destination != "default" and destination != self.agent_id:
            self.logger.warning(
                f"Destination agent_id '{destination}' differs from configured agent_id '{self.agent_id}'. "
                f"Using configured agent_id."
            )
        
        return self.process(data)