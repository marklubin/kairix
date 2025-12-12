"""
Unit tests for processor components.
"""

from unittest.mock import Mock, MagicMock

from apiana.core.components import (
    SummarizerTransform,
    EmbeddingTransform,
    ValidationTransform
)
from apiana.types.chat_fragment import ChatFragment


class TestSummarizerTransform:
    """Test summarizer processor component."""
    
    def test_summarizer_creation(self):
        """Test summarizer creation."""
        summarizer = SummarizerTransform()
        assert summarizer.name == "summarizer"
        assert summarizer.llm_provider is None
    
    def test_summarizer_with_custom_config(self):
        """Test summarizer with custom configuration."""
        config = {
            'system_prompt': 'Custom system prompt',
            'user_template': 'Custom template: {conversation}'
        }
        summarizer = SummarizerTransform("custom_summarizer", config)
        assert summarizer.name == "custom_summarizer"
        assert summarizer.config == config
    
    def test_validate_input_no_provider(self):
        """Test input validation when LLM provider not set."""
        summarizer = SummarizerTransform()
        
        fragment = ChatFragment(title="Test", messages=[])
        errors = summarizer.validate_input(fragment)
        
        assert "LLM provider not set" in errors[0]
    
    def test_validate_input_valid_fragment(self):
        """Test input validation with valid ChatFragment."""
        summarizer = SummarizerTransform()
        summarizer.set_llm_provider(Mock())
        
        fragment = ChatFragment(title="Test", messages=[])
        errors = summarizer.validate_input(fragment)
        
        assert errors == []
    
    def test_validate_input_valid_fragment_list(self):
        """Test input validation with valid list of ChatFragments."""
        summarizer = SummarizerTransform()
        summarizer.set_llm_provider(Mock())
        
        fragments = [
            ChatFragment(title="Test 1", messages=[]),
            ChatFragment(title="Test 2", messages=[])
        ]
        
        errors = summarizer.validate_input(fragments)
        assert errors == []
    
    def test_validate_input_invalid_input(self):
        """Test input validation with invalid inputs."""
        summarizer = SummarizerTransform()
        summarizer.set_llm_provider(Mock())
        
        # Invalid type
        errors = summarizer.validate_input("not a fragment")
        assert "must be a ChatFragment" in errors[0]
        
        # List with invalid items
        errors = summarizer.validate_input([ChatFragment(), "invalid"])
        assert "All items in list must be ChatFragment" in errors[0]
    
    def test_transform_single_fragment(self):
        """Test summarizing a single fragment."""
        # Mock LLM provider
        mock_provider = Mock()
        mock_response = Mock()
        mock_response.content = "This is a summary"
        mock_provider.invoke.return_value = mock_response
        
        summarizer = SummarizerTransform()
        summarizer.set_llm_provider(mock_provider)
        
        fragment = ChatFragment(
            fragment_id="test_123",
            title="Test Conversation",
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ]
        )
        
        result = summarizer.transform(fragment)
        
        assert result.success
        assert len(result.data) == 1
        assert result.data[0]['fragment_id'] == 'test_123'
        assert result.data[0]['title'] == 'Test Conversation'
        assert result.data[0]['summary'] == 'This is a summary'
        assert result.data[0]['original_messages'] == 2
        
        # Verify LLM was called
        mock_provider.invoke.assert_called_once()
    
    def test_transform_multiple_fragments(self):
        """Test summarizing multiple fragments."""
        # Mock LLM provider
        mock_provider = Mock()
        mock_response = Mock()
        mock_response.content = "Summary"
        mock_provider.invoke.return_value = mock_response
        
        summarizer = SummarizerTransform()
        summarizer.set_llm_provider(mock_provider)
        
        fragments = [
            ChatFragment(fragment_id="1", title="Conv 1", messages=[{"role": "user", "content": "Hi"}]),
            ChatFragment(fragment_id="2", title="Conv 2", messages=[{"role": "user", "content": "Hello"}])
        ]
        
        result = summarizer.transform(fragments)
        
        assert result.success
        assert len(result.data) == 2
        assert result.metadata['fragments_processed'] == 2
        assert result.metadata['summaries_generated'] == 2
        assert result.metadata['failures'] == 0
        
        # Verify LLM was called twice
        assert mock_provider.invoke.call_count == 2
    
    def test_transform_with_failure(self):
        """Test handling of summarization failures."""
        # Mock LLM provider that fails
        mock_provider = Mock()
        mock_provider.invoke.side_effect = Exception("LLM error")
        
        summarizer = SummarizerTransform()
        summarizer.set_llm_provider(mock_provider)
        
        fragment = ChatFragment(fragment_id="test", title="Test", messages=[])
        
        result = summarizer.transform(fragment)
        
        # ComponentResult considers having errors as failure
        assert not result.success
        assert len(result.errors) == 1
        assert "Failed to summarize fragment 0" in result.errors[0]
        assert result.data[0]['summary'] is None
        assert 'error' in result.data[0]
        assert result.metadata['failures'] == 1


