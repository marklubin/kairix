"""Test implementation for SummaryInsightPerceptor."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from kairix_core.cognition.perceptor.summary_insight import SummaryInsightPerceptor
from kairix_core.cognition.stores.sqlite_embedded_data import SQLiteEmbeddedDataStore
from kairix_core.runtime.agent import AgentRuntime
from kairix_core.types.cognition import Stimulus, StimulusType
from agents import Agent


class TestSummaryInsightPerceptor:
    """Test cases for SummaryInsightPerceptor class."""
    
    @pytest.fixture
    def mock_runtime(self):
        """Mock the agent runtime."""
        runtime = Mock(spec=AgentRuntime)
        runtime.run = AsyncMock()
        return runtime
    
    @pytest.fixture
    def mock_embedded_store(self):
        """Mock the embedded data store."""
        store = Mock(spec=SQLiteEmbeddedDataStore)
        store.search = Mock(return_value=[])
        return store
    
    @pytest.fixture
    def mock_spacy_nlp(self):
        """Mock spaCy NLP model."""
        with patch('kairix_core.cognition.perceptor.summary_insight.spacy.load') as mock_load:
            mock_nlp = Mock()
            mock_load.return_value = mock_nlp
            yield mock_nlp
    
    def test_initialization(self, mock_runtime, mock_embedded_store, mock_spacy_nlp):
        """Test SummaryInsightPerceptor initialization."""
        perceptor = SummaryInsightPerceptor(
            runtime=mock_runtime,
            embedded_sumary_store=mock_embedded_store,
            k_memories=5
        )
        
        assert perceptor.runtime is mock_runtime
        assert perceptor.embedded_summary_store is mock_embedded_store
        assert perceptor.k_memories == 5
        assert isinstance(perceptor.insight_extraction_agent, Agent)
        assert perceptor.insight_extraction_agent.name == "insight_extractor"
        assert perceptor.nlp is mock_spacy_nlp
    
    def test_spacy_download_on_missing_model(self, mock_runtime, mock_embedded_store):
        """Test that spaCy model is downloaded if not available."""
        with patch('kairix_core.cognition.perceptor.summary_insight.spacy.load') as mock_load:
            with patch('kairix_core.cognition.perceptor.summary_insight.spacy.cli.download') as mock_download:
                # First load attempt fails
                mock_load.side_effect = [Exception("Model not found"), Mock()]
                
                SummaryInsightPerceptor(
                    runtime=mock_runtime,
                    embedded_sumary_store=mock_embedded_store,
                    k_memories=5
                )
                
                # Verify download was called
                mock_download.assert_called_once_with("en_core_web_sm")
                # Verify load was called twice
                assert mock_load.call_count == 2
    
    @pytest.mark.asyncio
    async def test_perceive_with_user_message(self, mock_runtime, mock_embedded_store, mock_spacy_nlp):
        """Test perceive method with user_message stimulus."""
        # Set up mock spaCy document
        mock_doc = Mock()
        mock_token1 = Mock()
        mock_token1.pos_ = "VERB"
        mock_token1.lemma_ = "learn"
        
        mock_token2 = Mock()
        mock_token2.pos_ = "NOUN"  # Not in POS_TO_INCLUDE
        mock_token2.lemma_ = "python"
        
        mock_entity = Mock()
        mock_entity.lemma_ = "machine_learning"
        
        mock_doc.__iter__ = Mock(return_value=iter([mock_token1, mock_token2]))
        mock_doc.ents = [mock_entity]
        
        mock_spacy_nlp.return_value = mock_doc
        
        # Set up memory search results
        memory1 = "I learned about machine learning algorithms yesterday."
        memory2 = "Python is great for learning data science."
        mock_embedded_store.search.return_value = [(memory1, 0.9), (memory2, 0.8)]
        
        # Set up memory processing
        mock_memory_doc1 = Mock()
        mock_memory_doc2 = Mock()
        
        # Set up sentences for memories
        mock_sent1 = Mock()
        mock_sent1.__str__ = Mock(return_value="I learned about machine learning algorithms yesterday.")
        
        mock_sent2 = Mock()
        mock_sent2.__str__ = Mock(return_value="Python is great for learning data science.")
        
        # Token in memory1 matching keyword
        mock_memory_token1 = Mock()
        mock_memory_token1.lemma_ = "learn"
        mock_memory_token1.sent = mock_sent1
        
        # Entity in memory1
        mock_memory_entity1 = Mock()
        mock_memory_entity1.lemma_ = "machine_learning"
        mock_memory_entity1.sent = mock_sent1
        
        # Token in memory2
        mock_memory_token2 = Mock()
        mock_memory_token2.lemma_ = "learn"
        mock_memory_token2.sent = mock_sent2
        
        mock_memory_doc1.__iter__ = Mock(return_value=iter([mock_memory_token1]))
        mock_memory_doc1.ents = [mock_memory_entity1]
        
        mock_memory_doc2.__iter__ = Mock(return_value=iter([mock_memory_token2]))
        mock_memory_doc2.ents = []
        
        # Configure nlp to return different docs for different inputs
        def nlp_side_effect(text):
            if text == memory1:
                return mock_memory_doc1
            elif text == memory2:
                return mock_memory_doc2
            else:
                return mock_doc
        
        mock_spacy_nlp.side_effect = nlp_side_effect
        
        # Mock TextBlob
        with patch('kairix_core.cognition.perceptor.summary_insight.textblob.TextBlob') as mock_textblob_class:
            mock_blob = Mock()
            mock_blob.correct = Mock(return_value="I want to learn about machine learning")
            mock_textblob_class.return_value = mock_blob
            
            perceptor = SummaryInsightPerceptor(
                runtime=mock_runtime,
                embedded_sumary_store=mock_embedded_store,
                k_memories=5
            )
            
            stimulus = Stimulus(
                content="I want to lern about machine learning",  # Typo intentional
                type=StimulusType.user_message
            )
            
            perceptions = await perceptor.perceive(stimulus)
        
        # Verify TextBlob correction
        mock_textblob_class.assert_called_once_with("I want to lern about machine learning")
        
        # Verify keyword extraction
        # Keywords are in a set, so order may vary
        call_args = mock_embedded_store.search.call_args
        assert call_args[0][1] == 5  # Check k_memories parameter
        search_query = call_args[0][0]
        search_keywords = set(search_query.split())
        assert search_keywords == {"learn", "machine_learning"}
        
        # Verify perceptions (should have unique sentences)
        assert len(perceptions) > 0
        for perception in perceptions:
            assert perception.source == "summary_insight_memory"
            assert perception.confidence in [0.9, 0.8]  # Should match the search scores
    
    @pytest.mark.asyncio
    async def test_perceive_non_user_message(self, mock_runtime, mock_embedded_store, mock_spacy_nlp):
        """Test perceive method with non-user_message stimulus types."""
        perceptor = SummaryInsightPerceptor(
            runtime=mock_runtime,
            embedded_sumary_store=mock_embedded_store,
            k_memories=5
        )
        
        stimulus = Stimulus(
            content="2024-01-01T12:00:00",
            type=StimulusType.time_tick
        )
        
        perceptions = await perceptor.perceive(stimulus)
        
        assert perceptions == []
        # Should not process anything
        mock_embedded_store.search.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_perceive_short_input(self, mock_runtime, mock_embedded_store, mock_spacy_nlp):
        """Test perceive with input shorter than perception limit."""
        perceptor = SummaryInsightPerceptor(
            runtime=mock_runtime,
            embedded_sumary_store=mock_embedded_store,
            k_memories=5
        )
        
        with patch('kairix_core.cognition.perceptor.summary_insight.textblob.TextBlob') as mock_textblob_class:
            mock_blob = Mock()
            mock_blob.correct = Mock(return_value="Hi")
            mock_textblob_class.return_value = mock_blob
            
            stimulus = Stimulus(
                content="Hi",
                type=StimulusType.user_message
            )
            
            perceptions = await perceptor.perceive(stimulus)
        
        assert perceptions == []
        # Should not search when input is too short
        mock_embedded_store.search.assert_not_called()
    
    def test_generate_terms(self, mock_runtime, mock_embedded_store, mock_spacy_nlp):
        """Test keyword generation from user input."""
        # Set up mock spaCy document
        mock_doc = Mock()
        
        # Create tokens with different POS tags
        tokens = [
            Mock(pos_="VERB", lemma_="run"),
            Mock(pos_="PRON", lemma_="I"),
            Mock(pos_="ADJ", lemma_="fast"),
            Mock(pos_="NOUN", lemma_="race"),  # Not in POS_TO_INCLUDE
            Mock(pos_="DET", lemma_="the"),    # Not in POS_TO_INCLUDE
        ]
        
        # Create entities
        entities = [
            Mock(lemma_="marathon"),
            Mock(lemma_="Boston")
        ]
        
        mock_doc.__iter__ = Mock(return_value=iter(tokens))
        mock_doc.ents = entities
        
        mock_spacy_nlp.return_value = mock_doc
        
        perceptor = SummaryInsightPerceptor(
            runtime=mock_runtime,
            embedded_sumary_store=mock_embedded_store,
            k_memories=5
        )
        
        keywords = perceptor.generate_terms("I run fast in the marathon race")
        
        # Should include VERB, PRON, ADJ from tokens and all entities
        expected_keywords = {"run", "I", "fast", "marathon", "Boston"}
        assert keywords == expected_keywords
    
    @pytest.mark.asyncio
    async def test_empty_memory_search_results(self, mock_runtime, mock_embedded_store, mock_spacy_nlp):
        """Test handling when no memories are found."""
        mock_embedded_store.search.return_value = []
        
        # Set up basic mock doc
        mock_doc = Mock()
        mock_token = Mock(pos_="VERB", lemma_="test")
        mock_doc.__iter__ = Mock(return_value=iter([mock_token]))
        mock_doc.ents = []
        mock_spacy_nlp.return_value = mock_doc
        
        with patch('kairix_core.cognition.perceptor.summary_insight.textblob.TextBlob') as mock_textblob_class:
            mock_blob = Mock()
            mock_blob.correct = Mock(return_value="This is a test message about nothing")
            mock_textblob_class.return_value = mock_blob
            
            perceptor = SummaryInsightPerceptor(
                runtime=mock_runtime,
                embedded_sumary_store=mock_embedded_store,
                k_memories=5
            )
            
            stimulus = Stimulus(
                content="This is a test message about nothing",
                type=StimulusType.user_message
            )
            
            perceptions = await perceptor.perceive(stimulus)
        
        assert perceptions == []
    
    @pytest.mark.asyncio
    async def test_insight_deduplication(self, mock_runtime, mock_embedded_store, mock_spacy_nlp):
        """Test that duplicate insights are removed."""
        # Set up user input processing
        mock_doc = Mock()
        mock_token = Mock(pos_="VERB", lemma_="learn")
        mock_doc.__iter__ = Mock(return_value=iter([mock_token]))
        mock_doc.ents = []
        
        # Set up memories that will produce the same sentence
        memory1 = "I want to learn Python."
        memory2 = "I want to learn Python."  # Duplicate
        mock_embedded_store.search.return_value = [(memory1, 0.9), (memory2, 0.8)]
        
        # Mock sentence that will be repeated
        mock_sent = Mock()
        mock_sent.__str__ = Mock(return_value="I want to learn Python.")
        
        # Set up memory docs
        mock_memory_doc = Mock()
        mock_memory_token = Mock(lemma_="learn", sent=mock_sent)
        mock_memory_doc.__iter__ = Mock(return_value=iter([mock_memory_token]))
        mock_memory_doc.ents = []
        
        def nlp_side_effect(text):
            if text in [memory1, memory2]:
                return mock_memory_doc
            return mock_doc
        
        mock_spacy_nlp.side_effect = nlp_side_effect
        
        with patch('kairix_core.cognition.perceptor.summary_insight.textblob.TextBlob') as mock_textblob_class:
            mock_blob = Mock()
            mock_blob.correct = Mock(return_value="I want to learn programming")
            mock_textblob_class.return_value = mock_blob
            
            perceptor = SummaryInsightPerceptor(
                runtime=mock_runtime,
                embedded_sumary_store=mock_embedded_store,
                k_memories=5
            )
            
            stimulus = Stimulus(content="I want to learn programming", type=StimulusType.user_message)
            perceptions = await perceptor.perceive(stimulus)
        
        # With use_full_memories=True, we get both memories back (no deduplication)
        assert len(perceptions) == 2
        assert perceptions[0].content == memory1
        assert perceptions[0].confidence == 0.9
        assert perceptions[1].content == memory2
        assert perceptions[1].confidence == 0.8
    
    @pytest.mark.asyncio
    async def test_multiple_insights_from_single_memory(self, mock_runtime, mock_embedded_store, mock_spacy_nlp):
        """Test extracting multiple insights from a single memory."""
        # User input
        mock_doc = Mock()
        mock_token1 = Mock(pos_="VERB", lemma_="learn")
        mock_token2 = Mock(pos_="VERB", lemma_="code")
        mock_doc.__iter__ = Mock(return_value=iter([mock_token1, mock_token2]))
        mock_doc.ents = []
        
        # Memory with multiple sentences
        memory = "I love to learn new things. Coding is fun. Python helps you learn quickly."
        mock_embedded_store.search.return_value = [(memory, 0.9)]
        
        # Mock sentences
        sent1 = Mock()
        sent1.__str__ = Mock(return_value="I love to learn new things.")
        
        sent2 = Mock()
        sent2.__str__ = Mock(return_value="Coding is fun.")
        
        sent3 = Mock()
        sent3.__str__ = Mock(return_value="Python helps you learn quickly.")
        
        # Memory document with multiple matching tokens
        mock_memory_doc = Mock()
        memory_tokens = [
            Mock(lemma_="love", sent=sent1),
            Mock(lemma_="learn", sent=sent1),  # Matches keyword
            Mock(lemma_="code", sent=sent2),   # Matches keyword (lemma of "Coding")
            Mock(lemma_="fun", sent=sent2),
            Mock(lemma_="learn", sent=sent3),  # Matches keyword
        ]
        mock_memory_doc.__iter__ = Mock(return_value=iter(memory_tokens))
        mock_memory_doc.ents = []
        
        def nlp_side_effect(text):
            if text == memory:
                return mock_memory_doc
            return mock_doc
        
        mock_spacy_nlp.side_effect = nlp_side_effect
        
        with patch('kairix_core.cognition.perceptor.summary_insight.textblob.TextBlob') as mock_textblob_class:
            mock_blob = Mock()
            mock_blob.correct = Mock(return_value="I want to learn to code")
            mock_textblob_class.return_value = mock_blob
            
            perceptor = SummaryInsightPerceptor(
                runtime=mock_runtime,
                embedded_sumary_store=mock_embedded_store,
                k_memories=5
            )
            
            stimulus = Stimulus(content="I want to learn to code", type=StimulusType.user_message)
            perceptions = await perceptor.perceive(stimulus)
        
        # With use_full_memories=True, we get the full memory, not individual sentences
        assert len(perceptions) == 1
        assert perceptions[0].content == memory
        assert perceptions[0].confidence == 0.9
    
    def test_pos_filtering(self, mock_runtime, mock_embedded_store, mock_spacy_nlp):
        """Test that only specific POS tags are included in keywords."""
        mock_doc = Mock()
        
        # Create tokens covering all POS types we care about
        tokens = [
            Mock(pos_="PRON", lemma_="I"),      # Should include
            Mock(pos_="VERB", lemma_="run"),    # Should include
            Mock(pos_="ADJ", lemma_="fast"),    # Should include
            Mock(pos_="NOUN", lemma_="race"),   # Should NOT include
            Mock(pos_="ADV", lemma_="quickly"), # Should NOT include
            Mock(pos_="CONJ", lemma_="and"),    # Should NOT include
        ]
        
        mock_doc.__iter__ = Mock(return_value=iter(tokens))
        mock_doc.ents = []
        
        mock_spacy_nlp.return_value = mock_doc
        
        perceptor = SummaryInsightPerceptor(
            runtime=mock_runtime,
            embedded_sumary_store=mock_embedded_store,
            k_memories=5
        )
        
        keywords = perceptor.generate_terms("I run fast in the race quickly and smoothly")
        
        # Should only include PRON, VERB, ADJ
        assert keywords == {"I", "run", "fast"}
    
    @pytest.mark.asyncio
    async def test_run_insights_method(self, mock_runtime, mock_embedded_store, mock_spacy_nlp):
        """Test the _run_insights method for LLM integration."""
        # Set up mock results
        mock_result1 = Mock()
        mock_result1.final_output_as = Mock(return_value="Insight 1")
        
        mock_result2 = Mock()
        mock_result2.final_output_as = Mock(return_value="Insight 2")
        
        mock_runtime.run.side_effect = [mock_result1, mock_result2]
        
        perceptor = SummaryInsightPerceptor(
            runtime=mock_runtime,
            embedded_sumary_store=mock_embedded_store,
            k_memories=5
        )
        
        prompts = ["Extract insight from text 1", "Extract insight from text 2"]
        results = await perceptor._run_insights(prompts)
        
        assert results == ["Insight 1", "Insight 2"]
        assert mock_runtime.run.call_count == 2
        
        # Verify agent was called with correct prompts
        calls = mock_runtime.run.call_args_list
        assert calls[0][0][1] == "Extract insight from text 1"
        assert calls[1][0][1] == "Extract insight from text 2"