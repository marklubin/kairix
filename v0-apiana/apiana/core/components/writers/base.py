"""
Base writer interface for components that write data to external destinations.
"""

from abc import abstractmethod
from typing import Any

from apiana.core.components.common import Component, ComponentResult


class Writer(Component):
    """Base class for components that write data to external destinations."""
    
    @abstractmethod
    def write(self, data: Any, destination: str) -> ComponentResult:
        """Write data to the specified destination."""
        pass
    
    def process(self, input_data: tuple) -> ComponentResult:
        """Process by writing data to destination. Input should be (data, destination)."""
        data, destination = input_data
        return self.write(data, destination)