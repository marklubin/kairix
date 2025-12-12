"""
Unit tests for the generic PipelineBuilder.
"""

import pytest
from typing import Any
from unittest.mock import Mock

from apiana.core.pipelines.base import PipelineBuilder, Pipeline
from apiana.core.components.common import Component, ComponentResult


class MockComponent(Component):
    """Mock component for testing."""
    
    def __init__(self, name: str, config: dict = None, should_fail: bool = False):
        super().__init__(name, config)
        self.should_fail = should_fail
        self.process_called = False
        self.process_call_count = 0
        
    def process(self, input_data: Any) -> ComponentResult:
        self.process_called = True
        self.process_call_count += 1
        
        if self.should_fail:
            return ComponentResult(
                data=None,
                errors=[f"Mock component {self.name} failed"]
            )
        
        # Transform data by adding component name
        if isinstance(input_data, list):
            output_data = input_data + [self.name]
        else:
            output_data = [input_data, self.name]
            
        return ComponentResult(
            data=output_data,
            metadata={'component': self.name}
        )
    
    def validate_config(self):
        errors = []
        if self.config and self.config.get('invalid'):
            errors.append("Config marked as invalid")
        return errors


class TestPipelineBuilder:
    """Test the generic PipelineBuilder."""
    
    def test_builder_creation(self):
        """Test basic builder creation."""
        builder = PipelineBuilder("test_pipeline")
        assert builder.name == "test_pipeline"
        assert builder.get_stage_count() == 0
        assert builder.is_empty()
    
    def test_add_single_component(self):
        """Test adding a single component."""
        builder = PipelineBuilder()
        component = MockComponent("comp1")
        
        result = builder.add_component(component)
        
        # Should return self for chaining
        assert result is builder
        assert builder.get_stage_count() == 1
        assert not builder.is_empty()
        assert builder.has_component("comp1")
    
    def test_add_multiple_components(self):
        """Test adding multiple components."""
        builder = PipelineBuilder()
        comp1 = MockComponent("comp1")
        comp2 = MockComponent("comp2")
        comp3 = MockComponent("comp3")
        
        builder.add_components(comp1, comp2, comp3)
        
        assert builder.get_stage_count() == 3
        assert builder.has_component("comp1")
        assert builder.has_component("comp2")
        assert builder.has_component("comp3")
    
    def test_chaining_methods(self):
        """Test method chaining."""
        comp1 = MockComponent("comp1")
        comp2 = MockComponent("comp2")
        
        builder = PipelineBuilder("test")\
            .add_component(comp1)\
            .add_component(comp2)\
            .set_context("key", "value")
        
        assert builder.get_stage_count() == 2
        assert builder.get_context("key") == "value"
    
    def test_insert_component(self):
        """Test inserting components at specific positions."""
        comp1 = MockComponent("comp1")
        comp2 = MockComponent("comp2")
        comp3 = MockComponent("insert_me")
        
        builder = PipelineBuilder()\
            .add_component(comp1)\
            .add_component(comp2)\
            .insert_component(1, comp3)
        
        # Should be: comp1, insert_me, comp2
        stages = [c.name for c in builder.components]
        assert stages == ["comp1", "insert_me", "comp2"]
    
    def test_remove_component(self):
        """Test removing components by name."""
        comp1 = MockComponent("comp1")
        comp2 = MockComponent("comp2")
        comp3 = MockComponent("comp3")
        
        builder = PipelineBuilder()\
            .add_components(comp1, comp2, comp3)\
            .remove_component("comp2")
        
        assert builder.get_stage_count() == 2
        assert builder.has_component("comp1")
        assert not builder.has_component("comp2")
        assert builder.has_component("comp3")
    
    def test_replace_component(self):
        """Test replacing components."""
        comp1 = MockComponent("comp1")
        comp2 = MockComponent("comp2")
        comp3 = MockComponent("replacement")
        
        builder = PipelineBuilder()\
            .add_components(comp1, comp2)\
            .replace_component("comp2", comp3)
        
        assert builder.get_stage_count() == 2
        assert builder.has_component("comp1")
        assert not builder.has_component("comp2")
        assert builder.has_component("replacement")
        
        # Check that the actual component was replaced
        assert builder.get_component("replacement") is comp3
    
    def test_get_component(self):
        """Test getting components by name."""
        comp1 = MockComponent("comp1")
        comp2 = MockComponent("comp2")
        
        builder = PipelineBuilder().add_components(comp1, comp2)
        
        assert builder.get_component("comp1") is comp1
        assert builder.get_component("comp2") is comp2
        assert builder.get_component("nonexistent") is None
    
    def test_get_components_by_type(self):
        """Test getting components by type."""
        comp1 = MockComponent("comp1")
        comp2 = MockComponent("comp2")
        
        builder = PipelineBuilder().add_components(comp1, comp2)
        
        mock_components = builder.get_components_by_type(MockComponent)
        assert len(mock_components) == 2
        assert comp1 in mock_components
        assert comp2 in mock_components
        
        # Test with a type that doesn't exist
        other_components = builder.get_components_by_type(str)
        assert len(other_components) == 0
    
    def test_context_management(self):
        """Test context setting and getting."""
        builder = PipelineBuilder()
        
        # Test setting and getting context
        builder.set_context("key1", "value1")
        builder.set_context("key2", 42)
        
        assert builder.get_context("key1") == "value1"
        assert builder.get_context("key2") == 42
        assert builder.get_context("nonexistent") is None
        assert builder.get_context("nonexistent", "default") == "default"
        
        # Test clearing context
        builder.clear_context()
        assert builder.get_context("key1") is None
        assert builder.get_context("key2") is None
    
    def test_validation_empty_pipeline(self):
        """Test validation of empty pipeline."""
        builder = PipelineBuilder()
        
        errors = builder.validate()
        assert "Pipeline has no components" in errors
    
    def test_validation_duplicate_names(self):
        """Test validation catches duplicate component names."""
        comp1 = MockComponent("duplicate")
        comp2 = MockComponent("duplicate")
        
        builder = PipelineBuilder().add_components(comp1, comp2)
        
        errors = builder.validate()
        assert any("Duplicate component names" in error for error in errors)
    
    def test_validation_component_config_errors(self):
        """Test validation catches component configuration errors."""
        comp1 = MockComponent("comp1", config={"invalid": True})
        
        builder = PipelineBuilder().add_component(comp1)
        
        errors = builder.validate()
        assert any("Config marked as invalid" in error for error in errors)
    
    def test_validation_component_validation_exception(self):
        """Test validation handles component validation exceptions."""
        comp1 = MockComponent("comp1")
        # Mock the validate_config method to raise an exception
        comp1.validate_config = Mock(side_effect=Exception("Validation error"))
        
        builder = PipelineBuilder().add_component(comp1)
        
        errors = builder.validate()
        assert any("validation failed" in error for error in errors)
    
    def test_build_valid_pipeline(self):
        """Test building a valid pipeline."""
        comp1 = MockComponent("comp1")
        comp2 = MockComponent("comp2")
        
        builder = PipelineBuilder("test_pipeline").add_components(comp1, comp2)
        
        pipeline = builder.build()
        
        assert isinstance(pipeline, Pipeline)
        assert pipeline.name == "test_pipeline"
        assert len(pipeline.components) == 2
    
    def test_build_invalid_pipeline(self):
        """Test building an invalid pipeline raises error."""
        builder = PipelineBuilder()  # Empty pipeline
        
        with pytest.raises(ValueError, match="Pipeline validation failed"):
            builder.build()
    
    def test_build_and_run(self):
        """Test building and immediately running a pipeline."""
        comp1 = MockComponent("comp1")
        comp2 = MockComponent("comp2")
        
        builder = PipelineBuilder("test").add_components(comp1, comp2)
        
        result = builder.build_and_run("initial_data")
        
        assert result.success
        assert result.data == ["initial_data", "comp1", "comp2"]
        assert comp1.process_called
        assert comp2.process_called
    
    def test_reset(self):
        """Test resetting the builder."""
        comp1 = MockComponent("comp1")
        
        builder = PipelineBuilder("test")\
            .add_component(comp1)\
            .set_context("key", "value")
        
        assert builder.get_stage_count() == 1
        assert builder.get_context("key") == "value"
        
        builder.reset()
        
        assert builder.get_stage_count() == 0
        assert builder.get_context("key") is None
        assert builder.is_empty()
    
    def test_clone(self):
        """Test cloning the builder."""
        comp1 = MockComponent("comp1")
        comp2 = MockComponent("comp2")
        
        original = PipelineBuilder("original")\
            .add_components(comp1, comp2)\
            .set_context("key", "value")
        
        clone = original.clone()
        
        # Should have same configuration
        assert clone.name == "original"
        assert clone.get_stage_count() == 2
        assert clone.get_context("key") == "value"
        assert clone.has_component("comp1")
        assert clone.has_component("comp2")
        
        # But should be independent
        assert clone is not original
        assert clone.components is not original.components
        assert clone._context is not original._context
        
        # Modifying clone shouldn't affect original
        clone.remove_component("comp1")
        assert original.has_component("comp1")
        assert not clone.has_component("comp1")
    
    def test_get_stage_summary(self):
        """Test getting stage summary."""
        comp1 = MockComponent("reader")
        comp2 = MockComponent("processor")
        
        builder = PipelineBuilder().add_components(comp1, comp2)
        
        summary = builder.get_stage_summary()
        
        assert len(summary) == 2
        assert "1. reader (MockComponent)" in summary
        assert "2. processor (MockComponent)" in summary
    
    def test_string_representations(self):
        """Test string and repr methods."""
        # Empty builder
        empty_builder = PipelineBuilder("empty")
        assert "empty" in str(empty_builder)
        assert "empty" in repr(empty_builder)
        
        # Builder with components
        comp1 = MockComponent("comp1")
        comp2 = MockComponent("comp2")
        
        builder = PipelineBuilder("test").add_components(comp1, comp2)
        
        str_repr = str(builder)
        assert "test" in str_repr
        assert "comp1 -> comp2" in str_repr
        
        repr_str = repr(builder)
        assert "test" in repr_str
        assert "stages=2" in repr_str
    
    def test_integration_with_pipeline_execution(self):
        """Test integration with actual pipeline execution."""
        comp1 = MockComponent("reader")
        comp2 = MockComponent("processor") 
        comp3 = MockComponent("writer")
        
        builder = PipelineBuilder("integration_test")\
            .add_component(comp1)\
            .add_component(comp2)\
            .add_component(comp3)
        
        pipeline = builder.build()
        result = pipeline.run("start")
        
        assert result.success
        assert result.data == ["start", "reader", "processor", "writer"]
        
        # Check that all components were called
        assert comp1.process_called
        assert comp2.process_called
        assert comp3.process_called
        
        # Check metadata
        assert result.metadata['pipeline_name'] == "integration_test"
        assert result.metadata['stages_completed'] == 3
        assert result.metadata['total_stages'] == 3
    
    def test_error_handling_in_built_pipeline(self):
        """Test error handling when a component fails."""
        comp1 = MockComponent("good_comp")
        comp2 = MockComponent("failing_comp", should_fail=True)
        comp3 = MockComponent("never_reached")
        
        builder = PipelineBuilder("error_test")\
            .add_components(comp1, comp2, comp3)
        
        result = builder.build_and_run("start")
        
        assert not result.success
        assert len(result.errors) > 0
        assert "failing_comp failed" in str(result.errors)
        
        # First component should have run, third should not
        assert comp1.process_called
        assert comp2.process_called
        assert not comp3.process_called