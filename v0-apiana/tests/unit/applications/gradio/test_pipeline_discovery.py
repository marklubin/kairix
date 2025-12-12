"""
Unit tests for pipeline discovery system.
"""

import pytest
from unittest.mock import Mock, patch
import inspect

from apiana.applications.gradio.pipeline_discovery import PipelineDiscovery, get_pipeline_discovery
from apiana.types.configuration import Neo4jConfig


class TestPipelineDiscovery:
    """Unit tests for PipelineDiscovery class."""
    
    @patch('apiana.applications.gradio.pipeline_discovery.get_available_pipelines')
    @patch('apiana.applications.gradio.pipeline_discovery.get_pipeline_factory')
    @patch('apiana.applications.gradio.pipeline_discovery.get_pipeline_signature')
    def test_init_loads_pipelines(self, mock_get_signature, mock_get_factory, mock_get_available):
        """Should initialize with available pipelines."""
        # Arrange
        mock_pipelines = {
            "test_pipeline": Mock(name="Test Pipeline", category="Test")
        }
        mock_get_available.return_value = mock_pipelines
        mock_get_factory.return_value = Mock()
        mock_get_signature.return_value = Mock()
        
        # Act
        discovery = PipelineDiscovery()
        
        # Assert
        assert discovery.get_pipeline_names() == ["test_pipeline"]
        mock_get_factory.assert_called_once_with("test_pipeline")
        mock_get_signature.assert_called_once_with("test_pipeline")
    
    @patch('apiana.applications.gradio.pipeline_discovery.get_available_pipelines')
    def test_get_pipeline_names(self, mock_get_available):
        """Should return list of pipeline names."""
        # Arrange
        mock_pipelines = {
            "pipeline1": Mock(),
            "pipeline2": Mock(),
            "pipeline3": Mock()
        }
        mock_get_available.return_value = mock_pipelines
        
        # Act
        discovery = PipelineDiscovery()
        names = discovery.get_pipeline_names()
        
        # Assert
        assert set(names) == {"pipeline1", "pipeline2", "pipeline3"}
    
    @patch('apiana.applications.gradio.pipeline_discovery.get_available_pipelines')
    def test_get_pipeline_metadata(self, mock_get_available):
        """Should return metadata for specific pipeline."""
        # Arrange
        mock_metadata = Mock(name="Test Pipeline")
        mock_pipelines = {"test_pipeline": mock_metadata}
        mock_get_available.return_value = mock_pipelines
        
        # Act
        discovery = PipelineDiscovery()
        metadata = discovery.get_pipeline_metadata("test_pipeline")
        
        # Assert
        assert metadata == mock_metadata
    
    def test_infer_ui_type_string(self):
        """Should infer string UI type from string annotation."""
        discovery = PipelineDiscovery.__new__(PipelineDiscovery)
        
        assert discovery._infer_ui_type(str) == "string"
        assert discovery._infer_ui_type(type(None).__class__.__bases__[0]) == "string"  # Optional[str] fallback
    
    def test_infer_ui_type_integer(self):
        """Should infer integer UI type from int annotation."""
        discovery = PipelineDiscovery.__new__(PipelineDiscovery)
        
        assert discovery._infer_ui_type(int) == "integer"
    
    def test_infer_ui_type_boolean(self):
        """Should infer boolean UI type from bool annotation."""
        discovery = PipelineDiscovery.__new__(PipelineDiscovery)
        
        assert discovery._infer_ui_type(bool) == "boolean"
    
    def test_infer_ui_type_neo4j_config(self):
        """Should infer neo4j_config UI type from Neo4jConfig annotation."""
        discovery = PipelineDiscovery.__new__(PipelineDiscovery)
        
        assert discovery._infer_ui_type(Neo4jConfig) == "neo4j_config"
    
    @patch('apiana.applications.gradio.pipeline_discovery.get_available_pipelines')
    def test_get_pipelines_by_category(self, mock_get_available):
        """Should group pipelines by category."""
        # Arrange
        mock_pipelines = {
            "pipeline1": Mock(category="CategoryA"),
            "pipeline2": Mock(category="CategoryA"),
            "pipeline3": Mock(category="CategoryB")
        }
        mock_get_available.return_value = mock_pipelines
        
        # Act
        discovery = PipelineDiscovery()
        categories = discovery.get_pipelines_by_category()
        
        # Assert
        assert "CategoryA" in categories
        assert "CategoryB" in categories
        assert set(categories["CategoryA"]) == {"pipeline1", "pipeline2"}
        assert categories["CategoryB"] == ["pipeline3"]
    
    @patch('apiana.applications.gradio.pipeline_discovery.get_available_pipelines')
    @patch('apiana.applications.gradio.pipeline_discovery.get_pipeline_signature')
    @patch('apiana.applications.gradio.pipeline_discovery.get_pipeline_factory')
    def test_validate_pipeline_inputs_missing_required(self, mock_get_factory, mock_get_signature, mock_get_available):
        """Should detect missing required parameters."""
        # Arrange
        mock_pipelines = {"test_pipeline": Mock(input_parameters={})}
        mock_get_available.return_value = mock_pipelines
        
        # Mock factory
        mock_get_factory.return_value = Mock()
        
        # Create mock signature with required parameter
        mock_param = Mock()
        mock_param.default = inspect.Parameter.empty
        mock_param.annotation = str
        mock_signature = Mock()
        mock_signature.parameters = {"required_param": mock_param}
        mock_get_signature.return_value = mock_signature
        
        # Act
        discovery = PipelineDiscovery()
        errors = discovery.validate_pipeline_inputs("test_pipeline", {})
        
        # Assert
        assert len(errors) == 1
        assert "required_param" in errors[0]
        assert "missing" in errors[0].lower()
    
    @patch('apiana.applications.gradio.pipeline_discovery.get_available_pipelines')
    @patch('apiana.applications.gradio.pipeline_discovery.get_pipeline_signature')
    @patch('apiana.applications.gradio.pipeline_discovery.get_pipeline_factory')
    def test_validate_pipeline_inputs_valid(self, mock_get_factory, mock_get_signature, mock_get_available):
        """Should pass validation with valid inputs."""
        # Arrange
        mock_pipelines = {"test_pipeline": Mock(input_parameters={})}
        mock_get_available.return_value = mock_pipelines
        
        # Mock factory
        mock_get_factory.return_value = Mock()
        
        # Create mock signature with optional parameter
        mock_param = Mock()
        mock_param.default = "default_value"
        mock_param.annotation = str
        mock_signature = Mock()
        mock_signature.parameters = {"optional_param": mock_param}
        mock_get_signature.return_value = mock_signature
        
        # Act
        discovery = PipelineDiscovery()
        errors = discovery.validate_pipeline_inputs("test_pipeline", {"optional_param": "value"})
        
        # Assert
        assert len(errors) == 0
    
    @patch('apiana.applications.gradio.pipeline_discovery.get_available_pipelines')
    @patch('apiana.applications.gradio.pipeline_discovery.get_pipeline_factory')
    @patch('apiana.applications.gradio.pipeline_discovery.get_pipeline_signature')
    def test_create_pipeline_instance_success(self, mock_get_signature, mock_get_factory, mock_get_available):
        """Should create pipeline instance successfully."""
        # Arrange
        mock_pipelines = {"test_pipeline": Mock(input_parameters={})}
        mock_get_available.return_value = mock_pipelines
        
        mock_factory = Mock()
        mock_pipeline = Mock()
        mock_factory.return_value = mock_pipeline
        mock_get_factory.return_value = mock_factory
        
        mock_param = Mock()
        mock_param.default = "default"
        mock_param.annotation = str
        mock_signature = Mock()
        mock_signature.parameters = {"param": mock_param}
        mock_get_signature.return_value = mock_signature
        
        # Act
        discovery = PipelineDiscovery()
        result = discovery.create_pipeline_instance("test_pipeline", {"param": "value"})
        
        # Assert
        assert result == mock_pipeline
        mock_factory.assert_called_once_with(param="value")
    
    @patch('apiana.applications.gradio.pipeline_discovery.get_available_pipelines')
    @patch('apiana.applications.gradio.pipeline_discovery.get_pipeline_signature')
    @patch('apiana.applications.gradio.pipeline_discovery.get_pipeline_factory')
    def test_create_pipeline_instance_validation_failure(self, mock_get_factory, mock_get_signature, mock_get_available):
        """Should raise ValueError on validation failure."""
        # Arrange
        mock_pipelines = {"test_pipeline": Mock(input_parameters={})}
        mock_get_available.return_value = mock_pipelines
        
        # Mock factory
        mock_get_factory.return_value = Mock()
        
        mock_param = Mock()
        mock_param.default = inspect.Parameter.empty
        mock_param.annotation = str
        mock_signature = Mock()
        mock_signature.parameters = {"required_param": mock_param}
        mock_get_signature.return_value = mock_signature
        
        # Act & Assert
        discovery = PipelineDiscovery()
        with pytest.raises(ValueError, match="Input validation failed"):
            discovery.create_pipeline_instance("test_pipeline", {})


def test_get_pipeline_discovery_singleton():
    """Should return singleton instance."""
    discovery1 = get_pipeline_discovery()
    discovery2 = get_pipeline_discovery()
    
    assert discovery1 is discovery2