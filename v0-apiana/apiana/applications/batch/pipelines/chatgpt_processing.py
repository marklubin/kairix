"""
Simple ChatGPT export processing pipeline using local LLM and embeddings.

This module provides a consolidated pipeline that processes ChatGPT exports with:
- Reading ChatGPT export files
- Validating conversation fragments  
- Chunking large conversations
- Local LLM summarization
- Local embedding generation
"""

from apiana.core.pipelines.base import PipelineBuilder, Pipeline
from apiana.core.components import (
    ChatGPTExportReader,
    ValidationTransform,
    ConversationChunkerComponent,
    SummarizerTransform,
    EmbeddingTransform
)
from apiana.core.providers.local import LocalTransformersLLM
from neo4j_graphrag.embeddings.sentence_transformers import SentenceTransformerEmbeddings


def create_chatgpt_processing_pipeline() -> Pipeline:
    """
    Create a simple ChatGPT processing pipeline with local models.
    
    This pipeline:
    1. Reads ChatGPT export JSON files
    2. Validates fragments (min 2 messages)
    3. Chunks conversations that exceed 5000 tokens
    4. Summarizes conversations using local LLM
    5. Generates embeddings using local embedding model
    
    Returns:
        Configured Pipeline ready to run
    """
    # Create local providers with sensible defaults
    local_llm = LocalTransformersLLM(
        model_name="microsoft/DialoGPT-small",
        device="auto"
    )
    
    local_embedder = SentenceTransformerEmbeddings(
        "sentence-transformers/all-MiniLM-L6-v2",
        trust_remote_code=True
    )
    
    # Create components
    reader = ChatGPTExportReader("chatgpt_reader")
    
    validator = ValidationTransform("validator", config={
        "min_messages": 2,
        "require_title": False
    })
    
    chunker = ConversationChunkerComponent("chunker", config={
        "max_tokens": 5000,
        "model_name": "gpt2"
    })
    
    summarizer = SummarizerTransform("summarizer", config={
        "system_prompt": "Summarize this conversation concisely.",
        "user_template": "Conversation:\n\n{conversation}\n\nSummary:"
    })
    summarizer.set_llm_provider(local_llm)
    
    embedder = EmbeddingTransform("embedder")
    embedder.set_embedding_provider(local_embedder)
    
    # Build pipeline using generic PipelineBuilder
    pipeline = PipelineBuilder("chatgpt_processing")\
        .add_component(reader)\
        .add_component(validator)\
        .add_component(chunker)\
        .add_component(summarizer)\
        .add_component(embedder)\
        .build()
    
    return pipeline


def create_simple_chatgpt_pipeline() -> Pipeline:
    """
    Create a simple pipeline that just reads and summarizes without chunking.
    
    Useful for quick processing or when conversations are already short.
    
    Returns:
        Configured Pipeline ready to run
    """
    # Create local LLM with sensible defaults
    local_llm = LocalTransformersLLM(
        model_name="microsoft/DialoGPT-small",
        device="auto"
    )
    
    # Create components
    reader = ChatGPTExportReader("chatgpt_reader")
    
    validator = ValidationTransform("validator", config={
        "min_messages": 1,
        "require_title": False
    })
    
    summarizer = SummarizerTransform("summarizer", config={
        "system_prompt": "Summarize this conversation concisely.",
        "user_template": "Conversation:\n\n{conversation}\n\nSummary:"
    })
    summarizer.set_llm_provider(local_llm)
    
    # Build pipeline
    pipeline = PipelineBuilder("simple_chatgpt")\
        .add_component(reader)\
        .add_component(validator)\
        .add_component(summarizer)\
        .build()
    
    return pipeline


def create_chunking_only_pipeline() -> Pipeline:
    """
    Create a pipeline that only chunks conversations without LLM processing.
    
    Useful for preprocessing large datasets.
    
    Returns:
        Configured Pipeline ready to run
    """
    # Create components
    reader = ChatGPTExportReader("chatgpt_reader")
    
    validator = ValidationTransform("validator", config={
        "min_messages": 1,
        "require_title": False
    })
    
    chunker = ConversationChunkerComponent("chunker", config={
        "max_tokens": 5000,
        "model_name": "gpt2"
    })
    
    # Build pipeline
    pipeline = PipelineBuilder("chunking_only")\
        .add_component(reader)\
        .add_component(validator)\
        .add_component(chunker)\
        .build()
    
    return pipeline