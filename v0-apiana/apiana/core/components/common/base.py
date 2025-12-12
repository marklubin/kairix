"""
Base component interface and result class for the processing pipeline.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, Union, get_origin, get_args
from datetime import datetime


@dataclass
class ComponentResult:
    """Result from component execution."""
    data: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def success(self) -> bool:
        """True if no errors occurred."""
        return len(self.errors) == 0
    
    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
    
    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)


class Component(ABC):
    """
    Base class for all pipeline components.
    
    Components are the building blocks of processing pipelines. Each component
    takes input data, processes it, and returns a ComponentResult with the
    processed data and any metadata or errors.
    
    Components should specify their input and output types for pipeline validation.
    """
    
    # Type specifications - subclasses should override these
    input_types: List[Type] = [Any]  # Types this component can accept as input
    output_types: List[Type] = [Any]  # Types this component produces as output
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
    
    @abstractmethod
    def process(self, input_data: Any) -> ComponentResult:
        """
        Process input data and return result.
        
        Args:
            input_data: The data to process
            
        Returns:
            ComponentResult with processed data, metadata, and any errors
        """
        pass
    
    def validate_input(self, input_data: Any) -> List[str]:
        """
        Validate input data and return list of validation errors.
        
        Args:
            input_data: The data to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        return []
    
    def validate_config(self) -> List[str]:
        """
        Validate component configuration.
        
        Returns:
            List of configuration error messages (empty if valid)
        """
        return []
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', config={self.config})"
    
    def accepts_input_type(self, input_type: Type) -> bool:
        """
        Check if this component can accept the given input type.
        
        Args:
            input_type: The type to check compatibility for
            
        Returns:
            True if the component can accept this type
        """
        return self._is_type_compatible(input_type, self.input_types)
    
    def produces_output_type(self, output_type: Type) -> bool:
        """
        Check if this component produces the given output type.
        
        Args:
            output_type: The type to check for
            
        Returns:
            True if the component produces this type
        """
        return self._is_type_compatible(output_type, self.output_types)
    
    def is_compatible_with(self, other_component: 'Component') -> bool:
        """
        Check if this component's output is compatible with another component's input.
        
        Args:
            other_component: The component to check compatibility with
            
        Returns:
            True if output types are compatible with the other component's input types
        """
        # Check if any of our output types are compatible with any of their input types
        for output_type in self.output_types:
            for input_type in other_component.input_types:
                if self._is_type_compatible(output_type, [input_type]):
                    return True
        return False
    
    @staticmethod
    def _is_type_compatible(check_type: Type, allowed_types: List[Type]) -> bool:
        """
        Check if a type is compatible with any type in the allowed list.
        
        This handles:
        - Exact type matches
        - Subclass relationships
        - Union types
        - Any type (accepts everything)
        - List types with element compatibility
        """
        # Any accepts everything
        if Any in allowed_types or check_type is Any:
            return True
            
        for allowed_type in allowed_types:
            # Exact match
            if check_type == allowed_type:
                return True
                
            # Handle None/Optional
            if check_type is type(None) and allowed_type is type(None):
                return True
                
            # Subclass relationship
            try:
                if isinstance(check_type, type) and isinstance(allowed_type, type):
                    if issubclass(check_type, allowed_type):
                        return True
                    if issubclass(allowed_type, check_type):
                        return True
            except TypeError:
                # Not a class type, continue
                pass
            
            # Handle Union types (e.g., Union[str, int])
            if get_origin(allowed_type) is Union:
                union_args = get_args(allowed_type)
                if Component._is_type_compatible(check_type, list(union_args)):
                    return True
            
            if get_origin(check_type) is Union:
                union_args = get_args(check_type)
                if any(Component._is_type_compatible(arg, [allowed_type]) for arg in union_args):
                    return True
            
            # Handle List types (e.g., List[str])
            if get_origin(allowed_type) is list and get_origin(check_type) is list:
                allowed_args = get_args(allowed_type)
                check_args = get_args(check_type)
                if allowed_args and check_args:
                    # For List types, the element types must be compatible
                    if Component._is_type_compatible(check_args[0], [allowed_args[0]]):
                        return True
                elif not allowed_args and not check_args:
                    # Both are just List without type args
                    return True
        
        return False