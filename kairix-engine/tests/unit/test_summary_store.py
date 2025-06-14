import unittest
from unittest.mock import MagicMock, Mock, patch

import pytest

from kairix_engine.summary_store import (
    DEFAULT_EMBEDDING_MODEL,
    DefaultStoreDB,
    StoreDB,
    SummaryStore,
)


class MockStoreDB(StoreDB):
    """Mock implementation of StoreDB for testing"""

    def __init__(self):
        self.configured_url = None
        self.cypher_query_mock = Mock()

    def configure(self, url):
        self.configured_url = url

    def cypher_query(self, query, params):
        return self.cypher_query_mock(query, params)


class TestDefaultStoreDB(unittest.TestCase):
    """Test cases for DefaultStoreDB class"""

    @patch("kairix_engine.summary_store.db")
    @patch("kairix_engine.summary_store.neomodel_config")
    def test_configure(self, mock_config, mock_db):
        """Test that configure properly sets up the database connection"""
        store = DefaultStoreDB()
        test_url = "bolt://localhost:7687"

        store.configure(test_url)

        assert test_url == mock_config.DATABASE_URL
        mock_db.set_connection.assert_called_once_with(test_url)

    @patch("kairix_engine.summary_store.db")
    def test_cypher_query(self, mock_db):
        """Test that cypher_query passes through to db.cypher_query"""
        store = DefaultStoreDB()
        mock_db.cypher_query.return_value = (["result"], ["meta"])

        result = store.cypher_query("MATCH (n) RETURN n", {"param": "value"})

        mock_db.cypher_query.assert_called_once_with(
            "MATCH (n) RETURN n", {"param": "value"}
        )
        assert result == (["result"], ["meta"])


