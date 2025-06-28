"""Test implementation for SemanticGraphPerceptor."""

import pytest
from unittest.mock import Mock, patch

from kairix_core.cognition.perceptor.semantic_graph import SemanticGraphPerceptor, WeightedLinkage
from kairix_core.cognition.stores.embedded_data import EmbeddedDataStore
from kairix_core.types.cognition import Stimulus, StimulusType
from kairix_core.types.neo4j import Concept, SemanticLinkage


class TestSemanticGraphPerceptor:
    """Test cases for SemanticGraphPerceptor class."""
    
    @pytest.fixture
    def mock_embedded_store(self):
        """Mock the embedded data store."""
        store = Mock(spec=EmbeddedDataStore)
        store.search = Mock(return_value=[])
        return store
    
    @pytest.fixture
    def mock_concept(self):
        """Create a mock Concept."""
        concept = Mock(spec=Concept)
        concept.name = "test_concept"
        concept.encounters = ["encounter1", "encounter2"]
        return concept
    
    @pytest.fixture
    def mock_linkage(self):
        """Create a mock SemanticLinkage."""
        linkage = Mock(spec=SemanticLinkage)
        linkage.linkage_type = "relates_to"
        linkage.weight = [0.5, 0.3, 0.2]  # List to test len()
        return linkage
    
    def test_initialization(self, mock_embedded_store):
        """Test SemanticGraphPerceptor initialization."""
        perceptor = SemanticGraphPerceptor(data_store=mock_embedded_store)
        
        assert perceptor.data_store is mock_embedded_store
    
    @pytest.mark.asyncio
    async def test_perceive_with_user_message(self, mock_embedded_store):
        """Test perceive method with user_message stimulus."""
        # Set up mock concepts and linkages
        concept1 = Mock(spec=Concept)
        concept1.name = "machine learning"
        concept1.encounters = ["enc1", "enc2"]
        
        concept2 = Mock(spec=Concept)
        concept2.name = "artificial intelligence"
        concept2.encounters = ["enc3"]
        
        linkage = Mock(spec=SemanticLinkage)
        linkage.linkage_type = "is_part_of"
        linkage.weight = [0.8, 0.7]
        linkage.end_node = Mock(return_value=concept2)
        
        concept1.link = linkage
        
        # Configure mock store to return search results
        mock_embedded_store.search.return_value = [(concept1, 0.9)]
        
        perceptor = SemanticGraphPerceptor(data_store=mock_embedded_store)
        
        # Mock TextBlob
        with patch('kairix_core.cognition.perceptor.semantic_graph.TextBlob') as mock_textblob_class:
            mock_blob = Mock()
            mock_blob.noun_phrases = Mock()
            mock_blob.noun_phrases.lemmatize = Mock()
            mock_blob.noun_phrases.__iter__ = Mock(return_value=iter(["machine learning"]))
            mock_blob.correct = Mock()
            mock_textblob_class.return_value = mock_blob
            
            stimulus = Stimulus(
                content="Tell me about machine learning",
                type=StimulusType.user_message
            )
            
            perceptions = await perceptor.perceive(stimulus)
        
        # Verify TextBlob was used correctly
        mock_textblob_class.assert_called_once_with("Tell me about machine learning")
        mock_blob.correct.assert_called_once()
        mock_blob.noun_phrases.lemmatize.assert_called_once()
        
        # Verify search was called
        mock_embedded_store.search.assert_called_with("machine learning")
        
        # Verify perceptions
        assert len(perceptions) == 1
        assert perceptions[0].source == "semantic_graph.v1"
        assert "machine learning is_part_of artificial intelligence" in perceptions[0].content
        assert perceptions[0].confidence == 1.0
    
    @pytest.mark.asyncio
    async def test_traverse_keyword(self, mock_embedded_store, mock_concept, mock_linkage):
        """Test traverse_keyword method."""
        # Set up the linkage to return a related concept
        other_concept = Mock(spec=Concept)
        other_concept.name = "related_concept"
        other_concept.encounters = ["enc1"]
        
        mock_linkage.end_node.return_value = other_concept
        mock_concept.link = mock_linkage
        
        # Configure search to return concept with score
        mock_embedded_store.search.return_value = [(mock_concept, 0.85)]
        
        perceptor = SemanticGraphPerceptor(data_store=mock_embedded_store)
        
        results = await perceptor.traverse_keyword("test")
        
        assert len(results) == 1
        weighted_linkage = results[0]
        
        assert isinstance(weighted_linkage, WeightedLinkage)
        assert weighted_linkage.p is mock_concept
        assert weighted_linkage.q is other_concept
        assert weighted_linkage.linkage is mock_linkage
        assert weighted_linkage.base_score == 0.85
    
    def test_weighted_linkage_weight_calculation(self, mock_concept, mock_linkage):
        """Test WeightedLinkage weight calculation."""
        other_concept = Mock(spec=Concept)
        other_concept.name = "other"
        other_concept.encounters = ["enc1", "enc2", "enc3"]
        
        weighted_linkage = WeightedLinkage(
            p=mock_concept,
            q=other_concept,
            linkage=mock_linkage,
            base_score=0.5
        )
        
        # Weight = base_score * (len(p.encounters) + len(q.encounters) + len(linkage.weight))
        # = 0.5 * (2 + 3 + 3) = 0.5 * 8 = 4.0
        assert weighted_linkage.get_weight() == 4.0
    
    def test_weighted_linkage_string_representation(self, mock_concept, mock_linkage):
        """Test WeightedLinkage string representation."""
        other_concept = Mock(spec=Concept)
        other_concept.name = "other_concept"
        
        weighted_linkage = WeightedLinkage(
            p=mock_concept,
            q=other_concept,
            linkage=mock_linkage,
            base_score=0.7
        )
        
        assert str(weighted_linkage) == "test_concept relates_to other_concept"
    
    @pytest.mark.asyncio
    async def test_perceive_with_multiple_keywords(self, mock_embedded_store):
        """Test perceive with multiple keywords extracted."""
        # Set up multiple concepts
        concepts_data = [
            ("python", "programming language", "is_type_of", 0.9),
            ("data science", "field of study", "uses", 0.8),
            ("machine learning", "technique", "applied_in", 0.85)
        ]
        
        def create_search_result(name1, name2, linkage_type, score):
            concept1 = Mock(spec=Concept)
            concept1.name = name1
            concept1.encounters = ["enc1"]
            
            concept2 = Mock(spec=Concept)
            concept2.name = name2
            concept2.encounters = ["enc2"]
            
            linkage = Mock(spec=SemanticLinkage)
            linkage.linkage_type = linkage_type
            linkage.weight = [0.5]
            linkage.end_node = Mock(return_value=concept2)
            
            concept1.link = linkage
            
            return [(concept1, score)]
        
        # Configure search to return different results for different keywords
        search_results = {
            "python": create_search_result(*concepts_data[0]),
            "data science": create_search_result(*concepts_data[1]),
            "machine learning": create_search_result(*concepts_data[2])
        }
        
        mock_embedded_store.search.side_effect = lambda k: search_results.get(k, [])
        
        perceptor = SemanticGraphPerceptor(data_store=mock_embedded_store)
        
        with patch('kairix_core.cognition.perceptor.semantic_graph.TextBlob') as mock_textblob_class:
            mock_blob = Mock()
            mock_noun_phrases = Mock()
            mock_noun_phrases.lemmatize = Mock()
            mock_noun_phrases.__iter__ = Mock(return_value=iter(["python", "data science", "machine learning"]))
            mock_blob.noun_phrases = mock_noun_phrases
            mock_blob.correct = Mock()
            mock_textblob_class.return_value = mock_blob
            
            stimulus = Stimulus(
                content="I want to learn python for data science and machine learning",
                type=StimulusType.user_message
            )
            
            perceptions = await perceptor.perceive(stimulus)
        
        # Should have 3 perceptions (one for each keyword)
        assert len(perceptions) == 3
        
        # Verify all perceptions have correct format
        for perception in perceptions:
            assert perception.source == "semantic_graph.v1"
            assert perception.confidence == 1.0
    
    @pytest.mark.asyncio
    async def test_perceive_empty_search_results(self, mock_embedded_store):
        """Test perceive when no semantic matches found."""
        mock_embedded_store.search.return_value = []
        
        perceptor = SemanticGraphPerceptor(data_store=mock_embedded_store)
        
        with patch('kairix_core.cognition.perceptor.semantic_graph.TextBlob') as mock_textblob_class:
            mock_blob = Mock()
            mock_noun_phrases = Mock()
            mock_noun_phrases.lemmatize = Mock()
            mock_noun_phrases.__iter__ = Mock(return_value=iter(["unknown_term"]))
            mock_blob.noun_phrases = mock_noun_phrases
            mock_blob.correct = Mock()
            mock_textblob_class.return_value = mock_blob
            
            stimulus = Stimulus(
                content="Some unknown term",
                type=StimulusType.user_message
            )
            
            perceptions = await perceptor.perceive(stimulus)
        
        assert perceptions == []
    
    @pytest.mark.asyncio
    async def test_perceive_sorting_by_weight(self, mock_embedded_store):
        """Test that perceptions are sorted by weight in descending order."""
        # Create linkages with different weights
        def create_weighted_result(name, weight, base_score):
            concept1 = Mock(spec=Concept)
            concept1.name = f"{name}_source"
            concept1.encounters = ["e"] * 2
            
            concept2 = Mock(spec=Concept)
            concept2.name = f"{name}_target"
            concept2.encounters = ["e"] * 3
            
            linkage = Mock(spec=SemanticLinkage)
            linkage.linkage_type = "relates_to"
            linkage.weight = [0.1] * weight
            linkage.end_node = Mock(return_value=concept2)
            
            concept1.link = linkage
            
            return (concept1, base_score)
        
        # Create results with different weights
        # Weight calculation: base_score * (2 + 3 + weight_len)
        search_results = [
            create_weighted_result("low", 1, 0.1),    # 0.1 * (2 + 3 + 1) = 0.6
            create_weighted_result("high", 5, 0.5),   # 0.5 * (2 + 3 + 5) = 5.0
            create_weighted_result("medium", 3, 0.3), # 0.3 * (2 + 3 + 3) = 2.4
        ]
        
        mock_embedded_store.search.return_value = search_results
        
        perceptor = SemanticGraphPerceptor(data_store=mock_embedded_store)
        
        with patch('kairix_core.cognition.perceptor.semantic_graph.TextBlob') as mock_textblob_class:
            mock_blob = Mock()
            mock_noun_phrases = Mock()
            mock_noun_phrases.lemmatize = Mock()
            mock_noun_phrases.__iter__ = Mock(return_value=iter(["test"]))
            mock_blob.noun_phrases = mock_noun_phrases
            mock_blob.correct = Mock()
            mock_textblob_class.return_value = mock_blob
            
            stimulus = Stimulus(content="test", type=StimulusType.user_message)
            perceptions = await perceptor.perceive(stimulus)
        
        # Should be sorted by weight descending
        assert len(perceptions) == 3
        assert "high" in perceptions[0].content  # Highest weight
        assert "medium" in perceptions[1].content  # Medium weight
        assert "low" in perceptions[2].content  # Lowest weight
    
    @pytest.mark.asyncio
    async def test_perceive_limit_to_ten_results(self, mock_embedded_store):
        """Test that perceive returns at most 10 perceptions."""
        # Create more than 10 results
        results = []
        for i in range(15):
            concept1 = Mock(spec=Concept)
            concept1.name = f"concept_{i}"
            concept1.encounters = []
            
            concept2 = Mock(spec=Concept)
            concept2.name = f"related_{i}"
            concept2.encounters = []
            
            linkage = Mock(spec=SemanticLinkage)
            linkage.linkage_type = "relates_to"
            linkage.weight = []
            linkage.end_node = Mock(return_value=concept2)
            
            concept1.link = linkage
            results.append((concept1, 0.5))
        
        mock_embedded_store.search.return_value = results
        
        perceptor = SemanticGraphPerceptor(data_store=mock_embedded_store)
        
        with patch('kairix_core.cognition.perceptor.semantic_graph.TextBlob') as mock_textblob_class:
            mock_blob = Mock()
            mock_noun_phrases = Mock()
            mock_noun_phrases.lemmatize = Mock()
            mock_noun_phrases.__iter__ = Mock(return_value=iter(["test"]))
            mock_blob.noun_phrases = mock_noun_phrases
            mock_blob.correct = Mock()
            mock_textblob_class.return_value = mock_blob
            
            stimulus = Stimulus(content="test", type=StimulusType.user_message)
            perceptions = await perceptor.perceive(stimulus)
        
        # Should be limited to 10
        assert len(perceptions) == 10
    
    @pytest.mark.asyncio
    async def test_textblob_processing(self, mock_embedded_store):
        """Test TextBlob processing pipeline."""
        perceptor = SemanticGraphPerceptor(data_store=mock_embedded_store)
        
        with patch('kairix_core.cognition.perceptor.semantic_graph.TextBlob') as mock_textblob_class:
            mock_blob = Mock()
            mock_blob.noun_phrases = Mock()
            mock_blob.noun_phrases.lemmatize = Mock()
            mock_blob.noun_phrases.__iter__ = Mock(return_value=iter([]))
            mock_blob.correct = Mock()
            mock_textblob_class.return_value = mock_blob
            
            stimulus = Stimulus(
                content="This is a test sentence with spelling mistaks",
                type=StimulusType.user_message
            )
            
            await perceptor.perceive(stimulus)
            
            # Verify TextBlob processing steps
            mock_textblob_class.assert_called_once_with("This is a test sentence with spelling mistaks")
            mock_blob.correct.assert_called_once()
            mock_blob.noun_phrases.lemmatize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_empty_noun_phrases(self, mock_embedded_store):
        """Test handling when no noun phrases are extracted."""
        perceptor = SemanticGraphPerceptor(data_store=mock_embedded_store)
        
        with patch('kairix_core.cognition.perceptor.semantic_graph.TextBlob') as mock_textblob_class:
            mock_blob = Mock()
            mock_noun_phrases = Mock()
            mock_noun_phrases.lemmatize = Mock()
            mock_noun_phrases.__iter__ = Mock(return_value=iter([]))  # Empty noun phrases
            mock_blob.noun_phrases = mock_noun_phrases
            mock_blob.correct = Mock()
            mock_textblob_class.return_value = mock_blob
            
            stimulus = Stimulus(content="!", type=StimulusType.user_message)
            perceptions = await perceptor.perceive(stimulus)
        
        assert perceptions == []
        # Search should not be called
        mock_embedded_store.search.assert_not_called()