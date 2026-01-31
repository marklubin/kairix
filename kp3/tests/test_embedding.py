"""Tests for embedding processor."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.processors.base import ProcessorGroup
from kp3.processors.embedding import EmbeddingConfig, EmbeddingProcessor
from kp3.services.passages import create_passage


@pytest.fixture
def mock_vllm():
    """Create mock vLLM LLM instance."""
    llm = MagicMock()
    output = MagicMock()
    output.outputs.embedding = [0.1] * 1024
    llm.embed.return_value = [output]
    return llm


@pytest.fixture
def mock_generate_embedding():
    """Mock the generate_embedding function."""
    with patch("kp3.processors.embedding.generate_embedding") as mock:
        mock.return_value = [0.1] * 1024
        yield mock


async def test_embedding_processor_generates_embedding(
    session: AsyncSession,
    mock_generate_embedding: AsyncMock,
):
    """Processor generates embedding for passage."""
    passage = await create_passage(
        session,
        content="Test content for embedding",
        passage_type="raw",
    )
    await session.commit()

    processor = EmbeddingProcessor()

    group = ProcessorGroup(
        passage_ids=[passage.id],
        passages=[passage],
        group_key=str(passage.id),
    )

    config = EmbeddingConfig()
    result = await processor.process(group, config)

    assert result.action == "update"
    assert result.passage_id == passage.id
    assert "embedding_openai" in result.updates
    assert len(result.updates["embedding_openai"]) == 1024

    mock_generate_embedding.assert_called_once_with("Test content for embedding")


async def test_embedding_processor_skips_existing(
    session: AsyncSession,
    mock_generate_embedding: AsyncMock,
):
    """Processor skips passages that already have embeddings."""
    passage = await create_passage(
        session,
        content="Already embedded",
        passage_type="raw",
    )
    passage.embedding_openai = [0.5] * 1024
    await session.commit()

    processor = EmbeddingProcessor()

    group = ProcessorGroup(
        passage_ids=[passage.id],
        passages=[passage],
        group_key=str(passage.id),
    )

    config = EmbeddingConfig()
    result = await processor.process(group, config)

    assert result.action == "pass"
    mock_generate_embedding.assert_not_called()


async def test_embedding_processor_force_regenerate(
    session: AsyncSession,
    mock_generate_embedding: AsyncMock,
):
    """Processor regenerates embedding when force=True."""
    passage = await create_passage(
        session,
        content="Re-embed me",
        passage_type="raw",
    )
    passage.embedding_openai = [0.5] * 1024
    await session.commit()

    processor = EmbeddingProcessor()

    group = ProcessorGroup(
        passage_ids=[passage.id],
        passages=[passage],
        group_key=str(passage.id),
    )

    config = EmbeddingConfig(force=True)
    result = await processor.process(group, config)

    assert result.action == "update"
    mock_generate_embedding.assert_called_once()


async def test_embedding_processor_empty_group(
    mock_generate_embedding: AsyncMock,
):
    """Processor returns pass for empty groups."""
    processor = EmbeddingProcessor()

    group = ProcessorGroup(
        passage_ids=[],
        passages=[],
        group_key="empty",
    )

    config = EmbeddingConfig()
    result = await processor.process(group, config)

    assert result.action == "pass"
    mock_generate_embedding.assert_not_called()


async def test_embedding_batch_generation():
    """Test batch embedding generation."""
    from kp3.processors import embedding

    # Mock the OpenAI client response
    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(index=0, embedding=[0.1] * 1024),
        MagicMock(index=1, embedding=[0.2] * 1024),
        MagicMock(index=2, embedding=[0.3] * 1024),
    ]

    with patch.object(embedding, "_get_openai_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        result = await embedding.generate_embeddings_batch(["text1", "text2", "text3"])

    assert len(result) == 3
    mock_client.embeddings.create.assert_called_once()


async def test_embedding_batch_empty_list():
    """Test batch embedding with empty list."""
    from kp3.processors import embedding

    result = await embedding.generate_embeddings_batch([])

    assert result == []
