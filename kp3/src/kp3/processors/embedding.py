"""Embedding processor using OpenAI API."""

import logging
from dataclasses import dataclass

from openai import AsyncOpenAI

from kp3.config import get_settings
from kp3.processors.base import Processor, ProcessorGroup, ProcessorResult

logger = logging.getLogger(__name__)

_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    """Get or create singleton OpenAI client."""
    global _openai_client
    if _openai_client is None:
        settings = get_settings()
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


@dataclass
class EmbeddingConfig:
    """Configuration for embedding processor."""

    model: str | None = None  # Override model (uses config default if None)
    force: bool = False  # Re-generate even if embedding exists


class EmbeddingProcessor(Processor[EmbeddingConfig]):
    """Processor that generates embeddings for passages using OpenAI."""

    async def process(
        self,
        group: ProcessorGroup,
        config: EmbeddingConfig,
    ) -> ProcessorResult:
        """Generate embeddings for passages in the group."""
        if not group.passages:
            return ProcessorResult(action="pass")

        passage = group.passages[0]

        if passage.embedding_openai is not None and not config.force:
            return ProcessorResult(action="pass")

        embedding = await generate_embedding(passage.content)

        return ProcessorResult(
            action="update",
            passage_id=passage.id,
            updates={"embedding_openai": embedding},
        )

    @classmethod
    def parse_config(cls, raw: dict[str, object]) -> EmbeddingConfig:
        """Parse raw config dict into EmbeddingConfig."""
        model_value = raw.get("model")
        return EmbeddingConfig(
            model=model_value if isinstance(model_value, str) else None,
            force=bool(raw.get("force", False)),
        )

    @property
    def processor_type(self) -> str:
        return "embedding"


async def generate_embedding(text: str, model: str | None = None) -> list[float]:
    """Generate a single embedding using OpenAI.

    Args:
        text: Text to embed.
        model: Model to use (defaults to config value).

    Returns:
        Embedding vector as list of floats.
    """
    settings = get_settings()
    client = _get_openai_client()

    response = await client.embeddings.create(
        input=text,
        model=model or settings.openai_embedding_model,
        dimensions=settings.openai_embedding_dim,
    )

    return response.data[0].embedding


async def generate_embeddings_batch(
    texts: list[str],
    model: str | None = None,
) -> list[list[float]]:
    """Generate embeddings for multiple texts.

    Args:
        texts: List of texts to embed.
        model: Model to use (defaults to config value).

    Returns:
        List of embedding vectors.
    """
    if not texts:
        return []

    settings = get_settings()
    client = _get_openai_client()

    response = await client.embeddings.create(
        input=texts,
        model=model or settings.openai_embedding_model,
        dimensions=settings.openai_embedding_dim,
    )

    # Sort by index to maintain order
    sorted_data = sorted(response.data, key=lambda x: x.index)
    return [item.embedding for item in sorted_data]
