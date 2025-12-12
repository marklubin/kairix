"""
Unit tests for pipeline type validation.
"""

import pytest
from typing import List

from apiana.core.pipelines.base import PipelineBuilder
from apiana.core.components.common import Component, ComponentResult
from apiana.types.chat_fragment import ChatFragment


class MockStringComponent(Component):
    """Mock component that takes string input and outputs string."""
    
    input_types = [str]
    output_types = [str]
    
    def process(self, input_data):
        return ComponentResult(data=f"processed_{input_data}")


class MockListComponent(Component):
    """Mock component that takes list input and outputs list."""
    
    input_types = [List[str]]
    output_types = [List[str]]
    
    def process(self, input_data):
        return ComponentResult(data=[f"processed_{item}" for item in input_data])


class MockIntComponent(Component):
    """Mock component that takes int input and outputs int."""
    
    input_types = [int]
    output_types = [int]
    
    def process(self, input_data):
        return ComponentResult(data=input_data * 2)


class TestComponentTypeCompatibility:
    """Test component type compatibility checking."""
    
    def test_compatible_types(self):
        """Test components with compatible types."""
        comp1 = MockStringComponent("string1")
        comp2 = MockStringComponent("string2")
        
        assert comp1.is_compatible_with(comp2)
        assert comp2.is_compatible_with(comp1)
    
    def test_incompatible_types(self):
        """Test components with incompatible types."""
        string_comp = MockStringComponent("string")
        int_comp = MockIntComponent("int")
        
        assert not string_comp.is_compatible_with(int_comp)
        assert not int_comp.is_compatible_with(string_comp)
    
    def test_list_type_compatibility(self):
        """Test list type compatibility."""
        string_comp = MockStringComponent("string")
        list_comp = MockListComponent("list")
        
        # String and List[str] should not be compatible
        assert not string_comp.is_compatible_with(list_comp)
        assert not list_comp.is_compatible_with(string_comp)
    
    def test_accepts_input_type(self):
        """Test accepts_input_type method."""
        string_comp = MockStringComponent("string")
        
        assert string_comp.accepts_input_type(str)
        assert not string_comp.accepts_input_type(int)
        assert not string_comp.accepts_input_type(List[str])
    
    def test_produces_output_type(self):
        """Test produces_output_type method."""
        string_comp = MockStringComponent("string")
        
        assert string_comp.produces_output_type(str)
        assert not string_comp.produces_output_type(int)
        assert not string_comp.produces_output_type(List[str])


