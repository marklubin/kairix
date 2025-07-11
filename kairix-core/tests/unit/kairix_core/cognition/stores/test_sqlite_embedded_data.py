"""Tests for SQLite-based embedded data store."""
import numpy as np
import pytest
from unittest.mock import Mock, MagicMock, patch

from kairix_core.cognition.stores.sqlite_embedded_data import SQLiteEmbeddedDataStore


class TestSQLiteEmbeddedDataStore:
    """Test suite for SQLiteEmbeddedDataStore."""

    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage runtime."""
        storage = Mock()
        storage.vector_dao = Mock()
        return storage

    @pytest.fixture
    def mock_embedding_model(self):
        """Create a mock embedding model."""
        model = Mock()
        # Return 2D array (as Nomic does) to test flattening
        model.encode.return_value = np.array([[0.1, 0.2, 0.3, 0.4, 0.5]])
        model.embedding_dim = 5
        return model

    def test_get_embedding_flattens_2d_array(self, mock_storage, mock_embedding_model):
        """Test that _get_embedding properly flattens 2D arrays from embedding model."""
        store = SQLiteEmbeddedDataStore(
            table_name='memory_shard',
            content_key='contents',
            embedding_model=mock_embedding_model,
            storage=mock_storage
        )
        
        result = store._get_embedding("test query")
        
        # Should return a flat list
        assert result == [0.1, 0.2, 0.3, 0.4, 0.5]
        assert isinstance(result, list)
        mock_embedding_model.encode.assert_called_once_with("test query")

    def test_get_embedding_handles_1d_array(self, mock_storage):
        """Test that _get_embedding handles 1D arrays correctly."""
        model = Mock()
        # Return 1D array
        model.encode.return_value = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        
        store = SQLiteEmbeddedDataStore(
            table_name='memory_shard',
            content_key='contents',
            embedding_model=model,
            storage=mock_storage
        )
        
        result = store._get_embedding("test query")
        
        # Should return a flat list
        assert result == [0.1, 0.2, 0.3, 0.4, 0.5]
        assert isinstance(result, list)

    def test_search_memory_shards(self, mock_storage, mock_embedding_model):
        """Test searching memory shards with proper vector format."""
        # Mock vector search results
        mock_storage.vector_dao.search_similar_memories.return_value = [
            (1, 0.1),  # (id, distance)
            (2, 0.2)
        ]
        
        # Mock session and DAO
        mock_session = MagicMock()
        mock_storage.session.return_value.__enter__.return_value = mock_session
        
        mock_dao = Mock()
        mock_shard1 = Mock(contents="Memory content 1")
        mock_shard2 = Mock(contents="Memory content 2")
        mock_dao.get_by_id.side_effect = [mock_shard1, mock_shard2]
        mock_storage.get_dao.return_value = mock_dao
        
        store = SQLiteEmbeddedDataStore(
            table_name='memory_shard',
            content_key='contents',
            embedding_model=mock_embedding_model,
            storage=mock_storage
        )
        
        results = list(store.search("test query", k=2, agent_id=123))
        
        # Verify results
        assert len(results) == 2
        assert results[0][0] == "Memory content 1"
        assert results[1][0] == "Memory content 2"
        
        # Verify vector search was called with flat array
        mock_storage.vector_dao.search_similar_memories.assert_called_once_with(
            [0.1, 0.2, 0.3, 0.4, 0.5],  # Flattened array
            limit=2,
            agent_id=123
        )

    def test_search_entities(self, mock_storage, mock_embedding_model):
        """Test searching entities with proper vector format."""
        # Mock vector search results
        mock_storage.vector_dao.search_similar_entities.return_value = [
            (10, 0.15)  # (id, distance)
        ]
        
        # Mock session and DAO
        mock_session = MagicMock()
        mock_storage.session.return_value.__enter__.return_value = mock_session
        
        mock_dao = Mock()
        mock_entity = Mock(semantic_id="concept_123")
        mock_dao.get_by_id.return_value = mock_entity
        mock_storage.get_dao.return_value = mock_dao
        
        store = SQLiteEmbeddedDataStore(
            table_name='entity',
            content_key='semantic_id',
            embedding_model=mock_embedding_model,
            storage=mock_storage
        )
        
        results = list(store.search("test concept", k=1))
        
        # Verify results
        assert len(results) == 1
        assert results[0][0] == "concept_123"
        
        # Verify vector search was called with flat array
        mock_storage.vector_dao.search_similar_entities.assert_called_once_with(
            [0.1, 0.2, 0.3, 0.4, 0.5],  # Flattened array
            limit=1
        )

    def test_search_handles_invalid_k_value(self, mock_storage, mock_embedding_model):
        """Test that search handles invalid k values gracefully."""
        mock_storage.vector_dao.search_similar_memories.return_value = []
        mock_session = MagicMock()
        mock_storage.session.return_value.__enter__.return_value = mock_session
        
        store = SQLiteEmbeddedDataStore(
            table_name='memory_shard',
            content_key='contents',
            embedding_model=mock_embedding_model,
            storage=mock_storage
        )
        
        # Should not crash with k=0 or negative k
        list(store.search("test", k=0))
        list(store.search("test", k=-5))
        
        # Should use k=1 for invalid values
        assert mock_storage.vector_dao.search_similar_memories.call_count == 2
        for call in mock_storage.vector_dao.search_similar_memories.call_args_list:
            assert call[1]['limit'] == 1

    def test_content_transform(self, mock_storage, mock_embedding_model):
        """Test that content transformation is applied correctly."""
        # Mock vector search results
        mock_storage.vector_dao.search_similar_memories.return_value = [(1, 0.1)]
        
        # Mock session and DAO
        mock_session = MagicMock()
        mock_storage.session.return_value.__enter__.return_value = mock_session
        
        mock_dao = Mock()
        mock_shard = Mock(contents="UPPERCASE CONTENT")
        mock_dao.get_by_id.return_value = mock_shard
        mock_storage.get_dao.return_value = mock_dao
        
        # Create store with content transform
        store = SQLiteEmbeddedDataStore(
            table_name='memory_shard',
            content_key='contents',
            embedding_model=mock_embedding_model,
            storage=mock_storage,
            content_transform=lambda x: x.lower()
        )
        
        results = list(store.search("test", k=1))
        
        assert len(results) == 1
        assert results[0][0] == "uppercase content"  # Transformed

    def test_add_item_with_embedding(self, mock_storage, mock_embedding_model):
        """Test adding items with embeddings."""
        store = SQLiteEmbeddedDataStore(
            table_name='memory_shard',
            content_key='contents',
            embedding_model=mock_embedding_model,
            storage=mock_storage
        )
        
        # Test with pre-computed embedding
        store.add_item_with_embedding(123, "test content", embedding=[1.0, 2.0, 3.0])
        mock_storage.vector_dao.add_memory_embedding.assert_called_once_with(123, [1.0, 2.0, 3.0])
        
        # Test without pre-computed embedding (should generate)
        store.add_item_with_embedding(456, "test content 2")
        mock_storage.vector_dao.add_memory_embedding.assert_called_with(456, [0.1, 0.2, 0.3, 0.4, 0.5])

    def test_factory_functions(self):
        """Test the factory functions create stores with correct settings."""
        with patch('kairix_core.cognition.stores.sqlite_embedded_data.StorageRuntime') as mock_storage_class:
            mock_storage = Mock()
            mock_storage_class.return_value = mock_storage
            
            # Test memory shard store
            from kairix_core.cognition.stores.sqlite_embedded_data import create_memory_shard_store
            shard_store = create_memory_shard_store()
            assert shard_store.table_name == 'memory_shard'
            assert shard_store.content_key == 'contents'
            
            # Test concept store
            from kairix_core.cognition.stores.sqlite_embedded_data import create_concept_store
            concept_store = create_concept_store()
            assert concept_store.table_name == 'entity'
            assert concept_store.content_key == 'semantic_id'