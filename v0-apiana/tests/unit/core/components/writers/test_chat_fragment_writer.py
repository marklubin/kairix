"""
Unit tests for ChatFragmentWriter component.
"""

from datetime import datetime
from unittest.mock import Mock, patch
import pytest

from apiana.core.components.writers.chat_fragment_writer import ChatFragmentWriter
from apiana.types.chat_fragment import ChatFragment
from apiana.types.configuration import Neo4jConfig


@pytest.fixture
def mock_store():
    """Create a mock ApplicationStore."""
    return Mock()


@pytest.fixture
def sample_fragment():
    """Create a sample ChatFragment for testing."""
    return ChatFragment(
        title="Test Conversation",
        messages=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ],
        fragment_id="test-123",
        openai_conversation_id="conv-456",
        create_time=datetime(2024, 1, 15, 10, 0, 0),
        update_time=datetime(2024, 1, 15, 10, 5, 0),
    )


@pytest.fixture
def sample_fragment_list(sample_fragment):
    """Create a list of ChatFragments for testing."""
    fragment2 = ChatFragment(
        title="Another Conversation",
        messages=[{"role": "user", "content": "Test"}],
        fragment_id="test-456",
        openai_conversation_id="conv-789",
    )
    return [sample_fragment, fragment2]


class TestChatFragmentWriter:
    """Unit tests for ChatFragmentWriter."""

    def test_init_with_store(self, mock_store):
        """Should initialize with store and default tags."""
        writer = ChatFragmentWriter(store=mock_store)
        
        assert writer.store == mock_store
        assert writer.tags == []

    def test_init_with_tags(self, mock_store):
        """Should initialize with custom tags."""
        tags = ["important", "processed"]
        writer = ChatFragmentWriter(store=mock_store, tags=tags)
        
        assert writer.store == mock_store
        assert writer.tags == tags

    @patch('apiana.core.components.writers.chat_fragment_writer.ApplicationStore')
    def test_from_config(self, mock_store_class):
        """Should create writer from Neo4j configuration."""
        config = Neo4jConfig(
            username="test", password="test", host="localhost", port=7687
        )
        tags = ["test"]
        mock_store = Mock()
        mock_store_class.return_value = mock_store

        writer = ChatFragmentWriter.from_config(config, tags=tags)

        mock_store_class.assert_called_once_with(config)
        assert writer.store == mock_store
        assert writer.tags == tags

    def test_validate_input_single_fragment(self, mock_store, sample_fragment):
        """Should validate single ChatFragment input."""
        writer = ChatFragmentWriter(store=mock_store)
        
        result = writer.validate_input(sample_fragment)
        
        assert result.success
        assert not result.errors

    def test_validate_input_fragment_list(self, mock_store, sample_fragment_list):
        """Should validate list of ChatFragments."""
        writer = ChatFragmentWriter(store=mock_store)
        
        result = writer.validate_input(sample_fragment_list)
        
        assert result.success
        assert not result.errors

    def test_validate_input_empty_list(self, mock_store):
        """Should handle empty list with warning."""
        writer = ChatFragmentWriter(store=mock_store)
        
        result = writer.validate_input([])
        
        assert result.success
        assert len(result.warnings) == 1
        assert "Empty list" in result.warnings[0]

    def test_validate_input_invalid_type(self, mock_store):
        """Should reject invalid input types."""
        writer = ChatFragmentWriter(store=mock_store)
        
        result = writer.validate_input("invalid")
        
        assert not result.success
        assert len(result.errors) == 1
        assert "ChatFragment or List[ChatFragment]" in result.errors[0]

    def test_validate_input_mixed_list(self, mock_store, sample_fragment):
        """Should reject list with non-ChatFragment items."""
        writer = ChatFragmentWriter(store=mock_store)
        
        result = writer.validate_input([sample_fragment, "invalid"])
        
        assert not result.success
        assert len(result.errors) == 1
        assert "All items in list must be ChatFragment" in result.errors[0]

    def test_process_single_fragment_success(self, mock_store, sample_fragment):
        """Should process and store single ChatFragment successfully."""
        mock_store.store_fragment.return_value = Mock()
        writer = ChatFragmentWriter(store=mock_store, tags=["test"])
        
        result = writer.process(sample_fragment)
        
        assert result.success
        assert result.data == sample_fragment
        mock_store.store_fragment.assert_called_once_with(sample_fragment, tags=["test"])
        
        # Check metadata
        assert result.metadata["fragments_stored"] == 1
        assert result.metadata["fragments_failed"] == 0
        assert result.metadata["total_fragments"] == 1
        assert result.metadata["tags_applied"] == ["test"]
        assert result.metadata["entity_type"] == "chat_fragment"

    def test_process_fragment_list_success(self, mock_store, sample_fragment_list):
        """Should process and store list of ChatFragments successfully."""
        mock_store.store_fragment.return_value = Mock()
        writer = ChatFragmentWriter(store=mock_store)
        
        result = writer.process(sample_fragment_list)
        
        assert result.success
        assert result.data == sample_fragment_list
        assert mock_store.store_fragment.call_count == 2
        
        # Check metadata
        assert result.metadata["fragments_stored"] == 2
        assert result.metadata["fragments_failed"] == 0
        assert result.metadata["total_fragments"] == 2

    def test_process_empty_list(self, mock_store):
        """Should handle empty list gracefully."""
        writer = ChatFragmentWriter(store=mock_store)
        
        result = writer.process([])
        
        assert result.success
        assert result.data == []
        mock_store.store_fragment.assert_not_called()

    def test_process_storage_failure(self, mock_store, sample_fragment_list):
        """Should handle storage failures gracefully."""
        # First fragment succeeds, second fails
        mock_store.store_fragment.side_effect = [Mock(), Exception("Storage error")]
        writer = ChatFragmentWriter(store=mock_store)
        
        result = writer.process(sample_fragment_list)
        
        assert result.success  # Still successful despite partial failure
        assert result.data == sample_fragment_list  # Data passed through
        assert len(result.warnings) == 1
        assert "Storage error" in result.warnings[0]
        
        # Check metadata
        assert result.metadata["fragments_stored"] == 1
        assert result.metadata["fragments_failed"] == 1
        assert result.metadata["total_fragments"] == 2

    def test_process_validation_failure(self, mock_store):
        """Should handle validation failures."""
        writer = ChatFragmentWriter(store=mock_store)
        
        result = writer.process("invalid")
        
        assert not result.success
        assert len(result.errors) == 1
        mock_store.store_fragment.assert_not_called()

    def test_process_complete_failure(self, mock_store, sample_fragment):
        """Should handle complete processing failures gracefully."""
        mock_store.store_fragment.side_effect = Exception("Complete failure")
        writer = ChatFragmentWriter(store=mock_store)
        
        result = writer.process(sample_fragment)
        
        assert result.success  # Still passes through data
        assert result.data == sample_fragment
        assert len(result.warnings) == 1
        assert "Complete failure" in result.warnings[0]

    def test_write_method(self, mock_store, sample_fragment):
        """Should support Writer interface write method."""
        mock_store.store_fragment.return_value = Mock()
        writer = ChatFragmentWriter(store=mock_store)
        
        result = writer.write(sample_fragment, destination="ignored")
        
        assert result.success
        assert result.data == sample_fragment
        mock_store.store_fragment.assert_called_once()

    def test_type_specifications(self, mock_store):
        """Should have correct input/output type specifications."""
        writer = ChatFragmentWriter(store=mock_store)
        
        # Check for the actual types defined
        from typing import List
        assert ChatFragment in writer.input_types
        assert List[ChatFragment] in writer.input_types
        assert ChatFragment in writer.output_types
        assert List[ChatFragment] in writer.output_types