class TestEmbeddingTransform:
    """Test embedding processor component."""
    
    def test_embedder_creation(self):
        """Test embedder creation."""
        embedder = EmbeddingTransform()
        assert embedder.name == "embedder"
        assert embedder.embedding_provider is None
    
    def test_validate_input_no_provider(self):
        """Test input validation when embedding provider not set."""
        embedder = EmbeddingTransform()
        
        summaries = [{'summary': 'test'}]
        errors = embedder.validate_input(summaries)
        
        assert "Embedding provider not set" in errors[0]
    
    def test_validate_input_valid_summaries(self):
        """Test input validation with valid summaries."""
        embedder = EmbeddingTransform()
        embedder.set_embedding_provider(Mock())
        
        summaries = [
            {'summary': 'Summary 1'},
            {'summary': 'Summary 2'}
        ]
        
        errors = embedder.validate_input(summaries)
        assert errors == []
    
    def test_validate_input_invalid_input(self):
        """Test input validation with invalid inputs."""
        embedder = EmbeddingTransform()
        embedder.set_embedding_provider(Mock())
        
        # Not a list
        errors = embedder.validate_input("not a list")
        assert "must be a list" in errors[0]
        
        # List with invalid items
        errors = embedder.validate_input([{'summary': 'ok'}, "invalid", {'no_summary': True}])
        assert len(errors) == 2
        assert "must be a dictionary" in errors[0]
        assert "missing valid summary" in errors[1]
    
    def test_transform_success(self):
        """Test successful embedding generation."""
        # Mock embedding provider
        mock_provider = Mock()
        mock_provider.embed_query.return_value = [0.1, 0.2, 0.3]
        
        embedder = EmbeddingTransform()
        embedder.set_embedding_provider(mock_provider)
        
        summaries = [
            {'fragment_id': '1', 'title': 'Test 1', 'summary': 'Summary 1'},
            {'fragment_id': '2', 'title': 'Test 2', 'summary': 'Summary 2'}
        ]
        
        result = embedder.transform(summaries)
        
        assert result.success
        assert len(result.data) == 2
        assert result.data[0]['embedding'] == [0.1, 0.2, 0.3]
        assert result.data[0]['embedding_dim'] == 3
        assert result.metadata['items_processed'] == 2
        assert result.metadata['embeddings_generated'] == 2
        assert result.metadata['failures'] == 0
        
        assert mock_provider.embed_query.call_count == 2
    
    def test_transform_skip_missing_summaries(self):
        """Test that items without summaries are skipped."""
        mock_provider = Mock()
        mock_provider.embed_query.return_value = [0.1, 0.2]
        
        embedder = EmbeddingTransform()
        embedder.set_embedding_provider(mock_provider)
        
        summaries = [
            {'summary': 'Valid summary'},
            {'summary': None},  # Should be skipped
            {'summary': 'Another valid'}
        ]
        
        result = embedder.transform(summaries)
        
        assert result.success
        assert len(result.data) == 2  # Only 2 with embeddings
        assert mock_provider.embed_query.call_count == 2
    
    def test_transform_with_failure(self):
        """Test handling of embedding failures."""
        mock_provider = Mock()
        mock_provider.embed_query.side_effect = Exception("Embedding error")
        
        embedder = EmbeddingTransform()
        embedder.set_embedding_provider(mock_provider)
        
        summaries = [{'summary': 'Test summary'}]
        
        result = embedder.transform(summaries)
        
        # ComponentResult considers having errors as failure
        assert not result.success
        assert len(result.errors) == 1
        assert "Failed to generate embedding" in result.errors[0]
        assert result.data[0]['embedding'] is None
        assert result.metadata['failures'] == 1


