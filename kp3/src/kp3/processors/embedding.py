"""Embedding processor using vLLM in-process."""

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from kp3.config import get_settings
from kp3.processors.base import Processor, ProcessorGroup, ProcessorResult

if TYPE_CHECKING:
    from vllm import LLM

logger = logging.getLogger(__name__)

# Singleton LLM instance (model loading is expensive)
_llm_instance: "LLM | None" = None
_llm_lock = asyncio.Lock()


def _create_llm() -> "LLM":
    """Create the vLLM embedding model instance (synchronous)."""
    from vllm import LLM

    settings = get_settings()
    logger.info("Loading vLLM embedding model: %s", settings.vllm_embedding_model)

    llm = LLM(
        model=settings.vllm_embedding_model,
        runner="pooling",
        gpu_memory_utilization=settings.vllm_gpu_memory_utilization,
        enforce_eager=settings.vllm_enforce_eager,
        trust_remote_code=True,  # Required for some embedding models
    )
    logger.info("vLLM embedding model loaded successfully")
    return llm


async def _get_llm() -> "LLM":
    """Get or create the singleton LLM instance."""
    global _llm_instance
    async with _llm_lock:
        if _llm_instance is None:
            # Load model in thread pool to avoid blocking event loop
            _llm_instance = await asyncio.to_thread(_create_llm)
        return _llm_instance


def _embed_sync(llm: "LLM", texts: list[str], dim: int) -> list[list[float]]:
    """Synchronous embedding generation with MRL truncation."""
    outputs = llm.embed(texts)
    # Truncate to configured dimension (MRL allows this without quality loss)
    return [output.outputs.embedding[:dim] for output in outputs]


@dataclass
class EmbeddingConfig:
    """Configuration for embedding processor."""

    model: str | None = None  # Ignored - uses singleton model
    force: bool = False  # Re-generate even if embedding exists


class EmbeddingProcessor(Processor[EmbeddingConfig]):
    """Processor that generates embeddings for passages using vLLM."""

    async def process(
        self,
        group: ProcessorGroup,
        config: EmbeddingConfig,
    ) -> ProcessorResult:
        """Generate embeddings for passages in the group.

        For embedding, we update each passage in place rather than creating new ones.
        This processor expects single-passage groups (one passage per group).
        """
        if not group.passages:
            return ProcessorResult(action="pass")

        # For embedding processor, we expect single passages per group
        # and update them in place
        passage = group.passages[0]

        # Skip if already has embedding
        if passage.embedding_qwen3 is not None and not config.force:
            return ProcessorResult(action="pass")

        # Generate embedding
        embedding = await generate_embedding(passage.content)

        return ProcessorResult(
            action="update",
            passage_id=passage.id,
            updates={"embedding_qwen3": embedding},
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
    """Standalone function to generate a single embedding.

    Args:
        text: Text to embed.
        model: Ignored - uses the singleton vLLM model.

    Returns:
        Embedding vector as list of floats.
    """
    settings = get_settings()
    llm = await _get_llm()
    embeddings = await asyncio.to_thread(_embed_sync, llm, [text], settings.vllm_embedding_dim)
    return embeddings[0]


async def generate_embeddings_batch(
    texts: list[str],
    model: str | None = None,
) -> list[list[float]]:
    """Generate embeddings for multiple texts.

    Args:
        texts: List of texts to embed.
        model: Ignored - uses the singleton vLLM model.

    Returns:
        List of embedding vectors.
    """
    if not texts:
        return []

    settings = get_settings()
    llm = await _get_llm()
    return await asyncio.to_thread(_embed_sync, llm, texts, settings.vllm_embedding_dim)
