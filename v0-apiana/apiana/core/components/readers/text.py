"""
Plain text reader component.
"""

import time
from pathlib import Path
from typing import List

from apiana.core.components.common import ComponentResult
from apiana.core.components.readers.base import Reader
from apiana.types.chat_fragment import ChatFragment


class PlainTextReader(Reader):
    """Reader component for plain text conversation files."""
    
    def __init__(self, name: str = "plain_text_reader", config: dict = None):
        super().__init__(name, config)
    
    def validate_input(self, input_data) -> List[str]:
        """Validate that input is a valid file or directory path."""
        errors = []
        
        if not isinstance(input_data, (str, Path)):
            errors.append("Input must be a file or directory path")
            return errors
        
        path = Path(input_data)
        
        if not path.exists():
            errors.append(f"Path does not exist: {path}")
        
        return errors
    
    def read(self, source: str) -> ComponentResult:
        """Read plain text conversation files."""
        start_time = time.time()
        
        try:
            path = Path(source)
            fragments = []
            
            if path.is_file():
                # Single file
                if path.suffix.lower() == '.txt':
                    fragment = ChatFragment.from_file(path)
                    fragments.append(fragment)
            elif path.is_dir():
                # Directory of text files
                for txt_file in sorted(path.glob("*.txt")):
                    try:
                        fragment = ChatFragment.from_file(txt_file)
                        fragments.append(fragment)
                    except Exception:
                        # Add warning but continue processing
                        pass
            
            execution_time = (time.time() - start_time) * 1000
            
            metadata = {
                'source_path': str(source),
                'fragments_loaded': len(fragments),
                'total_messages': sum(len(f.messages) for f in fragments),
                'source_type': 'file' if path.is_file() else 'directory'
            }
            
            result = ComponentResult(
                data=fragments,
                metadata=metadata,
                execution_time_ms=execution_time
            )
            
            return result
            
        except Exception as e:
            return ComponentResult(
                data=[],
                errors=[f"Failed to load text files: {e}"],
                execution_time_ms=(time.time() - start_time) * 1000
            )