class TestValidationTransform:
    """Test validation processor component."""
    
    def test_validator_creation(self):
        """Test validator creation."""
        validator = ValidationTransform()
        assert validator.name == "validator"
    
    def test_validator_with_config(self):
        """Test validator with custom configuration."""
        config = {
            'min_messages': 2,
            'max_messages': 100,
            'require_title': True
        }
        validator = ValidationTransform("custom_validator", config)
        assert validator.config == config
    
    def test_validate_input_valid(self):
        """Test input validation."""
        validator = ValidationTransform()
        
        # Valid single fragment
        fragment = ChatFragment(title="Test", messages=[])
        errors = validator.validate_input(fragment)
        assert errors == []
        
        # Valid list
        fragments = [ChatFragment(), ChatFragment()]
        errors = validator.validate_input(fragments)
        assert errors == []
    
    def test_validate_input_invalid(self):
        """Test input validation with invalid inputs."""
        validator = ValidationTransform()
        
        # Invalid type
        errors = validator.validate_input("not a fragment")
        assert "must be a ChatFragment" in errors[0]
        
        # List with invalid items
        errors = validator.validate_input([ChatFragment(), "invalid"])
        assert "All items in list must be ChatFragment" in errors[0]
    
    def test_transform_all_valid(self):
        """Test transform with all valid fragments."""
        validator = ValidationTransform()
        
        fragments = [
            ChatFragment(title="Test 1", messages=[{"role": "user", "content": "Hello"}]),
            ChatFragment(title="Test 2", messages=[{"role": "user", "content": "Hi"}])
        ]
        
        result = validator.transform(fragments)
        
        assert result.success
        assert len(result.data) == 2
        assert result.metadata['input_fragments'] == 2
        assert result.metadata['valid_fragments'] == 2
        assert result.metadata['filtered_out'] == 0
        assert len(result.warnings) == 0
    
    def test_transform_with_filtering(self):
        """Test transform with filtering based on config."""
        config = {
            'min_messages': 2,
            'require_title': True
        }
        validator = ValidationTransform(config=config)
        
        fragments = [
            ChatFragment(title="Valid", messages=[{"role": "user", "content": "1"}, {"role": "assistant", "content": "2"}]),
            ChatFragment(title="", messages=[{"role": "user", "content": "Hello"}]),  # No title
            ChatFragment(title="Too few", messages=[{"role": "user", "content": "Hi"}])  # Too few messages
        ]
        
        result = validator.transform(fragments)
        
        assert result.success
        assert len(result.data) == 1  # Only first fragment is valid
        assert result.metadata['input_fragments'] == 3
        assert result.metadata['valid_fragments'] == 1
        assert result.metadata['filtered_out'] == 2
        assert len(result.warnings) == 2
    
    def test_transform_empty_message_detection(self):
        """Test detection of empty messages."""
        validator = ValidationTransform()
        
        fragment = ChatFragment(
            title="Test",
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": ""},  # Empty
                {"role": "user", "content": "   "}  # Whitespace only
            ]
        )
        
        result = validator.transform(fragment)
        
        assert result.success
        assert len(result.data) == 0  # Fragment filtered out
        assert len(result.warnings) == 1
        assert "2 empty messages" in result.warnings[0]
    
    def test_transform_max_messages(self):
        """Test filtering based on max_messages."""
        config = {'max_messages': 2}
        validator = ValidationTransform(config=config)
        
        fragments = [
            ChatFragment(title="Ok", messages=[{"content": "1"}, {"content": "2"}]),
            ChatFragment(title="Too many", messages=[{"content": "1"}, {"content": "2"}, {"content": "3"}])
        ]
        
        result = validator.transform(fragments)
        
        assert len(result.data) == 1
        assert "Too many messages: 3 > 2" in result.warnings[0]