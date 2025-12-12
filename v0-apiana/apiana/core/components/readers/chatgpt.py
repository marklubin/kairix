"""
ChatGPT export reader component.
"""

import time
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

from apiana.core.components.common import ComponentResult
from apiana.core.components.readers.base import Reader
from apiana.types.chat_fragment import ChatFragment
from apiana import utils

logger = logging.getLogger(__name__)


class ChatGPTExportReader(Reader):
    """Reader component for ChatGPT export JSON files."""
    
    # Type specifications
    input_types = [str, Path]  # File path as string or Path object
    output_types = [List[ChatFragment]]  # List of ChatFragment objects
    
    def __init__(self, name: str = "chatgpt_export_reader", config: dict = None):
        super().__init__(name, config)
    
    def validate_input(self, input_data) -> List[str]:
        """Validate that input is a valid file path."""
        errors = []
        
        if not isinstance(input_data, (str, Path)):
            errors.append("Input must be a file path (string or Path object)")
            return errors
        
        file_path = Path(input_data)
        
        if not file_path.exists():
            errors.append(f"File does not exist: {file_path}")
        elif not file_path.is_file():
            errors.append(f"Path is not a file: {file_path}")
        elif file_path.suffix.lower() != '.json':
            errors.append(f"File must be a JSON file, got: {file_path.suffix}")
        
        return errors
    
    def read(self, source: str) -> ComponentResult:
        """Read ChatGPT export file and return ChatFragments."""
        start_time = time.time()
        
        try:
            fragments = self._load_chatgpt_export(source)
            
            execution_time = (time.time() - start_time) * 1000
            
            metadata = {
                'source_file': str(source),
                'fragments_loaded': len(fragments),
                'total_messages': sum(len(f.messages) for f in fragments),
                'file_size_bytes': Path(source).stat().st_size
            }
            
            return ComponentResult(
                data=fragments,
                metadata=metadata,
                execution_time_ms=execution_time
            )
            
        except json.JSONDecodeError as e:
            return ComponentResult(
                data=[],
                errors=[f"Invalid JSON file: {e}"],
                execution_time_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return ComponentResult(
                data=[],
                errors=[f"Failed to load ChatGPT export: {e}"],
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def _load_chatgpt_export(self, file_path: str) -> List[ChatFragment]:
        """Load ChatGPT export file and return list of ChatFragments."""
        fragments = []
        
        logger.info(f"🔍 Starting to process file: {file_path}")
        with open(file_path, "r", encoding="utf-8") as file:
            conversations = json.load(file)
        
        if not isinstance(conversations, list):
            logger.error("Invalid file format: expected list of conversations")
            raise ValueError("Invalid file format: expected list of conversations")
        
        print(f"🔍 Found {len(conversations)} conversations to process")
        
        # Convert to ChatFragments
        fragments = self._load_fragments_from_export(conversations)
        failed_imports = len(conversations) - len(fragments)
        
        # Log results
        for i, fragment in enumerate(fragments):
            print(
                f"✅ Processed conversation {i}: '{fragment.title}' "
                f"({len(fragment.messages)} messages)"
            )
        
        if failed_imports > 0:
            print(f"⚠️  Skipped {failed_imports} conversations due to errors")
        
        return fragments
    
    def _load_fragments_from_export(self, export_data: List[Dict]) -> List[ChatFragment]:
        """Load multiple conversations from ChatGPT export format."""
        fragments = []
        
        for conv_data in export_data:
            try:
                fragment = self._fragment_from_export_format_dict(conv_data)
                if fragment and fragment.messages:  # Only add non-empty conversations
                    fragments.append(fragment)
            except Exception as e:
                logger.warning(f"Skipping conversation due to error: {e}")
                continue
        
        return fragments
    
    def _fragment_from_export_format_dict(self, data: Dict) -> Optional[ChatFragment]:
        """Convert ChatGPT export format to ChatFragment."""
        try:
            # Extract basic info
            fragment = ChatFragment(
                fragment_id=data.get("id", ""),
                title=data.get("title", "untitled conversation"),
                openai_conversation_id=data.get("id", "")
            )
            
            # Parse timestamps
            create_time = utils.parse_timestamp(data.get("create_time"))
            if create_time:
                fragment.create_time = create_time
                
            update_time = utils.parse_timestamp(data.get("update_time"))
            if update_time:
                fragment.update_time = update_time
            
            # Extract messages from mapping
            mapping_data = data.get("mapping", {})
            messages_data = self._extract_messages_from_mapping(mapping_data)
            
            # Add messages to fragment
            for msg_data in messages_data:
                result = self._message_from_chatgpt_format(msg_data)
                if result:
                    chatformat_msg, metadata = result
                    fragment.messages.append(chatformat_msg)
                    fragment.message_metadata.append(metadata)
            
            return fragment
            
        except Exception as e:
            logger.error(f"Failed to convert ChatGPT export: {e}")
            raise
    
    def _extract_messages_from_mapping(self, mapping_data: Dict) -> List[Dict]:
        """
        Extract messages from ChatGPT mapping structure in chronological order.
        The mapping is a tree structure, so we need to traverse it properly.
        """
        if not isinstance(mapping_data, dict):
            return []
        
        # Find root node (node with no parent)
        root_id = None
        for node_id, node_data in mapping_data.items():
            if isinstance(node_data, dict) and not node_data.get("parent"):
                root_id = node_id
                break
        
        if not root_id:
            # Fallback: just extract all messages
            messages = []
            for node_data in mapping_data.values():
                if isinstance(node_data, dict) and node_data.get("message"):
                    messages.append(node_data)
            return messages
        
        # Traverse tree from root
        messages = []
        visited = set()
        
        def traverse(node_id: str):
            if node_id in visited or node_id not in mapping_data:
                return
            
            visited.add(node_id)
            node_data = mapping_data[node_id]
            
            if isinstance(node_data, dict):
                # Add this node's message if it exists
                if node_data.get("message"):
                    messages.append(node_data)
                
                # Visit children
                children = node_data.get("children", [])
                if isinstance(children, list):
                    for child_id in children:
                        traverse(child_id)
        
        traverse(root_id)
        return messages
    
    def _message_from_chatgpt_format(self, data: Dict) -> Optional[tuple]:
        """
        Extract message data from ChatGPT export format.
        Returns a tuple of (chatformat_message, metadata).
        """
        if not data or not isinstance(data, dict):
            return None
        
        message_data = data.get("message", {})
        if not message_data or not isinstance(message_data, dict):
            return None
        
        # Extract author info
        author = message_data.get("author", {})
        if not isinstance(author, dict):
            author = {}
        
        role = author.get("role")
        if not role or role not in ["user", "assistant", "system"]:
            return None
        
        # Extract content
        content_dict = message_data.get("content", {})
        content = self._extract_text_content(content_dict)
        
        if not content:
            return None
        
        # Create chatformat style message
        chatformat_msg = {
            'role': role,
            'content': content
        }
        
        # Extract metadata
        metadata_dict = message_data.get("metadata", {})
        if not isinstance(metadata_dict, dict):
            metadata_dict = {}
        
        metadata = {
            'message_id': message_data.get("id", ""),
            'content_type': content_dict.get("content_type", "text"),
            'model_slug': metadata_dict.get("model_slug", ""),
            'request_id': metadata_dict.get("request_id", ""),
            'timestamp': message_data.get("create_time"),
        }
        
        return chatformat_msg, metadata
    
    def _extract_text_content(self, content_dict: Dict) -> str:
        """Extract text content from ChatGPT content structure."""
        if not isinstance(content_dict, dict):
            return str(content_dict) if content_dict else ""
        
        # Handle different content types
        content_type = content_dict.get("content_type", "text")
        
        if content_type == "text":
            # Text messages have 'parts' array
            parts = content_dict.get("parts", [])
            if isinstance(parts, list):
                return "\n".join(str(part) for part in parts if part)
            return ""
        
        elif content_type == "code":
            # Code messages might have different structure
            code = content_dict.get("text", "")
            language = content_dict.get("language", "")
            if language:
                return f"```{language}\n{code}\n```"
            return f"```\n{code}\n```"
        
        else:
            # For other types, try to get any text representation
            return content_dict.get("text", str(content_dict))


# Additional utility functions that were in the loader module
def save_as_plain_text(fragments: List[ChatFragment], output_dir: str) -> None:
    """Save ChatFragments as plain text files."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    for i, fragment in enumerate(fragments):
        # Generate filename from title or ID
        safe_title = fragment.title.replace('/', '_').replace('\\', '_')[:50]
        filename = f"{i:04d}_{safe_title}.txt"
        
        filepath = output_path / filename
        fragment.save_to_file(filepath, include_metadata=True)
        
        logger.info(f"Saved conversation to {filepath}")


def load_from_plain_text(input_dir: str) -> List[ChatFragment]:
    """Load ChatFragments from plain text files."""
    input_path = Path(input_dir)
    fragments = []
    
    for filepath in sorted(input_path.glob("*.txt")):
        try:
            fragment = ChatFragment.from_file(filepath)
            fragments.append(fragment)
            logger.info(f"Loaded conversation from {filepath}")
        except Exception as e:
            logger.warning(f"Failed to load {filepath}: {e}")
    
    return fragments