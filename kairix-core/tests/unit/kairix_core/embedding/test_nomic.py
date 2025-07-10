"""Tests for NomicEmbedding."""
import numpy as np
from unittest.mock import patch
from kairix_core.embedding.nomic import NomicEmbedding


class TestNomicEmbedding:
    @patch('kairix_core.embedding.nomic.embed')
    def test_encode(self, mock_embed):
        mock_embed.text.return_value = {'embeddings': [[0.1, 0.2, 0.3]]}
        result = NomicEmbedding(dim=3).encode("test")
        assert result.shape == (1, 3)
        
    def test_embedding_dim(self):
        assert NomicEmbedding(dim=512).embedding_dim == 512