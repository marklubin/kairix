"""
Chunking components for splitting conversations into token-limited pieces.
"""

import time
import logging
import uuid
from typing import List
from dataclasses import dataclass

try:
    from transformers import AutoTokenizer
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

from apiana.core.components.common import ComponentResult
from apiana.core.components.chunkers.base import Chunker
from apiana.types.chat_fragment import ChatFragment

logger = logging.getLogger(__name__)


@dataclass
class ChunkingConfig:
    """Configuration for conversation chunking."""
    max_tokens: int = 5000
    model_name: str = "gpt2"  # Used for tokenization
    preserve_message_boundaries: bool = True
    overlap_tokens: int = 0  # Optional overlap between chunks
    min_chunk_size: int = 100  # Minimum tokens per chunk


class ConversationChunkerComponent(Chunker):
    """Component that chunks conversations into token-limited pieces."""
    
    # Type specifications
    input_types = [List[ChatFragment], ChatFragment]  # List of fragments or single fragment
    output_types = [List[ChatFragment]]  # Always outputs list of (possibly chunked) fragments
    
    def __init__(self, name: str = "conversation_chunker", config: dict = None):
        super().__init__(name, config)
        
        # Create chunking config from component config
        self.chunking_config = ChunkingConfig(
            max_tokens=self.config.get('max_tokens', 5000),
            model_name=self.config.get('model_name', 'gpt2'),
            preserve_message_boundaries=self.config.get('preserve_message_boundaries', True),
            overlap_tokens=self.config.get('overlap_tokens', 0),
            min_chunk_size=self.config.get('min_chunk_size', 100)
        )
        
        # Initialize tokenizer
        self.tokenizer = None
        self._init_tokenizer()
    
    def _init_tokenizer(self):
        """Initialize the tokenizer for token counting."""
        if HAS_TRANSFORMERS:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(self.chunking_config.model_name)
                # Add pad token if missing (needed for some models)
                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token
                logger.info(f"Loaded tokenizer for {self.chunking_config.model_name}")
            except Exception as e:
                logger.warning(f"Failed to load tokenizer: {e}. Using fallback counting.")
                self.tokenizer = None
        else:
            logger.warning("Transformers not available. Using approximate token counting.")
    
    def validate_input(self, input_data) -> List[str]:
        """Validate that input is a ChatFragment or list of ChatFragments."""
        errors = []
        
        if isinstance(input_data, list):
            if not all(isinstance(item, ChatFragment) for item in input_data):
                errors.append("All items in list must be ChatFragment instances")
        elif not isinstance(input_data, ChatFragment):
            errors.append("Input must be a ChatFragment or list of ChatFragments")
        
        return errors
    
    def chunk(self, data) -> ComponentResult:
        """Chunk conversations into token-limited fragments."""
        start_time = time.time()
        
        # Handle both single fragment and list of fragments
        fragments = data if isinstance(data, list) else [data]
        
        all_chunks = []
        stats = {
            'input_fragments': len(fragments),
            'output_chunks': 0,
            'fragments_chunked': 0,
            'fragments_unchanged': 0
        }
        
        for fragment in fragments:
            chunks = self._chunk_fragment(fragment)
            all_chunks.extend(chunks)
            
            if len(chunks) > 1:
                stats['fragments_chunked'] += 1
            else:
                stats['fragments_unchanged'] += 1
        
        stats['output_chunks'] = len(all_chunks)
        
        # Get detailed chunking statistics
        chunk_stats = self._get_chunk_stats(all_chunks)
        stats.update(chunk_stats)
        
        execution_time = (time.time() - start_time) * 1000
        
        return ComponentResult(
            data=all_chunks,
            metadata=stats,
            execution_time_ms=execution_time
        )
    
    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            Number of tokens
        """
        if self.tokenizer:
            try:
                tokens = self.tokenizer.encode(text, add_special_tokens=True)
                return len(tokens)
            except Exception as e:
                logger.warning(f"Tokenizer failed: {e}. Using fallback.")
        
        # Fallback: approximate token count (roughly 4 chars per token)
        return len(text) // 4
    
    def _count_fragment_tokens(self, fragment: ChatFragment) -> int:
        """
        Count total tokens in a conversation fragment.
        
        Args:
            fragment: The ChatFragment to count tokens for
            
        Returns:
            Total token count
        """
        total = 0
        for message in fragment.messages:
            # Count role + content + formatting
            message_text = f"{message['role']}: {message['content']}\n"
            total += self._count_tokens(message_text)
        return total
    
    def _chunk_fragment(self, fragment: ChatFragment) -> List[ChatFragment]:
        """
        Split a conversation fragment into token-limited chunks.
        
        Args:
            fragment: The ChatFragment to chunk
            
        Returns:
            List of ChatFragment chunks
        """
        total_tokens = self._count_fragment_tokens(fragment)
        
        # If already under limit, return as-is
        if total_tokens <= self.chunking_config.max_tokens:
            return [fragment]
        
        logger.info(f"Chunking conversation '{fragment.title}' ({total_tokens} tokens)")
        
        chunks = []
        current_messages = []
        current_tokens = 0
        
        for message in fragment.messages:
            message_text = f"{message['role']}: {message['content']}\n"
            message_tokens = self._count_tokens(message_text)
            
            # If single message exceeds limit, we need to split it
            if message_tokens > self.chunking_config.max_tokens:
                # Save current chunk if it has messages
                if current_messages:
                    chunk = self._create_chunk(fragment, current_messages, len(chunks))
                    chunks.append(chunk)
                    current_messages = []
                    current_tokens = 0
                
                # Split the large message
                split_messages = self._split_large_message(message, message_tokens)
                for split_msg in split_messages:
                    chunk = self._create_chunk(fragment, [split_msg], len(chunks))
                    chunks.append(chunk)
                continue
            
            # Check if adding this message would exceed limit
            if current_tokens + message_tokens > self.chunking_config.max_tokens and current_messages:
                # Save current chunk and start new one
                chunk = self._create_chunk(fragment, current_messages, len(chunks))
                chunks.append(chunk)
                current_messages = []
                current_tokens = 0
            
            # Add message to current chunk
            current_messages.append(message)
            current_tokens += message_tokens
        
        # Don't forget the last chunk
        if current_messages:
            chunk = self._create_chunk(fragment, current_messages, len(chunks))
            chunks.append(chunk)
        
        logger.info(f"Split into {len(chunks)} chunks")
        return chunks
    
    def _create_chunk(self, original: ChatFragment, messages: List[dict], chunk_index: int) -> ChatFragment:
        """Create a new ChatFragment chunk from messages."""
        chunk_id = f"{original.fragment_id}_chunk_{chunk_index:02d}" if original.fragment_id else str(uuid.uuid4())
        
        # Create title with chunk number
        base_title = original.title or "untitled conversation"
        chunk_title = f"{base_title}_{chunk_index + 1:02d}"
        
        chunk = ChatFragment(
            fragment_id=chunk_id,
            title=chunk_title,
            openai_conversation_id=original.openai_conversation_id,
            create_time=original.create_time,
            update_time=original.update_time,
            messages=messages.copy(),
            message_metadata=[]
        )
        
        # Copy relevant metadata for the messages in this chunk
        original_msg_count = len(original.messages)
        chunk_msg_count = len(messages)
        
        if len(original.message_metadata) >= chunk_msg_count:
            # Simple case: copy metadata for these messages
            start_idx = sum(1 for msg in original.messages[:original_msg_count - chunk_msg_count])
            chunk.message_metadata = original.message_metadata[start_idx:start_idx + chunk_msg_count]
        
        return chunk
    
    def _split_large_message(self, message: dict, token_count: int) -> List[dict]:
        """
        Split a single message that's too large into smaller parts.
        
        This is a fallback for when a single message exceeds the token limit.
        """
        content = message['content']
        role = message['role']
        
        # Estimate how many parts we need
        parts_needed = (token_count // self.chunking_config.max_tokens) + 1
        chars_per_part = len(content) // parts_needed
        
        parts = []
        start = 0
        
        for i in range(parts_needed):
            if i == parts_needed - 1:
                # Last part gets the remainder
                part_content = content[start:]
            else:
                # Try to split at a reasonable boundary (sentence, paragraph, etc.)
                end = start + chars_per_part
                
                # Look for good split points
                for boundary in ['\n\n', '. ', '\n', ' ']:
                    split_point = content.rfind(boundary, start, end + 100)
                    if split_point > start:
                        end = split_point + len(boundary)
                        break
                
                part_content = content[start:end]
                start = end
            
            if part_content.strip():  # Only add non-empty parts
                part_message = {
                    'role': role,
                    'content': part_content.strip()
                }
                parts.append(part_message)
        
        logger.info(f"Split large {role} message into {len(parts)} parts")
        return parts
    
    def _get_chunk_stats(self, chunks: List[ChatFragment]) -> dict:
        """Get statistics about the chunking results."""
        if not chunks:
            return {}
        
        token_counts = [self._count_fragment_tokens(chunk) for chunk in chunks]
        message_counts = [len(chunk.messages) for chunk in chunks]
        
        return {
            'total_chunks': len(chunks),
            'total_tokens': sum(token_counts),
            'total_messages': sum(message_counts),
            'avg_tokens_per_chunk': sum(token_counts) / len(chunks),
            'max_tokens_per_chunk': max(token_counts),
            'min_tokens_per_chunk': min(token_counts),
            'avg_messages_per_chunk': sum(message_counts) / len(chunks),
        }