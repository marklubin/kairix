import logging
from typing import Any

from kairix_core.types import SourceDocument
from kairix_core.util.environment import get_or_raise
from neomodel import config as neomodel_config
from neomodel import db
from semchunk import chunkerify
from sentence_transformers import SentenceTransformer
from transformers import pipeline

from kairix_offline.processing.gpt_loader import load_sources_from_gpt_export
from kairix_offline.processing.summary_memory_synth import SummaryMemorySynth

__all__ = ["initialize_processing", "load_sources_from_gpt_export", "synth_memories"]

logger = logging.getLogger("kairix_offline")

# Global variables that will be initialized
summary_memory_synthezier: SummaryMemorySynth | None = None
summarizer_llm: Any | None = None
summarizer_batch_size: int | None = None
summarizer_max_length: int | None = None
_initialized = False


def load_llm(model, device):
    return pipeline(
        "summarization",
        model=model,
        device_map=device,
        torch_dtype="auto",
        pad_token_id=2,
        model_kwargs={"load_in_4bit": True})


def initialize_processing():
    """Initialize the processing environment including database and models.

    This must be called before using synth_memories() function.
    """
    global \
        summary_memory_synthezier, \
        summarizer_llm, \
        summarizer_batch_size, \
        summarizer_max_length, \
        _initialized

    if _initialized:
        logger.info("Processing environment already initialized.")
        return

    logger.info("Initializing Neo4J database.")
    neomodel_config.DATABASE_URL = get_or_raise("NEO4J_URL")
    SourceDocument(
        uid="1", source_label="smoke-test", source_type="none", content="test"
    ).create_or_update()
    db.install_all_labels()

    # Load configuration
    summarizer_model = get_or_raise("KAIRIX_SUMMARIZER_MODEL")
    summarizer_device = get_or_raise("KAIRIX_SUMMARIZER_MODEL_DEVICE")
    summarizer_batch_size = int(get_or_raise("KAIRIX_SUMMARIZER_BATCH_SIZE"))
    summarizer_max_length = int(get_or_raise("KAIRIX_SUMMARIZER_MAX_LENGTH"))

    # Initialize LLM
    summarizer_llm = load_llm(summarizer_model, summarizer_device)

    if summarizer_llm.tokenizer is None:
        raise Exception(f"No tokenizer found for model - {summarizer_model}")

    # Initialize chunker
    chunk_size = int(get_or_raise("KAIRIX_CHUNK_SIZE"))
    chunker = chunkerify(summarizer_llm.tokenizer, chunk_size)

    # Initialize embedder
    embedding_model = get_or_raise("KAIRIX_EMBEDDER_MODEL")
    embedding_device = get_or_raise("KAIRIX_EMBEDDER_DEVICE")
    embedidng_batch_size = int(get_or_raise("KAIRIX_EMBEDDING_BATCH_SIZE"))
    embedding_transformer = SentenceTransformer(
        embedding_model, device=embedding_device
    )

    # Create a wrapper function for encoding with custom parameters
    original_encode = embedding_transformer.encode

    def encode_with_params(*args, **kwargs):
        # Merge our default params with any passed kwargs
        kwargs["batch_size"] = kwargs.get("batch_size", embedidng_batch_size)
        kwargs["show_progress_bar"] = kwargs.get("show_progress_bar", True)
        return original_encode(*args, **kwargs)

    embedding_transformer.encode = encode_with_params  # type: ignore[method-assign]

    # Initialize synthesizer
    summary_memory_synthezier = SummaryMemorySynth(
        chunker=chunker, embedder=embedding_transformer, generator=summarizer_llm
    )

    _initialized = True
    logger.info("Processing environment initialized successfully.")


def llm_gen_factory(user_prompt):
    """Factory function for LLM generation. Requires initialize_processing() to be called first."""
    if not _initialized:
        raise RuntimeError(
            "Processing environment not initialized. Call initialize_processing() first."
        )
    assert summarizer_llm is not None
    assert summarizer_batch_size is not None
    assert summarizer_max_length is not None
    return summarizer_llm(
        user_prompt, batch_size=summarizer_batch_size, max_length=summarizer_max_length
    )


def synth_memories(agent_name, run_id):
    """Synthesize memories for an agent. Requires initialize_processing() to be called first."""
    if not _initialized:
        raise RuntimeError(
            "Processing environment not initialized. Call initialize_processing() first."
        )
    assert summary_memory_synthezier is not None
    return summary_memory_synthezier.synthesize_memories(agent_name, run_id)
