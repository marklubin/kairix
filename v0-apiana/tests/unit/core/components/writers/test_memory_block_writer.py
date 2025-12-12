"""
Unit tests for MemoryBlockWriter component.
"""

from datetime import datetime
from unittest.mock import Mock, patch
import pytest

from apiana.core.components.writers.memory_block_writer import MemoryBlockWriter
from apiana.types.chat_fragment import ChatFragment
from apiana.types.configuration import Neo4jConfig


@pytest.fixture
def mock_store():
    """Create a mock AgentMemoryStore."""
    store = Mock()
    store.get_database_name.return_value = "agent_test"
    return store


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
    )


@pytest.fixture
def sample_memory_item(sample_fragment):
    """Create a sample memory item for testing."""
    return {
        "summary": "A friendly greeting conversation",
        "embedding": [0.1, 0.2, 0.3, 0.4, 0.5],
        "fragment": sample_fragment
    }


@pytest.fixture
def sample_memory_list(sample_memory_item, sample_fragment):
    """Create a list of memory items for testing."""
    fragment2 = ChatFragment(
        title="Another Conversation",
        messages=[{"role": "user", "content": "Test"}],
        fragment_id="test-456",
    )
    
    memory2 = {
        "summary": "A test conversation",
        "embedding": [0.5, 0.4, 0.3, 0.2, 0.1],
        "fragment": fragment2
    }
    
    return [sample_memory_item, memory2]


