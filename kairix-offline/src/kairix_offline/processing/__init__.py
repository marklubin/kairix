import logging
import os

from kairix_core.types import SourceDocument
from kairix_core.util.environment import get_or_raise
from neomodel import config as neomodel_config
from neomodel import db
from semchunk import chunkerify
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer

from kairix_offline.processing.gpt_loader import load_sources_from_gpt_export
from kairix_offline.processing.summary_memory_synth import SummaryMemorySynth

__all__ = ["initialize_processing", "load_sources_from_gpt_export", "synth_memories"]

logger = logging.getLogger("kairix_offline")

# Global variables that will be initialized
summary_memory_synthezier: SummaryMemorySynth | None = None
summarizer_batch_size: int | None = None
summarizer_max_length: int | None = None
_initialized = False


def get_summary_inference_provider():
    summarizer_model = get_or_raise("KAIRIX_SUMMARIZER_MODEL")
    quantize = os.getenv("KAIRIX_SUMMARIZER_ENABLE_QUANTIZATION")
    from kairix_core.inference.vllm import VLLMInferenceProvider

    return VLLMInferenceProvider(
        model_parameters={
            "model": summarizer_model,
            "use_quantization": quantize,
        }
    )


def get_inference_parameters():
    tokens = get_or_raise("KAIRIX_SUMMARIZER_MAX_TOKENS")
    temp = get_or_raise("KAIRIX_SUMMARIZER_TEMPERATURE")
    template = get_or_raise("KAIRIX_SUMMARIZER_TEMPLATE")
    instruction = get_or_raise("KAIRIX_SUMMARIZER_INSTRUCTION")
    user_prompt = get_or_raise("KAIRIX_SUMMARIZER_USER_PROMPT")

    return {
        "requested_tokens": tokens,
        "temperature": temp,
        "chat_template": template,
        "system_instruction": instruction,
        "user_prompt": user_prompt,
    }


def initialize_processing():
    """Initialize the processing environment including database and models.

    This must be called before using synth_memories() function.
    """
    global \
        summary_memory_synthezier, \
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

    inference_provider = get_summary_inference_provider()

    # Initialize chunker
    chunk_size = int(get_or_raise("KAIRIX_CHUNK_SIZE"))
    chunker = chunkerify(AutoTokenizer.from_pretrained("gpt2"), chunk_size)

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
        chunker=chunker,
        embedder=embedding_transformer,
        inference_provider=inference_provider,
    )

    _initialized = True
    logger.info("Processing environment initialized successfully.")


def synth_memories(agent_name, run_id):
    """Synthesize memories for an agent. Requires initialize_processing() to be called first."""
    if not _initialized:
        raise RuntimeError(
            "Processing environment not initialized. Call initialize_processing() first."
        )
    assert summary_memory_synthezier is not None
    return summary_memory_synthezier.synthesize_memories(agent_name, run_id)
