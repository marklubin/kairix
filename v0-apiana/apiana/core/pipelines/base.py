"""
Base pipeline classes for orchestrating component execution.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime

from apiana.core.components.common import Component, ComponentResult


@dataclass
class PipelineResult:
    """Result from pipeline execution."""
    success: bool
    data: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stage_results: List[ComponentResult] = field(default_factory=list)
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
        self.success = False
    
    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)


class Pipeline:
    """
    A pipeline that executes a sequence of components.
    
    The pipeline manages the flow of data through multiple processing stages,
    handling errors and collecting metadata from each stage.
    """
    
    def __init__(self, name: str, components: List[Component]):
        self.name = name
        self.components = components
        self.progress_callback: Optional[Callable[[int, int, str], None]] = None
    
    def set_progress_callback(self, callback: Callable[[int, int, str], None]) -> None:
        """Set a callback for progress updates. Args: (current_stage, total_stages, stage_name)"""
        self.progress_callback = callback
    
    def validate(self) -> List[str]:
        """Validate the pipeline configuration."""
        errors = []
        
        if not self.components:
            errors.append("Pipeline has no components")
            return errors
        
        # Validate each component
        for i, component in enumerate(self.components):
            config_errors = component.validate_config()
            if config_errors:
                errors.extend([f"Component {i} ({component.name}): {err}" for err in config_errors])
        
        return errors
    
    def run(self, initial_data: Any) -> PipelineResult:
        """
        Execute the pipeline with the given initial data.
        
        Args:
            initial_data: The input data for the first component
            
        Returns:
            PipelineResult with final data and execution metadata
        """
        start_time = time.time()
        
        # Validate pipeline before execution
        validation_errors = self.validate()
        if validation_errors:
            return PipelineResult(
                success=False,
                data=None,
                errors=validation_errors,
                execution_time_ms=(time.time() - start_time) * 1000
            )
        
        result = PipelineResult(success=True, data=initial_data)
        current_data = initial_data
        
        for i, component in enumerate(self.components):
            try:
                # Update progress
                if self.progress_callback:
                    self.progress_callback(i, len(self.components), component.name)
                
                # Validate input for this component
                input_errors = component.validate_input(current_data)
                if input_errors:
                    for error in input_errors:
                        result.add_error(f"Stage {i} ({component.name}) input validation: {error}")
                    break
                
                # Execute component
                component_result = component.process(current_data)
                result.stage_results.append(component_result)
                
                # Check for component errors
                if not component_result.success:
                    for error in component_result.errors:
                        result.add_error(f"Stage {i} ({component.name}): {error}")
                    break
                
                # Add any warnings
                for warning in component_result.warnings:
                    result.add_warning(f"Stage {i} ({component.name}): {warning}")
                
                # Pass data to next stage
                current_data = component_result.data
                
            except Exception as e:
                result.add_error(f"Stage {i} ({component.name}) failed with exception: {e}")
                break
        
        # Finalize result
        result.data = current_data
        result.execution_time_ms = (time.time() - start_time) * 1000
        
        # Calculate metadata
        if result.stage_results:
            total_stage_time = sum(sr.execution_time_ms for sr in result.stage_results)
            result.metadata.update({
                'pipeline_name': self.name,
                'stages_completed': len(result.stage_results),
                'total_stages': len(self.components),
                'total_stage_time_ms': total_stage_time,
                'overhead_time_ms': result.execution_time_ms - total_stage_time
            })
        
        # Final progress update
        if self.progress_callback:
            if result.success:
                self.progress_callback(len(self.components), len(self.components), "Complete")
            else:
                self.progress_callback(len(result.stage_results), len(self.components), "Failed")
        
        return result
    
    def get_stage_info(self) -> List[Dict[str, Any]]:
        """Get information about each stage in the pipeline."""
        return [
            {
                'index': i,
                'name': component.name,
                'type': component.__class__.__name__,
                'config': component.config
            }
            for i, component in enumerate(self.components)
        ]
    
    def __str__(self) -> str:
        stage_names = [c.name for c in self.components]
        return f"Pipeline('{self.name}': {' -> '.join(stage_names)})"
    
    def __repr__(self) -> str:
        return f"Pipeline(name='{self.name}', stages={len(self.components)})"


class ParallelPipeline(Pipeline):
    """
    A pipeline that can execute certain stages in parallel.
    
    This is useful when multiple components can process the same data
    independently (e.g., generating summaries and embeddings).
    """
    
    def __init__(self, name: str, components: List[Component], parallel_stages: List[List[int]] = None):
        super().__init__(name, components)
        self.parallel_stages = parallel_stages or []
    
    def run(self, initial_data: Any) -> PipelineResult:
        """Execute pipeline with parallel stages where specified."""
        # For now, implement as sequential pipeline
        # In a full implementation, this would use threading/asyncio
        # for the parallel stages
        return super().run(initial_data)


class PipelineBuilder:
    """
    Generic pipeline builder for creating processing workflows with a fluent API.
    
    This is a generic interface that works with any Component types and avoids
    coupling to specific domain logic like ChatGPT exports.
    """
    
    def __init__(self, name: str = "pipeline"):
        """
        Initialize a new pipeline builder.
        
        Args:
            name: Name for the pipeline
        """
        self.name = name
        self.components: List[Component] = []
        self._context: Dict[str, Any] = {}
    
    def add_component(self, component: Component, validate_types: bool = True) -> "PipelineBuilder":
        """
        Add a component to the pipeline.
        
        Args:
            component: Any component implementing the Component interface
            validate_types: Whether to validate type compatibility with previous component
            
        Returns:
            Self for chaining
            
        Raises:
            TypeError: If type validation fails
        """
        if validate_types and self.components:
            # Check compatibility with the last component in the pipeline
            last_component = self.components[-1]
            if not last_component.is_compatible_with(component):
                raise TypeError(
                    f"Type mismatch: {last_component.__class__.__name__} "
                    f"(outputs: {[self._format_type_name(t) for t in last_component.output_types]}) "
                    f"is not compatible with {component.__class__.__name__} "
                    f"(inputs: {[self._format_type_name(t) for t in component.input_types]})"
                )
        
        self.components.append(component)
        return self
    
    def add_components(self, *components: Component) -> "PipelineBuilder":
        """
        Add multiple components to the pipeline.
        
        Args:
            *components: Variable number of components
            
        Returns:
            Self for chaining
        """
        self.components.extend(components)
        return self
    
    def insert_component(self, index: int, component: Component, validate_types: bool = True) -> "PipelineBuilder":
        """
        Insert a component at a specific position in the pipeline.
        
        Args:
            index: Position to insert at
            component: Component to insert
            validate_types: Whether to validate type compatibility
            
        Returns:
            Self for chaining
            
        Raises:
            TypeError: If type validation fails
        """
        if validate_types:
            # Check compatibility with previous component (if exists)
            if index > 0 and index <= len(self.components):
                prev_component = self.components[index - 1]
                if not prev_component.is_compatible_with(component):
                    raise TypeError(
                        f"Type mismatch: {prev_component.__class__.__name__} "
                        f"(outputs: {[t.__name__ for t in prev_component.output_types]}) "
                        f"is not compatible with {component.__class__.__name__} "
                        f"(inputs: {[t.__name__ for t in component.input_types]})"
                    )
            
            # Check compatibility with next component (if exists)
            if index < len(self.components):
                next_component = self.components[index]
                if not component.is_compatible_with(next_component):
                    raise TypeError(
                        f"Type mismatch: {component.__class__.__name__} "
                        f"(outputs: {[t.__name__ for t in component.output_types]}) "
                        f"is not compatible with {next_component.__class__.__name__} "
                        f"(inputs: {[t.__name__ for t in next_component.input_types]})"
                    )
        
        self.components.insert(index, component)
        return self
    
    def remove_component(self, name: str) -> "PipelineBuilder":
        """
        Remove a component by name.
        
        Args:
            name: Name of the component to remove
            
        Returns:
            Self for chaining
        """
        self.components = [c for c in self.components if c.name != name]
        return self
    
    def replace_component(self, name: str, new_component: Component) -> "PipelineBuilder":
        """
        Replace a component with a new one.
        
        Args:
            name: Name of the component to replace
            new_component: New component to use
            
        Returns:
            Self for chaining
        """
        for i, component in enumerate(self.components):
            if component.name == name:
                self.components[i] = new_component
                break
        return self
    
    def set_context(self, key: str, value: Any) -> "PipelineBuilder":
        """
        Set a context value that can be used by components.
        
        Args:
            key: Context key
            value: Context value
            
        Returns:
            Self for chaining
        """
        self._context[key] = value
        return self
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """
        Get a context value.
        
        Args:
            key: Context key
            default: Default value if key not found
            
        Returns:
            Context value or default
        """
        return self._context.get(key, default)
    
    def clear_context(self) -> "PipelineBuilder":
        """
        Clear all context values.
        
        Returns:
            Self for chaining
        """
        self._context.clear()
        return self
    
    def get_component(self, name: str) -> Optional[Component]:
        """
        Get a component by name.
        
        Args:
            name: Component name
            
        Returns:
            Component if found, None otherwise
        """
        for component in self.components:
            if component.name == name:
                return component
        return None
    
    def get_components_by_type(self, component_type: type) -> List[Component]:
        """
        Get all components of a specific type.
        
        Args:
            component_type: Type to filter by
            
        Returns:
            List of components matching the type
        """
        return [c for c in self.components if isinstance(c, component_type)]
    
    def validate(self) -> List[str]:
        """
        Validate the pipeline configuration.
        
        Returns:
            List of validation errors
        """
        errors = []
        
        if not self.components:
            errors.append("Pipeline has no components")
            return errors
        
        # Check for duplicate names
        names = [c.name for c in self.components]
        duplicates = set([name for name in names if names.count(name) > 1])
        if duplicates:
            errors.append(f"Duplicate component names: {', '.join(duplicates)}")
        
        # Validate each component
        for i, component in enumerate(self.components):
            try:
                config_errors = component.validate_config()
                if config_errors:
                    errors.extend([f"Component {i} ({component.name}): {err}" for err in config_errors])
            except Exception as e:
                errors.append(f"Component {i} ({component.name}) validation failed: {e}")
        
        # Validate type compatibility chain
        type_errors = self.validate_type_chain()
        errors.extend(type_errors)
        
        return errors
    
    def validate_type_chain(self) -> List[str]:
        """
        Validate that component types are compatible in sequence.
        
        Returns:
            List of type compatibility errors
        """
        errors = []
        
        if len(self.components) < 2:
            return errors  # Nothing to validate
        
        for i in range(len(self.components) - 1):
            current = self.components[i]
            next_comp = self.components[i + 1]
            
            if not current.is_compatible_with(next_comp):
                errors.append(
                    f"Type incompatibility between components {i} and {i+1}: "
                    f"{current.__class__.__name__} "
                    f"(outputs: {[self._format_type_name(t) for t in current.output_types]}) "
                    f"-> {next_comp.__class__.__name__} "
                    f"(inputs: {[self._format_type_name(t) for t in next_comp.input_types]})"
                )
        
        return errors
    
    @staticmethod
    def _format_type_name(type_obj) -> str:
        """Format a type object into a readable string."""
        from typing import get_origin, get_args
        
        if hasattr(type_obj, '__name__'):
            name = type_obj.__name__
        else:
            name = str(type_obj)
        
        # Handle generic types like List[ChatFragment]
        origin = get_origin(type_obj)
        args = get_args(type_obj)
        
        if origin is not None:
            origin_name = origin.__name__ if hasattr(origin, '__name__') else str(origin)
            if args:
                arg_names = [PipelineBuilder._format_type_name(arg) for arg in args]
                return f"{origin_name}[{', '.join(arg_names)}]"
            else:
                return origin_name
        
        return name
    
    def build(self) -> Pipeline:
        """
        Build the pipeline from the configured components.
        
        Returns:
            Pipeline instance ready to run
            
        Raises:
            ValueError: If pipeline configuration is invalid
        """
        validation_errors = self.validate()
        if validation_errors:
            raise ValueError(f"Pipeline validation failed: {'; '.join(validation_errors)}")
        
        if not self.components:
            raise ValueError("Pipeline must have at least one component")
        
        return Pipeline(self.name, self.components.copy())
    
    def build_and_run(self, input_data: Any) -> PipelineResult:
        """
        Build the pipeline and immediately run it.
        
        Args:
            input_data: Initial data for the pipeline
            
        Returns:
            PipelineResult with execution results
        """
        pipeline = self.build()
        return pipeline.run(input_data)
    
    def reset(self) -> "PipelineBuilder":
        """
        Reset the builder to start fresh.
        
        Returns:
            Self for chaining
        """
        self.components.clear()
        self._context.clear()
        return self
    
    def clone(self) -> "PipelineBuilder":
        """
        Create a copy of this builder.
        
        Returns:
            New PipelineBuilder with the same configuration
        """
        new_builder = PipelineBuilder(self.name)
        new_builder.components = self.components.copy()
        new_builder._context = self._context.copy()
        return new_builder
    
    def get_stage_summary(self) -> List[str]:
        """
        Get a summary of the current pipeline stages.
        
        Returns:
            List of stage descriptions
        """
        return [
            f"{i + 1}. {comp.name} ({comp.__class__.__name__})"
            for i, comp in enumerate(self.components)
        ]
    
    def get_stage_count(self) -> int:
        """
        Get the number of stages in the pipeline.
        
        Returns:
            Number of components
        """
        return len(self.components)
    
    def is_empty(self) -> bool:
        """
        Check if the pipeline is empty.
        
        Returns:
            True if no components are configured
        """
        return len(self.components) == 0
    
    def has_component(self, name: str) -> bool:
        """
        Check if a component with the given name exists.
        
        Args:
            name: Component name to check
            
        Returns:
            True if component exists
        """
        return any(c.name == name for c in self.components)
    
    def __str__(self) -> str:
        if not self.components:
            return f"PipelineBuilder('{self.name}': empty)"
        
        stages = " -> ".join([comp.name for comp in self.components])
        return f"PipelineBuilder('{self.name}': {stages})"
    
    def __repr__(self) -> str:
        return f"PipelineBuilder(name='{self.name}', stages={len(self.components)})"