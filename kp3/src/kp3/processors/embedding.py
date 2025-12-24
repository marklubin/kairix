"""Embedding processor using Ollama qwen3-embedding."""

from dataclasses import dataclass

import ollama

from kp3.config import get_settings
from kp3.processors.base import Processor, ProcessorGroup, ProcessorResult


@dataclass
class EmbeddingConfig:
    """Configuration for embedding processor."""

    model: str | None = None  # None = use default from settings
    force: bool = False  # Re-generate even if embedding exists


class EmbeddingProcessor(Processor[EmbeddingConfig]):
    """Processor that generates embeddings for passages using Ollama."""

    def __init__(self, client: ollama.AsyncClient | None = None) -> None:
        settings = get_settings()
        self._client = client or ollama.AsyncClient(host=settings.ollama_host)
        self._default_model = settings.ollama_embedding_model
        self._embedding_dim = settings.ollama_embedding_dim

    async def process(
        self,
        group: ProcessorGroup,
        config: EmbeddingConfig,
    ) -> ProcessorResult:
        """Generate embeddings for passages in the group.

        For embedding, we update each passage in place rather than creating new ones.
        This processor expects single-passage groups (one passage per group).
        """
        model = config.model or self._default_model

        if not group.passages:
            return ProcessorResult(action="pass")

        # For embedding processor, we expect single passages per group
        # and update them in place
        passage = group.passages[0]

        # Skip if already has embedding
        if passage.embedding_qwen3 is not None and not config.force:
            return ProcessorResult(action="pass")

        # Generate embedding
        embedding = await self._generate_embedding(passage.content, model)

        return ProcessorResult(
            action="update",
            passage_id=passage.id,
            updates={"embedding_qwen3": embedding},
        )

    @classmethod
    def parse_config(cls, raw: dict) -> EmbeddingConfig:
        """Parse raw config dict into EmbeddingConfig."""
        return EmbeddingConfig(
            model=raw.get("model"),
            force=raw.get("force", False),
        )

    async def _generate_embedding(self, text: str, model: str) -> list[float]:
        """Generate embedding vector for text."""
        response = await self._client.embed(model=model, input=text, dimensions=self._embedding_dim)
        return response.embeddings[0]

    @property
    def processor_type(self) -> str:
        return "embedding"


async def generate_embedding(text: str, model: str | None = None) -> list[float]:
    """Standalone function to generate a single embedding."""
    settings = get_settings()
    client = ollama.AsyncClient(host=settings.ollama_host)
    model = model or settings.ollama_embedding_model

    response = await client.embed(model=model, input=text, dimensions=settings.ollama_embedding_dim)
    return response.embeddings[0]


async def generate_embeddings_batch(
    texts: list[str],
    model: str | None = None,
) -> list[list[float]]:
    """Generate embeddings for multiple texts."""
    settings = get_settings()
    client = ollama.AsyncClient(host=settings.ollama_host)
    model = model or settings.ollama_embedding_model

    response = await client.embed(
        model=model, input=texts, dimensions=settings.ollama_embedding_dim
    )
    return response.embeddings
