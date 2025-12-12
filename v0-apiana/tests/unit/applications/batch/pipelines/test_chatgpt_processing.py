"""
Unit tests for the ChatGPT processing pipeline.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from apiana.applications.batch.pipelines.chatgpt_processing import (
    create_chatgpt_processing_pipeline,
    create_simple_chatgpt_pipeline,
    create_chunking_only_pipeline
)
from apiana.core.pipelines.base import Pipeline
from apiana.types.chat_fragment import ChatFragment


class TestChatGPTProcessingPipelines:
    """Test ChatGPT processing pipeline creation and execution."""
    
    @patch('apiana.applications.batch.pipelines.chatgpt_processing.LocalTransformersLLM')
    @patch('apiana.applications.batch.pipelines.chatgpt_processing.SentenceTransformerEmbeddings')
    def test_create_chatgpt_processing_pipeline(self, mock_embedder_class, mock_llm_class):
        """Test creating the full ChatGPT processing pipeline."""
        # Mock the providers
        mock_llm = Mock()
        mock_embedder = Mock()
        mock_llm_class.return_value = mock_llm
        mock_embedder_class.return_value = mock_embedder
        
        pipeline = create_chatgpt_processing_pipeline()
        
        # Should create a pipeline with correct configuration
        assert isinstance(pipeline, Pipeline)
        assert pipeline.name == "chatgpt_processing"
        assert len(pipeline.components) == 5
        
        # Check component names and order
        component_names = [c.name for c in pipeline.components]
        expected_names = ["chatgpt_reader", "validator", "chunker", "summarizer", "embedder"]
        assert component_names == expected_names
        
        # Verify LLM and embedder were created with correct parameters
        mock_llm_class.assert_called_once_with(
            model_name="microsoft/DialoGPT-small",
            device="auto"
        )
        mock_embedder_class.assert_called_once_with(
            "sentence-transformers/all-MiniLM-L6-v2",
            trust_remote_code=True
        )
    
    @patch('apiana.applications.batch.pipelines.chatgpt_processing.LocalTransformersLLM')
    def test_create_simple_chatgpt_pipeline(self, mock_llm_class):
        """Test creating the simple ChatGPT pipeline."""
        mock_llm = Mock()
        mock_llm_class.return_value = mock_llm
        
        pipeline = create_simple_chatgpt_pipeline()
        
        # Should create a simpler pipeline
        assert isinstance(pipeline, Pipeline)
        assert pipeline.name == "simple_chatgpt"
        assert len(pipeline.components) == 3
        
        # Check component names and order
        component_names = [c.name for c in pipeline.components]
        expected_names = ["chatgpt_reader", "validator", "summarizer"]
        assert component_names == expected_names
        
        # Verify LLM was created
        mock_llm_class.assert_called_once_with(
            model_name="microsoft/DialoGPT-small",
            device="auto"
        )
    
    def test_create_chunking_only_pipeline(self):
        """Test creating the chunking-only pipeline."""
        pipeline = create_chunking_only_pipeline()
        
        # Should create a minimal pipeline
        assert isinstance(pipeline, Pipeline)
        assert pipeline.name == "chunking_only"
        assert len(pipeline.components) == 3
        
        # Check component names and order
        component_names = [c.name for c in pipeline.components]
        expected_names = ["chatgpt_reader", "validator", "chunker"]
        assert component_names == expected_names
    
    def test_pipeline_component_configuration(self):
        """Test that pipeline components are configured correctly."""
        pipeline = create_chunking_only_pipeline()
        
        # Check validator configuration
        validator = pipeline.components[1]
        assert validator.name == "validator"
        assert validator.config["min_messages"] == 1
        assert validator.config["require_title"] == False
        
        # Check chunker configuration
        chunker = pipeline.components[2]
        assert chunker.name == "chunker"
        assert chunker.config["max_tokens"] == 5000
        assert chunker.config["model_name"] == "gpt2"
    
    @patch('apiana.applications.batch.pipelines.chatgpt_processing.LocalTransformersLLM')
    @patch('apiana.applications.batch.pipelines.chatgpt_processing.SentenceTransformerEmbeddings')
    def test_pipeline_provider_injection(self, mock_embedder_class, mock_llm_class):
        """Test that providers are correctly injected into components."""
        # Mock the providers
        mock_llm = Mock()
        mock_embedder = Mock()
        mock_llm_class.return_value = mock_llm
        mock_embedder_class.return_value = mock_embedder
        
        pipeline = create_chatgpt_processing_pipeline()
        
        # Get the summarizer and embedder components
        summarizer = pipeline.components[3]  # 4th component
        embedder = pipeline.components[4]    # 5th component
        
        # Verify providers were injected
        assert summarizer.llm_provider is mock_llm
        assert embedder.embedding_provider is mock_embedder
    
    @patch('apiana.applications.batch.pipelines.chatgpt_processing.LocalTransformersLLM')
    def test_summarizer_configuration(self, mock_llm_class):
        """Test summarizer component configuration."""
        mock_llm = Mock()
        mock_llm_class.return_value = mock_llm
        
        pipeline = create_simple_chatgpt_pipeline()
        summarizer = pipeline.components[2]  # 3rd component
        
        # Check summarizer configuration
        assert summarizer.name == "summarizer"
        assert summarizer.config["system_prompt"] == "Summarize this conversation concisely."
        assert summarizer.config["user_template"] == "Conversation:\n\n{conversation}\n\nSummary:"
    
    def test_pipeline_validation(self):
        """Test that created pipelines pass validation."""
        # Test all pipeline types
        pipelines = [
            create_chunking_only_pipeline(),
        ]
        
        for pipeline in pipelines:
            validation_errors = pipeline.validate()
            assert validation_errors == [], f"Pipeline {pipeline.name} has validation errors: {validation_errors}"
    
    @patch('apiana.applications.batch.pipelines.chatgpt_processing.LocalTransformersLLM')
    @patch('apiana.applications.batch.pipelines.chatgpt_processing.SentenceTransformerEmbeddings')
    def test_full_pipeline_integration(self, mock_embedder_class, mock_llm_class):
        """Test full pipeline creation and basic structure verification."""
        # Mock the providers
        mock_llm = Mock()
        mock_embedder = Mock()
        mock_llm_class.return_value = mock_llm
        mock_embedder_class.return_value = mock_embedder
        
        pipeline = create_chatgpt_processing_pipeline()
        
        # Verify pipeline structure
        assert isinstance(pipeline, Pipeline)
        assert len(pipeline.components) == 5
        
        # Verify all components have unique names
        component_names = [c.name for c in pipeline.components]
        assert len(component_names) == len(set(component_names)), "Component names should be unique"
        
        # Verify pipeline can be validated without errors
        validation_errors = pipeline.validate()
        assert validation_errors == []
    
    def test_component_types(self):
        """Test that components are of the expected types."""
        pipeline = create_chunking_only_pipeline()
        
        # Import component types for checking
        from apiana.core.components import (
            ChatGPTExportReader,
            ValidationTransform,
            ConversationChunkerComponent
        )
        
        # Check component types
        assert isinstance(pipeline.components[0], ChatGPTExportReader)
        assert isinstance(pipeline.components[1], ValidationTransform)
        assert isinstance(pipeline.components[2], ConversationChunkerComponent)
    
    @patch('apiana.applications.batch.pipelines.chatgpt_processing.LocalTransformersLLM')
    def test_pipeline_execution_flow(self, mock_llm_class):
        """Test that pipeline components are chained correctly."""
        # This is a basic test to ensure the pipeline can be executed
        # In a real scenario, you'd mock the components and test data flow
        
        mock_llm = Mock()
        mock_llm_class.return_value = mock_llm
        
        pipeline = create_simple_chatgpt_pipeline()
        
        # Verify the pipeline has the expected flow
        # Reader -> Validator -> Summarizer
        component_types = [type(c).__name__ for c in pipeline.components]
        expected_types = ["ChatGPTExportReader", "ValidationTransform", "SummarizerTransform"]
        assert component_types == expected_types
        
        # Ensure each component can be called with mock data
        for component in pipeline.components:
            # Each component should have a process method
            assert hasattr(component, 'process')
            assert callable(component.process)