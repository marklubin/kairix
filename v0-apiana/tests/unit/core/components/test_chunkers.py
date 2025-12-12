"""
Unit tests for chunking components.
"""

from unittest.mock import Mock, patch

from apiana.core.components import ConversationChunkerComponent
from apiana.types.chat_fragment import ChatFragment


class TestConversationChunkerComponent:
    """Test conversation chunker component."""

    def test_chunker_creation_default(self):
        """Test chunker creation with default config."""
        chunker = ConversationChunkerComponent()
        assert chunker.name == "conversation_chunker"
        assert chunker.config.get("max_tokens", 5000) == 5000

    def test_chunker_creation_custom_config(self):
        """Test chunker creation with custom config."""
        config = {
            "max_tokens": 3000,
            "model_name": "gpt-3.5-turbo",
            "preserve_message_boundaries": True,
        }
        chunker = ConversationChunkerComponent("custom_chunker", config)
        assert chunker.name == "custom_chunker"
        assert chunker.config == config

    def test_validate_input_valid_fragment(self):
        """Test input validation with valid ChatFragment."""
        chunker = ConversationChunkerComponent()

        fragment = ChatFragment(
            title="Test", messages=[{"role": "user", "content": "Hello"}]
        )

        errors = chunker.validate_input(fragment)
        assert errors == []

    def test_validate_input_valid_fragment_list(self):
        """Test input validation with valid list of ChatFragments."""
        chunker = ConversationChunkerComponent()

        fragments = [
            ChatFragment(title="Test 1", messages=[]),
            ChatFragment(title="Test 2", messages=[]),
        ]

        errors = chunker.validate_input(fragments)
        assert errors == []

    def test_validate_input_invalid_input(self):
        """Test input validation with invalid inputs."""
        chunker = ConversationChunkerComponent()

        # Invalid type
        errors = chunker.validate_input("not a fragment")
        assert "must be a ChatFragment" in errors[0]

        # List with invalid items
        errors = chunker.validate_input([ChatFragment(), "invalid", 123])
        assert "All items in list must be ChatFragment" in errors[0]

    def test_chunk_single_fragment_no_chunking_needed(self):
        """Test chunking when no chunking is needed."""
        chunker = ConversationChunkerComponent()
        
        # Mock the internal token counting to return small number
        chunker._count_fragment_tokens = Mock(return_value=100)

        fragment = ChatFragment(
            title="Test", messages=[{"role": "user", "content": "Hello"}]
        )

        result = chunker.chunk(fragment)

        assert result.success
        assert len(result.data) == 1
        assert result.metadata["input_fragments"] == 1
        assert result.metadata["output_chunks"] == 1
        assert result.metadata["fragments_unchanged"] == 1
        assert result.metadata["fragments_chunked"] == 0
        assert result.data[0] == fragment

    def test_chunk_single_fragment_with_chunking(self):
        """Test chunking when chunking is needed."""
        config = {"max_tokens": 50}  # Very low limit to force chunking
        chunker = ConversationChunkerComponent("test_chunker", config)
        
        # Mock token counting to force chunking
        chunker._count_fragment_tokens = Mock(return_value=200)  # Total is high
        chunker._count_tokens = Mock(return_value=30)  # Each message fits

        fragment = ChatFragment(
            title="Test",
            messages=[
                {"role": "user", "content": "First message"},
                {"role": "assistant", "content": "First response"},
                {"role": "user", "content": "Second message"},
                {"role": "assistant", "content": "Second response"},
            ],
        )

        result = chunker.chunk(fragment)

        assert result.success
        assert len(result.data) > 1  # Should be chunked
        assert result.metadata["input_fragments"] == 1
        assert result.metadata["fragments_chunked"] == 1
        assert result.metadata["fragments_unchanged"] == 0
        
        # Check chunk naming
        for i, chunk in enumerate(result.data):
            expected_title = f"Test_{i + 1:02d}"
            assert chunk.title == expected_title

    def test_chunk_multiple_fragments(self):
        """Test chunking multiple fragments."""
        config = {"max_tokens": 1000}  # Set reasonable limit
        chunker = ConversationChunkerComponent("test_chunker", config)
        
        # Use realistic chunking scenario with small vs large fragments
        fragments = [
            ChatFragment(title="small", messages=[{"role": "user", "content": "Hi"}]),
            ChatFragment(title="large", messages=[
                {"role": "user", "content": "This is a very long message that contains a lot of text. " * 20},
                {"role": "assistant", "content": "This is also a very long response that contains detailed information. " * 20},
                {"role": "user", "content": "Another very long follow-up message with lots of content. " * 20},
                {"role": "assistant", "content": "Final very long response with comprehensive details. " * 20},
            ]),
        ]

        result = chunker.chunk(fragments)

        assert result.success
        assert len(result.data) >= 2  # At least original fragments
        assert result.metadata["input_fragments"] == 2
        # The exact chunking behavior depends on token counting, so we'll check more flexibly
        assert result.metadata["fragments_unchanged"] + result.metadata["fragments_chunked"] == 2

    def test_chunk_execution_time_tracking(self):
        """Test that execution time is tracked."""
        chunker = ConversationChunkerComponent()

        fragment = ChatFragment(title="Test", messages=[])
        result = chunker.chunk(fragment)

        assert result.execution_time_ms >= 0
        assert isinstance(result.execution_time_ms, float)
    
    @patch("apiana.core.components.chunkers.conversation.HAS_TRANSFORMERS", False)
    def test_chunker_fallback_tokenization(self):
        """Test chunker with fallback tokenization."""
        chunker = ConversationChunkerComponent()
        
        # Should use fallback tokenization
        assert chunker.tokenizer is None
        
        fragment = ChatFragment(
            title="Test", 
            messages=[{"role": "user", "content": "Hello world!"}]
        )
        
        result = chunker.chunk(fragment)
        assert result.success
        assert len(result.data) == 1
    
    def test_token_counting_methods(self):
        """Test token counting functionality."""
        chunker = ConversationChunkerComponent()
        
        # Test basic token counting
        count = chunker._count_tokens("Hello world!")
        assert count > 0
        
        # Test fragment token counting
        fragment = ChatFragment(
            title="Test",
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"}
            ]
        )
        
        total_count = chunker._count_fragment_tokens(fragment)
        assert total_count > 0
        
    def test_chunk_stats_generation(self):
        """Test chunk statistics generation."""
        chunker = ConversationChunkerComponent()
        
        chunks = [
            ChatFragment(title="Chunk 1", messages=[{"role": "user", "content": "Hello"}]),
            ChatFragment(title="Chunk 2", messages=[
                {"role": "user", "content": "Hi"}, 
                {"role": "assistant", "content": "Hello"}
            ]),
        ]
        
        stats = chunker._get_chunk_stats(chunks)
        
        assert stats['total_chunks'] == 2
        assert 'total_tokens' in stats
        assert 'total_messages' in stats
        assert 'avg_tokens_per_chunk' in stats
