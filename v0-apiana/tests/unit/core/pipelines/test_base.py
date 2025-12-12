"""
Unit tests for base pipeline classes.
"""

from unittest.mock import Mock
import time

from apiana.core.pipelines.base import Pipeline, PipelineResult
from apiana.core.components.common import Component, ComponentResult


class MockComponent(Component):
    """Mock component for testing."""
    
    def __init__(self, name: str, should_fail: bool = False, delay: float = 0.0, config: dict = None):
        super().__init__(name, config)
        self.should_fail = should_fail
        self.delay = delay
        self.process_called = False
        self.validate_called = False
    
    def process(self, input_data):
        self.process_called = True
        if self.delay > 0:
            time.sleep(self.delay)
        
        if self.should_fail:
            return ComponentResult(data=None, errors=[f"{self.name} failed"])
        
        return ComponentResult(data=f"{self.name}_processed_{input_data}")
    
    def validate_input(self, input_data):
        self.validate_called = True
        if input_data == "invalid":
            return [f"{self.name} input validation failed"]
        return []
    
    def validate_config(self):
        if self.config.get('invalid'):
            return [f"{self.name} config is invalid"]
        return []


class TestPipelineResult:
    """Test PipelineResult class."""
    
    def test_pipeline_result_creation(self):
        """Test basic PipelineResult creation."""
        result = PipelineResult(success=True, data="test_data")
        assert result.success is True
        assert result.data == "test_data"
        assert result.errors == []
        assert result.warnings == []
        assert result.stage_results == []
        assert result.execution_time_ms == 0.0
        assert result.timestamp is not None
    
    def test_add_error(self):
        """Test adding errors sets success to False."""
        result = PipelineResult(success=True, data="test")
        assert result.success is True
        
        result.add_error("Something went wrong")
        assert result.success is False
        assert "Something went wrong" in result.errors
    
    def test_add_warning(self):
        """Test adding warnings doesn't affect success."""
        result = PipelineResult(success=True, data="test")
        result.add_warning("Warning message")
        assert "Warning message" in result.warnings
        assert result.success is True