class TestSummaryStoreInitialization(unittest.TestCase):
    """Test cases for SummaryStore initialization"""

    @patch("kairix_engine.summary_store.SentenceTransformer")
    def test_init_with_override_store(self, mock_transformer):
        """Test initialization with override_store"""
        mock_store = MockStoreDB()
        store = SummaryStore(override_store=mock_store)

        assert store.store == mock_store
        mock_transformer.assert_called_once_with(DEFAULT_EMBEDDING_MODEL)

    @patch("kairix_engine.summary_store.SentenceTransformer")
    @patch("kairix_engine.summary_store.DefaultStoreDB")
    def test_init_with_store_url(self, mock_default_store_class, mock_transformer):
        """Test initialization with store_url"""
        test_url = "bolt://localhost:7687"
        mock_store_instance = Mock()
        mock_default_store_class.return_value = mock_store_instance

        store = SummaryStore(store_url=test_url)

        mock_default_store_class.assert_called_once()
        mock_store_instance.configure.assert_called_once_with(test_url)
        assert store.store == mock_store_instance

    @patch("kairix_engine.summary_store.SentenceTransformer")
    def test_init_with_custom_embedding_model(self, mock_transformer):
        """Test initialization with custom embedding model"""
        custom_model = "custom/model"
        mock_store = MockStoreDB()

        SummaryStore(override_store=mock_store, embedding_model=custom_model)

        mock_transformer.assert_called_once_with(custom_model)

    def test_init_without_store_or_url_raises_error(self):
        """Test that initialization without store or URL raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            SummaryStore()

        assert str(exc_info.value) == "Must provide store_url or override_store"


class TestSummaryStoreFunctionality(unittest.TestCase):
    """Test cases for SummaryStore functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_store = MockStoreDB()
        self.mock_transformer = Mock()
        # Create a mock numpy array with proper length and tolist method
        mock_array = MagicMock()
        mock_array.__len__.return_value = 3
        mock_array.tolist.return_value = [0.1, 0.2, 0.3]
        self.mock_transformer.encode.return_value = mock_array

        with patch("kairix_engine.summary_store.SentenceTransformer") as mock_st:
            mock_st.return_value = self.mock_transformer
            self.summary_store = SummaryStore(override_store=self.mock_store)

    def test_get_embedding(self):
        """Test _get_embedding method"""
        test_text = "test text"
        result = self.summary_store._get_embedding(test_text)

        self.mock_transformer.encode.assert_called_once_with(test_text)
        assert result == [0.1, 0.2, 0.3]

    def test_vector_search(self):
        """Test _vector_search method"""
        query_vector = [0.1, 0.2, 0.3]
        k = 3
        self.mock_store.cypher_query_mock.return_value = (
            [
                ["@#$%^&*()content1", 0.9],
                ["@#$%^&*()content2", 0.8],
                ["@#$%^&*()content3", 0.7],
            ],
            None,
        )

        result = self.summary_store._vector_search(query_vector, k)

        self.mock_store.cypher_query_mock.assert_called_once()
        call_args = self.mock_store.cypher_query_mock.call_args[0]
        assert "vector_index_MemoryShard_vector_address" in call_args[0]
        assert call_args[1] == {"k": k, "query_vector": query_vector}

        assert result == [("content1", 0.9), ("content2", 0.8), ("content3", 0.7)]

    def test_vector_search_empty_results(self):
        """Test _vector_search with empty results"""
        self.mock_store.cypher_query_mock.return_value = ([], None)

        result = self.summary_store._vector_search([0.1, 0.2], 2)

        assert result == []

    def test_search_success(self):
        """Test successful search operation"""
        query = "test query"
        k = 2
        self.mock_store.cypher_query_mock.return_value = (
            [["@#$%^&*()result1", 0.95], ["@#$%^&*()result2", 0.85]],
            None,
        )

        result = self.summary_store.search(query, k)

        self.mock_transformer.encode.assert_called_once_with(query)
        assert result == [("result1", 0.95), ("result2", 0.85)]

    def test_search_with_default_k(self):
        """Test search with default k value"""
        self.mock_store.cypher_query_mock.return_value = ([], None)

        self.summary_store.search("test")

        call_args = self.mock_store.cypher_query_mock.call_args[0]
        assert call_args[1]["k"] == 2  # default k value

    @patch("kairix_engine.summary_store.logger")
    def test_search_error_handling(self, mock_logger):
        """Test search error handling"""
        query = "test query"
        self.mock_transformer.encode.side_effect = Exception("Encoding failed")

        with pytest.raises(RuntimeError) as exc_info:
            self.summary_store.search(query)

        assert str(exc_info.value) == f"Failed to retrieve summaries for query {query}"
        mock_logger.error.assert_called_once()

    @patch("kairix_engine.summary_store.logger")
    def test_search_database_error(self, mock_logger):
        """Test search with database error"""
        query = "test query"
        self.mock_store.cypher_query_mock.side_effect = Exception("Database error")

        with pytest.raises(RuntimeError) as exc_info:
            self.summary_store.search(query)

        assert str(exc_info.value) == f"Failed to retrieve summaries for query {query}"
        mock_logger.error.assert_called_once()

    @patch("kairix_engine.summary_store.logger")
    def test_get_embedding_logging(self, mock_logger):
        """Test that _get_embedding logs debug information"""
        self.summary_store._get_embedding("test")

        mock_logger.debug.assert_called_once_with("Got embedding of length: 3.")


class TestCypherQuery(unittest.TestCase):
    """Test the Cypher query constant"""

    def test_cypher_query_format(self):
        """Test that the Cypher query is properly formatted"""
        from kairix_engine.summary_store import CYPHER_QUERY

        assert "vector_index_MemoryShard_vector_address" in CYPHER_QUERY
        assert "$k" in CYPHER_QUERY
        assert "$query_vector" in CYPHER_QUERY
        assert "node.shard_contents AS content" in CYPHER_QUERY
        assert "ORDER BY score DESC" in CYPHER_QUERY


if __name__ == "__main__":
    unittest.main()