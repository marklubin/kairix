"""
Pipeline Discovery System

Automatically discovers and introspects pipeline factory functions
to generate dynamic UI components and configuration forms.
"""

import inspect
from typing import Dict, Any, List, Callable, Optional
from pathlib import Path

from pipelines import get_available_pipelines, get_pipeline_factory, get_pipeline_signature, PipelineMetadata
from apiana.types.configuration import Neo4jConfig


class PipelineDiscovery:
    """
    Discovers and provides metadata about available pipeline factories.
    
    This class automatically finds pipeline factory functions and provides
    the necessary metadata for dynamic UI generation.
    """
    
    def __init__(self):
        """Initialize the pipeline discovery system."""
        self._pipelines = get_available_pipelines()
        self._factories = {}
        self._signatures = {}
        
        # Load factory functions and signatures
        for pipeline_name in self._pipelines.keys():
            try:
                self._factories[pipeline_name] = get_pipeline_factory(pipeline_name)
                self._signatures[pipeline_name] = get_pipeline_signature(pipeline_name)
            except Exception as e:
                print(f"Warning: Could not load pipeline '{pipeline_name}': {e}")
    
    def get_pipeline_names(self) -> List[str]:
        """Get list of all available pipeline names."""
        return list(self._pipelines.keys())
    
    def get_pipeline_metadata(self, pipeline_name: str) -> PipelineMetadata:
        """Get metadata for a specific pipeline."""
        return self._pipelines[pipeline_name]
    
    def get_pipeline_factory(self, pipeline_name: str) -> Callable:
        """Get the factory function for a pipeline."""
        return self._factories[pipeline_name]
    
    def get_pipeline_signature(self, pipeline_name: str) -> inspect.Signature:
        """Get the function signature for a pipeline factory."""
        return self._signatures[pipeline_name]
    
    def get_pipeline_parameters(self, pipeline_name: str) -> Dict[str, Any]:
        """
        Get detailed parameter information for a pipeline.
        
        Returns:
            Dictionary with parameter details for UI generation
        """
        metadata = self._pipelines[pipeline_name]
        signature = self._signatures[pipeline_name]
        
        parameters = {}
        
        for param_name, param in signature.parameters.items():
            param_info = {
                "name": param_name,
                "type": param.annotation,
                "required": param.default == inspect.Parameter.empty,
                "default": param.default if param.default != inspect.Parameter.empty else None,
                "description": ""
            }
            
            # Get additional info from metadata if available
            if param_name in metadata.input_parameters:
                meta_param = metadata.input_parameters[param_name]
                param_info.update({
                    "ui_type": meta_param.get("type", "string"),
                    "description": meta_param.get("description", ""),
                    "default": meta_param.get("default", param_info["default"]),
                    "accept": meta_param.get("accept", None),
                    "required": meta_param.get("required", param_info["required"])
                })
            else:
                # Infer UI type from annotation
                param_info["ui_type"] = self._infer_ui_type(param.annotation)
            
            parameters[param_name] = param_info
        
        return parameters
    
    def _infer_ui_type(self, annotation) -> str:
        """Infer the UI component type from parameter annotation."""
        if annotation is str or annotation is Optional[str]:
            return "string"
        elif annotation is int or annotation is Optional[int]:
            return "integer"
        elif annotation is float or annotation is Optional[float]:
            return "number"
        elif annotation is bool or annotation is Optional[bool]:
            return "boolean"
        elif annotation is Path or annotation is Optional[Path]:
            return "file"
        elif annotation is Neo4jConfig:
            return "neo4j_config"
        elif hasattr(annotation, "__origin__") and annotation.__origin__ is list:
            return "list"
        else:
            return "string"  # Default fallback
    
    def get_pipelines_by_category(self) -> Dict[str, List[str]]:
        """Group pipelines by their categories."""
        categories = {}
        
        for pipeline_name, metadata in self._pipelines.items():
            category = metadata.category
            if category not in categories:
                categories[category] = []
            categories[category].append(pipeline_name)
        
        return categories
    
    def validate_pipeline_inputs(self, pipeline_name: str, inputs: Dict[str, Any]) -> List[str]:
        """
        Validate inputs for a pipeline.
        
        Args:
            pipeline_name: Name of the pipeline
            inputs: Input values to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        parameters = self.get_pipeline_parameters(pipeline_name)
        
        # Check required parameters
        for param_name, param_info in parameters.items():
            if param_info["required"] and param_name not in inputs:
                errors.append(f"Required parameter '{param_name}' is missing")
            elif param_name in inputs:
                # Type validation could be added here
                value = inputs[param_name]
                if param_info["ui_type"] == "file" and not value:
                    errors.append(f"File parameter '{param_name}' cannot be empty")
                elif param_info["ui_type"] == "string" and param_info["required"] and not value:
                    errors.append(f"String parameter '{param_name}' cannot be empty")
        
        return errors
    
    def create_pipeline_instance(self, pipeline_name: str, inputs: Dict[str, Any]):
        """
        Create a pipeline instance with the given inputs.
        
        Args:
            pipeline_name: Name of the pipeline factory
            inputs: Input parameters for the pipeline
            
        Returns:
            Configured Pipeline instance
            
        Raises:
            ValueError: If validation fails or pipeline creation fails
        """
        # Validate inputs
        errors = self.validate_pipeline_inputs(pipeline_name, inputs)
        if errors:
            raise ValueError(f"Input validation failed: {', '.join(errors)}")
        
        # Get factory function
        factory = self._factories[pipeline_name]
        signature = self._signatures[pipeline_name]
        
        # Prepare arguments, matching signature
        kwargs = {}
        for param_name, param in signature.parameters.items():
            if param_name in inputs:
                value = inputs[param_name]
                
                # Type conversion based on parameter annotation
                if param.annotation is Path and isinstance(value, str):
                    kwargs[param_name] = Path(value)
                elif param.annotation is int and isinstance(value, (str, float)):
                    kwargs[param_name] = int(value)
                elif param.annotation is float and isinstance(value, (str, int)):
                    kwargs[param_name] = float(value)
                else:
                    kwargs[param_name] = value
            elif param.default != inspect.Parameter.empty:
                kwargs[param_name] = param.default
        
        # Create pipeline instance
        try:
            return factory(**kwargs)
        except Exception as e:
            raise ValueError(f"Failed to create pipeline: {str(e)}")


# Global discovery instance
_discovery_instance = None


def get_pipeline_discovery() -> PipelineDiscovery:
    """Get the global pipeline discovery instance."""
    global _discovery_instance
    if _discovery_instance is None:
        _discovery_instance = PipelineDiscovery()
    return _discovery_instance