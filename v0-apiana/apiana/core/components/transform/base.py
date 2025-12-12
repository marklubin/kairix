"""
Base processor interface for components that transform data.
"""

from abc import abstractmethod
from typing import Any

from apiana.core.components.common import Component, ComponentResult


class Transform(Component):
    """Base class for components that transform data."""

    @abstractmethod
    def transform(self, data: Any) -> ComponentResult:
        """Transform the input data."""
        pass

    def process(self, input_data: Any) -> ComponentResult:
        """Process by transforming the input data."""
        return self.transform(input_data)
