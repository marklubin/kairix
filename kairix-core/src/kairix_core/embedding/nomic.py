"""Nomic embedding implementation."""
from typing import List, Union
import numpy as np
from nomic import embed
from .base import EmbeddingModel


class NomicEmbedding(EmbeddingModel):
    def __init__(self, model_name: str = "nomic-embed-text-v1.5", dim: int = 768):
        self.model_name, self.dim = model_name, dim
    
    def encode(self, text: Union[str, List[str]]) -> np.ndarray:
        texts = [text] if isinstance(text, str) else text
        return np.array(embed.text(texts=texts, model=self.model_name, 
                                   task_type='search_document', dimensionality=self.dim,
                                   inference_mode='local')['embeddings'])
    
    @property
    def embedding_dim(self) -> int:
        return self.dim