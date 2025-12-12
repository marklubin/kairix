"""
Base interfaces for LLM and embedding providers.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    model: str
    usage: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMProvider(ABC):
    """Base interface for LLM providers."""
    
    @abstractmethod
    def invoke(self, prompt: str, system_instruction: Optional[str] = None, **kwargs) -> LLMResponse:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model."""
        pass


class EmbeddingProvider(ABC):
    """Base interface for embedding providers."""
    
    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Generate embeddings for a text query."""
        pass
    
    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple documents."""
        pass
    
    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embeddings."""
        pass