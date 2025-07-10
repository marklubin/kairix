"""Placeholder embedding model for development."""
import numpy as np
from typing import List, Union
from .base import EmbeddingModel


class PlaceholderEmbedding(EmbeddingModel):
    """Placeholder embedding model that returns random vectors."""
    
    def __init__(self, embedding_dim: int = 768):
        self._embedding_dim = embedding_dim
    
    def encode(self, text: Union[str, List[str]]) -> np.ndarray:
        """Return random embeddings for now."""
        if isinstance(text, str):
            return np.random.randn(self._embedding_dim).astype(np.float32)
        else:
            return np.random.randn(len(text), self._embedding_dim).astype(np.float32)
    
    @property
    def embedding_dim(self) -> int:
        """Return the dimension of embeddings."""
        return self._embedding_dim