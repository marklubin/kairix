"""
Base chunker interface for components that split data into smaller pieces.
"""

from abc import abstractmethod
from typing import Any

from apiana.core.components.common import ComponentResult
from apiana.core.components.transform.base import Transform


class Chunker(Transform):
    """Base class for components that split data into smaller pieces."""

    @abstractmethod
    def chunk(self, data: Any) -> ComponentResult:
        """Split data into chunks."""
        pass

    def transform(self, data: Any) -> ComponentResult:
        """Transform by chunking the data."""
        return self.chunk(data)
