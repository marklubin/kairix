"""
ChatFragmentWriter component for persisting ChatFragments to the application store.

This component provides transparent ChatFragment persistence during pipeline execution.
It accepts ChatFragments, stores them in the ApplicationStore, and passes them through
unchanged for downstream processing.
"""

from typing import List, Any, Type, Optional
import logging

from apiana.core.components.common import ComponentResult
from apiana.core.components.writers.base import Writer
from apiana.stores import ApplicationStore
from apiana.types.chat_fragment import ChatFragment
from apiana.types.configuration import Neo4jConfig


class ChatFragmentWriter(Writer):
    """
    Writer component for persisting ChatFragments.
    
    This component transparently captures and persists ChatFragments flowing through
    a pipeline while passing them through unchanged for further processing.
    
    Key features:
    - Transparent pass-through operation
    - Handles single ChatFragment or List[ChatFragment]
    - Configurable tagging for stored fragments
    - Error handling that doesn't break pipeline flow
    """
    
    # Type specifications
    input_types: List[Type] = [List[ChatFragment], ChatFragment]
    output_types: List[Type] = [List[ChatFragment], ChatFragment]
    
    def __init__(self, store: ApplicationStore, tags: Optional[List[str]] = None, name: str = "ChatFragmentWriter", **kwargs):
        """
        Initialize the ChatFragmentWriter.
        
        Args:
            store: ApplicationStore instance for data persistence
            tags: Optional tags to apply to stored fragments
            name: Component name for identification
            **kwargs: Additional component configuration
        """
        super().__init__(name=name, **kwargs)
        self.store = store
        self.tags = tags or []
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    @classmethod
    def from_config(cls, config: Neo4jConfig, tags: Optional[List[str]] = None, **kwargs):
        """
        Create ChatFragmentWriter from Neo4j configuration.
        
        Args:
            config: Neo4j configuration
            tags: Optional tags to apply to stored fragments
            **kwargs: Additional component configuration
            
        Returns:
            ChatFragmentWriter instance
        """
        store = ApplicationStore(config)
        return cls(store=store, tags=tags, **kwargs)
    
    def validate_input(self, input_data: Any) -> ComponentResult:
        """Validate that input is ChatFragment or List[ChatFragment]."""
        result = ComponentResult(data=None)
        
        if isinstance(input_data, ChatFragment):
            return result
        elif isinstance(input_data, list):
            if not input_data:
                result.add_warning("Empty list provided - nothing to store")
                return result
            if all(isinstance(item, ChatFragment) for item in input_data):
                return result
            else:
                result.add_error("All items in list must be ChatFragment instances")
        else:
            result.add_error(f"Input must be ChatFragment or List[ChatFragment], got {type(input_data)}")
        
        return result
    
    def process(self, input_data: Any) -> ComponentResult:
        """
        Process and store ChatFragments while passing them through.
        
        Args:
            input_data: ChatFragment or List[ChatFragment] to store
            
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
            fragments = input_data if isinstance(input_data, list) else [input_data]
            stored_count = 0
            failed_count = 0
            
            # Store each fragment
            for fragment in fragments:
                try:
                    self.store.store_fragment(fragment, tags=self.tags)
                    stored_count += 1
                except Exception as e:
                    failed_count += 1
                    result.add_warning(f"Failed to store fragment {fragment.fragment_id}: {str(e)}")
            
            # Add metadata about storage operation
            result.metadata.update({
                "fragments_stored": stored_count,
                "fragments_failed": failed_count,
                "total_fragments": len(fragments),
                "tags_applied": self.tags,
                "entity_type": "chat_fragment"
            })
            
            # Always pass through the original data unchanged
            result.data = input_data
            
            if stored_count > 0:
                self.logger.info(f"Stored {stored_count} ChatFragments to ApplicationStore")
            if failed_count > 0:
                self.logger.warning(f"Failed to store {failed_count} ChatFragments")
            
        except Exception as e:
            # Even on failure, pass through the data but log the error
            result.add_warning(f"ChatFragmentWriter processing failed: {str(e)}")
            result.data = input_data
        
        return result
    
    def write(self, data: Any, destination: str = "default") -> ComponentResult:
        """
        Write method for Writer interface compatibility.
        
        Args:
            data: ChatFragment or List[ChatFragment] to store
            destination: Ignored (ApplicationStore uses default database)
            
        Returns:
            ComponentResult with stored data
        """
        return self.process(data)