class TestPipeline:
    """Test Pipeline class."""
    
    def test_pipeline_creation(self):
        """Test pipeline creation."""
        components = [MockComponent("comp1"), MockComponent("comp2")]
        pipeline = Pipeline("test_pipeline", components)
        
        assert pipeline.name == "test_pipeline"
        assert len(pipeline.components) == 2
        assert pipeline.progress_callback is None
    
    def test_pipeline_validation_empty(self):
        """Test pipeline validation with no components."""
        pipeline = Pipeline("empty", [])
        errors = pipeline.validate()
        assert "no components" in errors[0]
    
    def test_pipeline_validation_invalid_config(self):
        """Test pipeline validation with invalid component config."""
        component = MockComponent("test")
        component.config = {'invalid': True}
        pipeline = Pipeline("test", [component])
        
        errors = pipeline.validate()
        assert len(errors) == 1
        assert "config is invalid" in errors[0]
    
    def test_pipeline_validation_success(self):
        """Test successful pipeline validation."""
        components = [MockComponent("comp1"), MockComponent("comp2")]
        pipeline = Pipeline("test", components)
        
        errors = pipeline.validate()
        assert errors == []
    
    def test_pipeline_run_success(self):
        """Test successful pipeline execution."""
        components = [MockComponent("comp1"), MockComponent("comp2")]
        pipeline = Pipeline("test", components)
        
        result = pipeline.run("initial_data")
        
        assert result.success
        assert result.data == "comp2_processed_comp1_processed_initial_data"
        assert len(result.stage_results) == 2
        assert result.execution_time_ms > 0
        
        # Check that all components were called
        for comp in components:
            assert comp.process_called
            assert comp.validate_called
    
    def test_pipeline_run_validation_failure(self):
        """Test pipeline execution with validation errors."""
        pipeline = Pipeline("test", [])  # Empty pipeline
        result = pipeline.run("data")
        
        assert not result.success
        assert "no components" in result.errors[0]
        assert len(result.stage_results) == 0
    
    def test_pipeline_run_input_validation_failure(self):
        """Test pipeline execution with input validation failure."""
        component = MockComponent("comp1")
        pipeline = Pipeline("test", [component])
        
        result = pipeline.run("invalid")  # This will fail validation
        
        assert not result.success
        assert "input validation" in result.errors[0]
        assert len(result.stage_results) == 0
        assert component.validate_called
        assert not component.process_called
    
    def test_pipeline_run_component_failure(self):
        """Test pipeline execution with component failure."""
        components = [
            MockComponent("comp1"),
            MockComponent("comp2", should_fail=True),
            MockComponent("comp3")  # Should not be called
        ]
        pipeline = Pipeline("test", components)
        
        result = pipeline.run("data")
        
        assert not result.success
        assert "comp2 failed" in result.errors[0]
        assert len(result.stage_results) == 2  # Only comp1 and comp2
        assert components[0].process_called
        assert components[1].process_called
        assert not components[2].process_called
    
    def test_pipeline_run_exception_handling(self):
        """Test pipeline handles component exceptions."""
        component = MockComponent("comp1")
        component.process = Mock(side_effect=Exception("Unexpected error"))
        pipeline = Pipeline("test", [component])
        
        result = pipeline.run("data")
        
        assert not result.success
        assert "failed with exception" in result.errors[0]
        assert "Unexpected error" in result.errors[0]
    
    def test_pipeline_progress_callback(self):
        """Test pipeline progress callback functionality."""
        components = [MockComponent("comp1"), MockComponent("comp2")]
        pipeline = Pipeline("test", components)
        
        # Track progress calls
        progress_calls = []
        def progress_callback(current, total, stage):
            progress_calls.append((current, total, stage))
        
        pipeline.set_progress_callback(progress_callback)
        result = pipeline.run("data")
        
        assert result.success
        assert len(progress_calls) >= 2  # At least one call per component
        
        # Check final call
        final_call = progress_calls[-1]
        assert final_call[0] == final_call[1]  # current == total
        assert final_call[2] == "Complete"
    
    def test_pipeline_progress_callback_on_failure(self):
        """Test progress callback on pipeline failure."""
        components = [MockComponent("comp1", should_fail=True)]
        pipeline = Pipeline("test", components)
        
        progress_calls = []
        def progress_callback(current, total, stage):
            progress_calls.append((current, total, stage))
        
        pipeline.set_progress_callback(progress_callback)
        result = pipeline.run("data")
        
        assert not result.success
        
        # Should have final "Failed" call
        final_call = progress_calls[-1]
        assert final_call[2] == "Failed"
    
    def test_pipeline_metadata_collection(self):
        """Test pipeline collects metadata correctly."""
        components = [
            MockComponent("comp1", delay=0.01),  # Small delay for timing
            MockComponent("comp2", delay=0.01)
        ]
        pipeline = Pipeline("test", components)
        
        result = pipeline.run("data")
        
        assert result.success
        assert 'pipeline_name' in result.metadata
        assert result.metadata['pipeline_name'] == 'test'
        assert result.metadata['stages_completed'] == 2
        assert result.metadata['total_stages'] == 2
        assert 'total_stage_time_ms' in result.metadata
        assert 'overhead_time_ms' in result.metadata
        assert result.metadata['total_stage_time_ms'] >= 0  # Allow for very fast execution
    
    def test_get_stage_info(self):
        """Test getting stage information."""
        components = [
            MockComponent("comp1", {'param1': 'value1'}),
            MockComponent("comp2", {'param2': 'value2'})
        ]
        components[0].config = {'param1': 'value1'}
        components[1].config = {'param2': 'value2'}
        
        pipeline = Pipeline("test", components)
        stage_info = pipeline.get_stage_info()
        
        assert len(stage_info) == 2
        assert stage_info[0]['index'] == 0
        assert stage_info[0]['name'] == 'comp1'
        assert stage_info[0]['type'] == 'MockComponent'
        assert stage_info[0]['config'] == {'param1': 'value1'}
    
    def test_pipeline_string_representations(self):
        """Test string representations of pipeline."""
        components = [MockComponent("comp1"), MockComponent("comp2")]
        pipeline = Pipeline("test_pipeline", components)
        
        str_repr = str(pipeline)
        assert "test_pipeline" in str_repr
        assert "comp1 -> comp2" in str_repr
        
        repr_str = repr(pipeline)
        assert "Pipeline" in repr_str
        assert "test_pipeline" in repr_str
        assert "stages=2" in repr_str