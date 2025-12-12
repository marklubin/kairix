"""
Fragment list reader component.
"""

import time
from typing import List

from apiana.core.components.common import ComponentResult
from apiana.core.components.readers.base import Reader
from apiana.types.chat_fragment import ChatFragment


class FragmentListReader(Reader):
    """Reader component that accepts a list of ChatFragments directly."""
    
    def __init__(self, name: str = "fragment_list_reader", config: dict = None):
        super().__init__(name, config)
    
    def validate_input(self, input_data) -> List[str]:
        """Validate that input is a list of ChatFragments."""
        errors = []
        
        if not isinstance(input_data, list):
            errors.append("Input must be a list of ChatFragments")
            return errors
        
        for i, item in enumerate(input_data):
            if not isinstance(item, ChatFragment):
                errors.append(f"Item {i} is not a ChatFragment: {type(item)}")
        
        return errors
    
    def read(self, source: List[ChatFragment]) -> ComponentResult:
        """Pass through the list of ChatFragments."""
        start_time = time.time()
        
        execution_time = (time.time() - start_time) * 1000
        
        metadata = {
            'fragments_count': len(source),
            'total_messages': sum(len(f.messages) for f in source),
            'source_type': 'fragment_list'
        }
        
        return ComponentResult(
            data=source,
            metadata=metadata,
            execution_time_ms=execution_time
        )