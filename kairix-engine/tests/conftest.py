"""Common test fixtures and configuration for kairix-engine tests."""

import pytest


@pytest.fixture
def neo4j_test_url():
    """Fixture providing a test Neo4j database URL."""
    return "bolt://localhost:7687"


@pytest.fixture
def test_embedding_model():
    """Fixture providing a test embedding model name."""
    return "sentence-transformers/all-MiniLM-L6-v2"  # Smaller model for tests