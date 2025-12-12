"""
Base reader interface for components that read data from external sources.
"""

from abc import abstractmethod

from apiana.core.components.common import Component, ComponentResult


class Reader(Component):
    """Base class for components that read data from external sources."""
    
    @abstractmethod
    def read(self, source: str) -> ComponentResult:
        """Read data from the specified source."""
        pass
    
    def process(self, input_data: str) -> ComponentResult:
        """Process by reading from the input source path/identifier."""
        return self.read(input_data)