class TestMemoryBlockWriter:
    """Unit tests for MemoryBlockWriter."""

    def test_init_with_defaults(self, mock_store):
        """Should initialize with default values."""
        writer = MemoryBlockWriter(
            store=mock_store,
            agent_id="test-agent"
        )
        
        assert writer.store == mock_store
        assert writer.agent_id == "test-agent"
        assert writer.tags == ["memory", "conversation", "experience"]

    def test_init_with_custom_tags(self, mock_store):
        """Should initialize with custom tags."""
        tags = ["custom", "important"]
        writer = MemoryBlockWriter(
            store=mock_store,
            agent_id="test-agent",
            tags=tags
        )
        
        assert writer.tags == tags

    @patch('apiana.core.components.writers.memory_block_writer.AgentMemoryStore')
    def test_from_config(self, mock_store_class):
        """Should create writer from Neo4j configuration."""
        config = Neo4jConfig(
            username="test", password="test", host="localhost", port=7687
        )
        tags = ["test"]
        mock_store = Mock()
        mock_store_class.return_value = mock_store

        writer = MemoryBlockWriter.from_config(
            config, 
            agent_id="test-agent",
            tags=tags
        )

        mock_store_class.assert_called_once_with(config, "test-agent")
        assert writer.store == mock_store
        assert writer.agent_id == "test-agent"
        assert writer.tags == tags

    def test_validate_input_single_memory(self, mock_store, sample_memory_item):
        """Should validate single memory item input."""
        writer = MemoryBlockWriter(store=mock_store, agent_id="test")
        
        result = writer.validate_input(sample_memory_item)
        
        assert result.success
        assert not result.errors

    def test_validate_input_memory_list(self, mock_store, sample_memory_list):
        """Should validate list of memory items."""
        writer = MemoryBlockWriter(store=mock_store, agent_id="test")
        
        result = writer.validate_input(sample_memory_list)
        
        assert result.success
        assert not result.errors

    def test_validate_input_empty_list(self, mock_store):
        """Should handle empty list with warning."""
        writer = MemoryBlockWriter(store=mock_store, agent_id="test")
        
        result = writer.validate_input([])
        
        assert result.success
        assert len(result.warnings) == 1
        assert "Empty list" in result.warnings[0]

    def test_validate_input_invalid_type(self, mock_store):
        """Should reject invalid input types."""
        writer = MemoryBlockWriter(store=mock_store, agent_id="test")
        
        result = writer.validate_input("invalid")
        
        assert not result.success
        assert len(result.errors) == 1
        assert "dict or List[dict]" in result.errors[0]

    def test_validate_input_missing_keys(self, mock_store):
        """Should reject memory items missing required keys."""
        writer = MemoryBlockWriter(store=mock_store, agent_id="test")
        
        result = writer.validate_input({"summary": "test"})  # Missing embedding and fragment
        
        assert not result.success
        assert len(result.errors) == 1
        assert "summary', 'embedding', and 'fragment'" in result.errors[0]

    def test_validate_input_mixed_list(self, mock_store, sample_memory_item):
        """Should reject list with invalid items."""
        writer = MemoryBlockWriter(store=mock_store, agent_id="test")
        
        result = writer.validate_input([sample_memory_item, "invalid"])
        
        assert not result.success
        assert "must be a dictionary" in result.errors[0]

    def test_is_valid_memory_dict(self, mock_store, sample_memory_item):
        """Should correctly identify valid memory dictionaries."""
        writer = MemoryBlockWriter(store=mock_store, agent_id="test")
        
        # Valid item
        assert writer._is_valid_memory_dict(sample_memory_item)
        
        # Invalid items
        assert not writer._is_valid_memory_dict({"summary": "test"})
        assert not writer._is_valid_memory_dict({})

    def test_validate_memory_item_valid(self, mock_store, sample_memory_item):
        """Should validate a correct memory item."""
        writer = MemoryBlockWriter(store=mock_store, agent_id="test")
        
        errors = writer._validate_memory_item(sample_memory_item)
        
        assert errors == []

    def test_validate_memory_item_invalid_fragment(self, mock_store):
        """Should detect invalid fragment type."""
        writer = MemoryBlockWriter(store=mock_store, agent_id="test")
        
        item = {
            "summary": "test",
            "embedding": [0.1, 0.2],
            "fragment": "not a fragment"
        }
        
        errors = writer._validate_memory_item(item)
        
        assert len(errors) > 0
        assert any("Fragment must be ChatFragment" in error for error in errors)

    def test_validate_memory_item_invalid_summary(self, mock_store, sample_fragment):
        """Should detect invalid summary."""
        writer = MemoryBlockWriter(store=mock_store, agent_id="test")
        
        # Non-string summary
        item = {
            "summary": 123,
            "embedding": [0.1, 0.2],
            "fragment": sample_fragment
        }
        
        errors = writer._validate_memory_item(item)
        assert any("Summary must be string" in error for error in errors)
        
        # Empty summary
        item["summary"] = ""
        errors = writer._validate_memory_item(item)
        assert any("Summary cannot be empty" in error for error in errors)

    def test_validate_memory_item_invalid_embedding(self, mock_store, sample_fragment):
        """Should detect invalid embedding."""
        writer = MemoryBlockWriter(store=mock_store, agent_id="test")
        
        # Non-list embedding
        item = {
            "summary": "test",
            "embedding": "not a list",
            "fragment": sample_fragment
        }
        
        errors = writer._validate_memory_item(item)
        assert any("Embedding must be list" in error for error in errors)
        
        # Empty embedding
        item["embedding"] = []
        errors = writer._validate_memory_item(item)
        assert any("Embedding cannot be empty" in error for error in errors)
        
        # Non-numeric embedding
        item["embedding"] = ["not", "numbers"]
        errors = writer._validate_memory_item(item)
        assert any("list of numbers" in error for error in errors)

    def test_process_single_memory_success(self, mock_store, sample_memory_item):
        """Should process and store single memory item successfully."""
        mock_memory_block = Mock()
        mock_store.store_fragment.return_value = mock_memory_block
        writer = MemoryBlockWriter(store=mock_store, agent_id="test-agent", tags=["test"])
        
        result = writer.process(sample_memory_item)
        
        assert result.success
        assert result.data == sample_memory_item
        
        mock_store.store_fragment.assert_called_once_with(
            fragment=sample_memory_item["fragment"],
            summary=sample_memory_item["summary"],
            embeddings=sample_memory_item["embedding"],
            tags=["test"]
        )
        
        # Check metadata
        assert result.metadata["memories_stored"] == 1
        assert result.metadata["memories_failed"] == 0
        assert result.metadata["total_memories"] == 1
        assert result.metadata["agent_id"] == "test-agent"
        assert result.metadata["entity_type"] == "memory_block"

    def test_process_memory_list_success(self, mock_store, sample_memory_list):
        """Should process and store list of memory items successfully."""
        mock_memory_block = Mock()
        mock_store.store_fragment.return_value = mock_memory_block
        writer = MemoryBlockWriter(store=mock_store, agent_id="test-agent")
        
        result = writer.process(sample_memory_list)
        
        assert result.success
        assert result.data == sample_memory_list
        assert mock_store.store_fragment.call_count == 2
        
        # Check metadata
        assert result.metadata["memories_stored"] == 2
        assert result.metadata["memories_failed"] == 0
        assert result.metadata["total_memories"] == 2

    def test_process_empty_list(self, mock_store):
        """Should handle empty list gracefully."""
        writer = MemoryBlockWriter(store=mock_store, agent_id="test")
        
        result = writer.process([])
        
        assert result.success
        assert result.data == []
        mock_store.store_fragment.assert_not_called()

    def test_process_validation_errors(self, mock_store, sample_fragment):
        """Should handle validation errors gracefully."""
        # Invalid fragment type
        invalid_item = {
            "summary": "test",
            "embedding": [0.1, 0.2],
            "fragment": "not a fragment"
        }
        
        writer = MemoryBlockWriter(store=mock_store, agent_id="test")
        
        result = writer.process([invalid_item])
        
        assert result.success  # Still passes through data
        assert result.data == [invalid_item]
        assert len(result.warnings) > 0
        assert "Fragment must be ChatFragment" in str(result.warnings)
        
        # Check metadata shows failure
        assert result.metadata["memories_stored"] == 0
        assert result.metadata["memories_failed"] == 1

    def test_process_storage_failure(self, mock_store, sample_memory_list):
        """Should handle storage failures gracefully."""
        # First memory succeeds, second fails
        mock_store.store_fragment.side_effect = [Mock(), Exception("Storage error")]
        writer = MemoryBlockWriter(store=mock_store, agent_id="test")
        
        result = writer.process(sample_memory_list)
        
        assert result.success  # Still successful despite partial failure
        assert result.data == sample_memory_list  # Data passed through
        assert len(result.warnings) == 1
        assert "Storage error" in result.warnings[0]
        
        # Check metadata
        assert result.metadata["memories_stored"] == 1
        assert result.metadata["memories_failed"] == 1

    def test_process_validation_failure(self, mock_store):
        """Should handle input validation failures."""
        writer = MemoryBlockWriter(store=mock_store, agent_id="test")
        
        result = writer.process("invalid")
        
        assert not result.success
        assert len(result.errors) == 1
        mock_store.store_fragment.assert_not_called()

    def test_process_complete_failure(self, mock_store, sample_memory_item):
        """Should handle complete processing failures gracefully."""
        mock_store.store_fragment.side_effect = Exception("Complete failure")
        writer = MemoryBlockWriter(store=mock_store, agent_id="test")
        
        result = writer.process(sample_memory_item)
        
        assert result.success  # Still passes through data
        assert result.data == sample_memory_item
        assert len(result.warnings) == 1
        assert "Complete failure" in result.warnings[0]

    def test_write_method(self, mock_store, sample_memory_item):
        """Should support Writer interface write method."""
        mock_store.store_fragment.return_value = Mock()
        writer = MemoryBlockWriter(store=mock_store, agent_id="test")
        
        result = writer.write(sample_memory_item, destination="different-agent")
        
        assert result.success
        assert result.data == sample_memory_item
        mock_store.store_fragment.assert_called_once()

    def test_write_method_different_destination_warning(self, mock_store, sample_memory_item):
        """Should warn when destination differs from configured agent_id."""
        mock_store.store_fragment.return_value = Mock()
        writer = MemoryBlockWriter(store=mock_store, agent_id="test-agent")
        
        with patch.object(writer, 'logger') as mock_logger:
            result = writer.write(sample_memory_item, destination="different-agent")
            
            mock_logger.warning.assert_called_once()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "different-agent" in warning_call
            assert "test-agent" in warning_call

    def test_type_specifications(self, mock_store):
        """Should have correct input/output type specifications."""
        writer = MemoryBlockWriter(store=mock_store, agent_id="test")
        
        # Check for the actual types defined
        from typing import List
        assert dict in writer.input_types
        assert List[dict] in writer.input_types
        assert dict in writer.output_types
        assert List[dict] in writer.output_types