class TestPipelineBuilderTypeValidation:
    """Test PipelineBuilder type validation."""
    
    def test_compatible_pipeline_builds(self):
        """Test that compatible components can be chained."""
        builder = PipelineBuilder("compatible_test")
        
        # This should work without raising an exception
        builder.add_component(MockStringComponent("comp1"))
        builder.add_component(MockStringComponent("comp2"))
        
        pipeline = builder.build()
        assert len(pipeline.components) == 2
    
    def test_incompatible_pipeline_fails_on_add(self):
        """Test that incompatible components fail when added."""
        builder = PipelineBuilder("incompatible_test")
        builder.add_component(MockStringComponent("string_comp"))
        
        # This should raise a TypeError
        with pytest.raises(TypeError, match="Type mismatch"):
            builder.add_component(MockIntComponent("int_comp"))
    
    def test_type_validation_can_be_disabled(self):
        """Test that type validation can be disabled."""
        builder = PipelineBuilder("disable_validation_test")
        builder.add_component(MockStringComponent("string_comp"))
        
        # This should work when validation is disabled
        builder.add_component(MockIntComponent("int_comp"), validate_types=False)
        
        # But the built pipeline should fail validation
        validation_errors = builder.validate()
        assert len(validation_errors) > 0
        assert "Type incompatibility" in validation_errors[0]
    
    def test_insert_component_type_validation(self):
        """Test type validation when inserting components."""
        builder = PipelineBuilder("insert_test")
        builder.add_component(MockStringComponent("comp1"))
        builder.add_component(MockStringComponent("comp3"))
        
        # Inserting compatible component should work
        builder.insert_component(1, MockStringComponent("comp2"))
        assert len(builder.components) == 3
        
        # Inserting incompatible component should fail
        with pytest.raises(TypeError, match="Type mismatch"):
            builder.insert_component(1, MockIntComponent("int_comp"))
    
    def test_validation_error_messages(self):
        """Test that validation error messages are informative."""
        builder = PipelineBuilder("error_message_test")
        builder.add_component(MockStringComponent("string_comp"), validate_types=False)
        builder.add_component(MockIntComponent("int_comp"), validate_types=False)
        
        errors = builder.validate()
        assert len(errors) == 1
        error_msg = errors[0]
        
        # Check that error message contains useful information
        assert "Type incompatibility" in error_msg
        assert "MockStringComponent" in error_msg
        assert "MockIntComponent" in error_msg
        assert "str" in error_msg
        assert "int" in error_msg
    
    def test_validate_type_chain_empty_pipeline(self):
        """Test type chain validation with empty pipeline."""
        builder = PipelineBuilder("empty_test")
        errors = builder.validate_type_chain()
        assert errors == []
    
    def test_validate_type_chain_single_component(self):
        """Test type chain validation with single component."""
        builder = PipelineBuilder("single_test")
        builder.add_component(MockStringComponent("comp1"))
        
        errors = builder.validate_type_chain()
        assert errors == []


class TestRealComponentTypeValidation:
    """Test type validation with real pipeline components."""
    
    def test_valid_chatgpt_pipeline(self):
        """Test a valid ChatGPT processing pipeline."""
        from apiana.core.components import (
            ChatGPTExportReader,
            ValidationTransform,
            ConversationChunkerComponent,
            SummarizerTransform,
            EmbeddingTransform
        )
        
        # This should build successfully
        pipeline = PipelineBuilder("valid_chatgpt")\
            .add_component(ChatGPTExportReader("reader"))\
            .add_component(ValidationTransform("validator"))\
            .add_component(ConversationChunkerComponent("chunker"))\
            .add_component(SummarizerTransform("summarizer"))\
            .add_component(EmbeddingTransform("embedder"))\
            .build()
        
        assert len(pipeline.components) == 5
        
        # Validate that there are no type errors
        builder = PipelineBuilder("validation_test")
        builder.components = pipeline.components
        errors = builder.validate_type_chain()
        assert errors == []
    
    def test_invalid_chatgpt_pipeline(self):
        """Test an invalid ChatGPT processing pipeline."""
        from apiana.core.components import (
            ChatGPTExportReader,
            ConversationChunkerComponent,
            EmbeddingTransform
        )
        
        builder = PipelineBuilder("invalid_chatgpt")
        builder.add_component(ChatGPTExportReader("reader"))
        builder.add_component(ConversationChunkerComponent("chunker"))
        
        # This should fail - chunker outputs List[ChatFragment] but embedder expects List[dict]
        with pytest.raises(TypeError, match="Type mismatch"):
            builder.add_component(EmbeddingTransform("embedder"))
    
    def test_mixed_valid_invalid_components(self):
        """Test pipeline with mix of valid and invalid component chains."""
        from apiana.core.components import (
            ChatGPTExportReader,
            ValidationTransform,
            EmbeddingTransform
        )
        
        builder = PipelineBuilder("mixed_test")
        # Add components without validation to create invalid chain
        builder.add_component(ChatGPTExportReader("reader"))
        builder.add_component(ValidationTransform("validator"))
        builder.add_component(EmbeddingTransform("embedder"), validate_types=False)  # Invalid!
        
        # Validation should catch the incompatibility
        errors = builder.validate_type_chain()
        assert len(errors) == 1
        assert "ValidationTransform" in errors[0]
        assert "EmbeddingTransform" in errors[0]