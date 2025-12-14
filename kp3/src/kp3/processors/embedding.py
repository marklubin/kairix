"""Embedding processor using Ollama qwen3-embedding."""

import ollama

from kp3.config import get_settings
from kp3.processors.base import Processor, ProcessorGroup, ProcessorResult


class EmbeddingProcessor(Processor):
    """Processor that generates embeddings for passages using Ollama."""

    def __init__(self, client: ollama.AsyncClient | None = None):
        settings = get_settings()
        self._client = client or ollama.AsyncClient(host=settings.ollama_host)
        self._model = settings.ollama_embedding_model

    async def process(
        self,
        group: ProcessorGroup,
        config: dict,
    ) -> ProcessorResult:
        """Generate embeddings for passages in the group.

        For embedding, we update each passage in place rather than creating new ones.
        This processor expects single-passage groups (one passage per group).

        Config options:
        - model: Override default embedding model
        """
        model = config.get("model", self._model)

        if not group.passages:
            return ProcessorResult(action="pass")

        # For embedding processor, we expect single passages per group
        # and update them in place
        passage = group.passages[0]

        # Skip if already has embedding
        if passage.embedding_qwen3 is not None and not config.get("force", False):
            return ProcessorResult(action="pass")

        # Generate embedding
        embedding = await self._generate_embedding(passage.content, model)

        return ProcessorResult(
            action="update",
            passage_id=passage.id,
            updates={"embedding_qwen3": embedding},
        )

    async def _generate_embedding(self, text: str, model: str) -> list[float]:
        """Generate embedding vector for text."""
        response = await self._client.embed(model=model, input=text)
        return response.embeddings[0]

    @property
    def processor_type(self) -> str:
        return "embedding"


async def generate_embedding(text: str, model: str | None = None) -> list[float]:
    """Standalone function to generate a single embedding."""
    settings = get_settings()
    client = ollama.AsyncClient(host=settings.ollama_host)
    model = model or settings.ollama_embedding_model

    response = await client.embed(model=model, input=text)
    return response.embeddings[0]


async def generate_embeddings_batch(
    texts: list[str],
    model: str | None = None,
) -> list[list[float]]:
    """Generate embeddings for multiple texts."""
    settings = get_settings()
    client = ollama.AsyncClient(host=settings.ollama_host)
    model = model or settings.ollama_embedding_model

    response = await client.embed(model=model, input=texts)
    return response.embeddings
