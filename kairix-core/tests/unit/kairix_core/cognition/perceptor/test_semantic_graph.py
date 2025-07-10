"""Simplified test implementation for SemanticGraphPerceptor."""

import pytest
from unittest.mock import Mock, patch

from kairix_core.cognition.perceptor.semantic_graph import SemanticGraphPerceptor
from kairix_core.cognition.stores.sqlite_embedded_data import SQLiteEmbeddedDataStore
from kairix_core.types.cognition import Stimulus, StimulusType


class TestSemanticGraphPerceptor:
    """Test cases for SemanticGraphPerceptor class."""
    
    @pytest.fixture
    def mock_embedded_store(self):
        """Mock the embedded data store."""
        store = Mock(spec=SQLiteEmbeddedDataStore)
        store.search = Mock(return_value=[])
        return store
    
    def test_initialization(self, mock_embedded_store):
        """Test SemanticGraphPerceptor initialization."""
        perceptor = SemanticGraphPerceptor(data_store=mock_embedded_store)
        
        assert perceptor.data_store is mock_embedded_store
    
    @pytest.mark.asyncio
    async def test_traverse_keyword_empty_results(self, mock_embedded_store):
        """Test traverse_keyword with no search results."""
        mock_embedded_store.search.return_value = []
        
        perceptor = SemanticGraphPerceptor(data_store=mock_embedded_store)
        results = await perceptor.traverse_keyword("nonexistent")
        
        assert results == []
        mock_embedded_store.search.assert_called_once_with("nonexistent")
    
    @pytest.mark.asyncio
    async def test_perceive_empty_content(self, mock_embedded_store):
        """Test perceive with empty content."""
        perceptor = SemanticGraphPerceptor(data_store=mock_embedded_store)
        
        with patch('kairix_core.cognition.perceptor.semantic_graph.TextBlob') as mock_textblob_class:
            mock_blob = Mock()
            mock_blob.noun_phrases = []
            mock_blob.correct.return_value = mock_blob
            mock_textblob_class.return_value = mock_blob
            
            stimulus = Stimulus(content="", type=StimulusType.user_message)
            perceptions = await perceptor.perceive(stimulus)
            
            assert perceptions == []
            mock_textblob_class.assert_called_once_with("")
            mock_blob.correct.assert_called_once()