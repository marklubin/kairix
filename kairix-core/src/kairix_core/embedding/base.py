"""Base embedding interface."""
from abc import ABC, abstractmethod
from typing import List, Union
import numpy as np


class EmbeddingModel(ABC):
    """Abstract base class for embedding models."""
    
    @abstractmethod
    def encode(self, text: Union[str, List[str]]) -> np.ndarray:
        """Encode text into embeddings."""
        pass
    
    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        """Return the dimension of embeddings."""
        pass