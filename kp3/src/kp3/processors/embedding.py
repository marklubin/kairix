"""Embedding processor supporting Ollama and vLLM backends."""

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from kp3.config import get_settings
from kp3.processors.base import Processor, ProcessorGroup, ProcessorResult

if TYPE_CHECKING:
    from vllm import LLM

logger = logging.getLogger(__name__)


class EmbeddingBackend(Protocol):
    """Protocol for embedding backends."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for texts."""
        ...


# =============================================================================
# Ollama Backend
# =============================================================================


class OllamaBackend:
    """Embedding backend using Ollama API."""

    def __init__(self) -> None:
        import ollama

        settings = get_settings()
        self._client = ollama.AsyncClient(host=settings.ollama_host)
        self._model = settings.ollama_embedding_model
        self._dim = settings.ollama_embedding_dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings via Ollama API."""
        response = await self._client.embed(
            model=self._model,
            input=texts,
            dimensions=self._dim,
        )
        return [list(emb) for emb in response.embeddings]


# =============================================================================
# vLLM Backend
# =============================================================================

_vllm_instance: "LLM | None" = None
_vllm_lock = asyncio.Lock()


def _create_vllm() -> "LLM":
    """Create vLLM embedding model instance (synchronous)."""
    from vllm import LLM

    settings = get_settings()
    logger.info("Loading vLLM embedding model: %s", settings.vllm_embedding_model)

    llm = LLM(
        model=settings.vllm_embedding_model,
        task="embed",
        gpu_memory_utilization=settings.vllm_gpu_memory_utilization,
        enforce_eager=settings.vllm_enforce_eager,
        trust_remote_code=True,
    )
    logger.info("vLLM embedding model loaded successfully")
    return llm


class VLLMBackend:
    """Embedding backend using vLLM in-process."""

    def __init__(self) -> None:
        self._dim = get_settings().vllm_embedding_dim

    async def _get_llm(self) -> "LLM":
        """Get or create singleton LLM instance."""
        global _vllm_instance
        async with _vllm_lock:
            if _vllm_instance is None:
                _vllm_instance = await asyncio.to_thread(_create_vllm)
            return _vllm_instance

    def _embed_sync(self, llm: "LLM", texts: list[str]) -> list[list[float]]:
        """Synchronous embedding with MRL truncation."""
        outputs = llm.embed(texts)
        return [output.outputs.embedding[: self._dim] for output in outputs]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings via vLLM."""
        llm = await self._get_llm()
        return await asyncio.to_thread(self._embed_sync, llm, texts)


# =============================================================================
# Backend Selection
# =============================================================================

_backend_instance: EmbeddingBackend | None = None
_backend_lock = asyncio.Lock()


async def _get_backend() -> EmbeddingBackend:
    """Get or create the embedding backend based on config."""
    global _backend_instance
    async with _backend_lock:
        if _backend_instance is None:
            settings = get_settings()
            if settings.embedding_backend == "vllm":
                logger.info("Using vLLM embedding backend")
                _backend_instance = VLLMBackend()
            else:
                logger.info("Using Ollama embedding backend")
                _backend_instance = OllamaBackend()
        return _backend_instance


# =============================================================================
# Public API
# =============================================================================


@dataclass
class EmbeddingConfig:
    """Configuration for embedding processor."""

    model: str | None = None  # Ignored - uses configured backend
    force: bool = False  # Re-generate even if embedding exists


class EmbeddingProcessor(Processor[EmbeddingConfig]):
    """Processor that generates embeddings for passages."""

    async def process(
        self,
        group: ProcessorGroup,
        config: EmbeddingConfig,
    ) -> ProcessorResult:
        """Generate embeddings for passages in the group."""
        if not group.passages:
            return ProcessorResult(action="pass")

        passage = group.passages[0]

        if passage.embedding_qwen3 is not None and not config.force:
            return ProcessorResult(action="pass")

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
    """Generate a single embedding.

    Args:
        text: Text to embed.
        model: Ignored - uses configured backend.

    Returns:
        Embedding vector as list of floats.
    """
    backend = await _get_backend()
    embeddings = await backend.embed([text])
    return embeddings[0]


async def generate_embeddings_batch(
    texts: list[str],
    model: str | None = None,
) -> list[list[float]]:
    """Generate embeddings for multiple texts.

    Args:
        texts: List of texts to embed.
        model: Ignored - uses configured backend.

    Returns:
        List of embedding vectors.
    """
    if not texts:
        return []

    backend = await _get_backend()
    return await backend.embed(texts)
