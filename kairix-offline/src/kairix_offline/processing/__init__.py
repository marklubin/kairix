import logging
import os

from kairix_core.inference_provider import (
    ModelParams,
    get_inference_provider_for_environement,
)
from kairix_core.prompt import summary_system_instruction, summary_user_prompt
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
    quantize = bool(os.getenv("KAIRIX_SUMMARIZER_ENABLE_QUANTIZATION"))

    model_parameters: ModelParams = {
        "model": summarizer_model,
        "use_quantization": quantize,
    }

    return get_inference_provider_for_environement(model_parameters=model_parameters)


def get_inference_parameters():
    tokens = int(get_or_raise("KAIRIX_SUMMARIZER_MAX_TOKENS"))
    temp = float(get_or_raise("KAIRIX_SUMMARIZER_TEMPERATURE"))
    # os.getenv("KAIRIX_SUMMARIZER_USE_SYSTEM_PROMPT")

    return {
        "requested_tokens": tokens,
        "temperature": temp,
        "chat_template": "chatml",
        "system_instruction": summary_system_instruction,
        "user_prompt": summary_user_prompt,
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
    db.install_all_labels()
    SourceDocument(
        uid="1", source_label="smoke-test", source_type="none", content="test"
    ).create_or_update()

    inference_provider = get_summary_inference_provider()

    logger.info(
        "Inference provider initialized of type {}. ", inference_provider.__class__
    )

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
    inference_params = get_inference_parameters()
    summary_memory_synthezier = SummaryMemorySynth(
        chunker=chunker,
        embedder=embedding_transformer,
        inference_provider=inference_provider,
        **inference_params,
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
    shards, failed = summary_memory_synthezier.synthesize_memories(agent_name, run_id)

    return f"""\
    Memory Synthesis Completed!
    ----------------------------
    Agent: {agent_name}
    Run ID: {run_id}
    New Memory Shards Generated: {len(shards)}
    Errors: {len(failed)}
    """
