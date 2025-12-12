"""
Enhanced ChatGPT export processing pipeline with integrated data persistence.

This module provides a comprehensive pipeline that processes ChatGPT exports with:
- Reading ChatGPT export files
- Transparently storing ChatFragments during processing
- Validating conversation fragments
- Chunking large conversations  
- Local LLM summarization
- Local embedding generation
- Storing final memory blocks in agent-specific storage
- Tracking pipeline execution metadata
"""

from typing import Optional
from pathlib import Path

from apiana.core.pipelines.base import PipelineBuilder, Pipeline
from apiana.core.components import (
    ChatGPTExportReader,
    ValidationTransform,
    ConversationChunkerComponent,
    SummarizerTransform,
    EmbeddingTransform
)
from apiana.core.components.writers import (
    ChatFragmentWriter,
    MemoryBlockWriter,
)
from apiana.core.components.managers import PipelineRunManager
from apiana.core.providers.local import LocalTransformersLLM
from apiana.stores import ApplicationStore, AgentMemoryStore
from apiana.types.configuration import Neo4jConfig
from neo4j_graphrag.embeddings.sentence_transformers import SentenceTransformerEmbeddings


def create_chatgpt_processing_pipeline_with_persistence(
    neo4j_config: Neo4jConfig,
    agent_id: str,
    run_name: Optional[str] = None,
    input_file: Optional[Path] = None
) -> Pipeline:
    """
    Create an enhanced ChatGPT processing pipeline with integrated data persistence.
    
    This pipeline provides transparent data storage throughout the processing flow:
    1. Tracks pipeline execution metadata
    2. Reads ChatGPT export JSON files
    3. Stores ChatFragments transparently as they flow through
    4. Validates fragments (min 2 messages)
    5. Chunks conversations that exceed 5000 tokens
    6. Summarizes conversations using local LLM
    7. Generates embeddings using local embedding model
    8. Stores final memory blocks in agent-specific storage
    
    Args:
        neo4j_config: Neo4j database configuration
        agent_id: Unique identifier for the agent (used for memory storage)
        run_name: Optional name for the pipeline run (auto-generated if not provided)
        input_file: Optional input file path for naming the run
        
    Returns:
        Configured Pipeline ready to run with integrated persistence
    """
    # Generate run name if not provided
    if not run_name:
        file_name = input_file.stem if input_file else "unknown"
        run_name = f"ChatGPT Export Processing: {file_name}"
    
    # Create stores
    app_store = ApplicationStore(neo4j_config)
    agent_store = AgentMemoryStore(neo4j_config, agent_id)
    
    # Create local providers with sensible defaults
    local_llm = LocalTransformersLLM(
        model_name="microsoft/DialoGPT-small",
        device="auto"
    )
    
    local_embedder = SentenceTransformerEmbeddings(
        "sentence-transformers/all-MiniLM-L6-v2",
        trust_remote_code=True
    )
    
    # Create pipeline manager for execution tracking
    pipeline_manager = PipelineRunManager(
        store=app_store,
        run_name=run_name,
        config={"agent_id": agent_id, "input_file": str(input_file) if input_file else None},
        auto_link_fragments=True
    )
    
    # Create processing components
    reader = ChatGPTExportReader("chatgpt_reader")
    
    # ChatFragment writer for transparent storage during processing
    fragment_writer = ChatFragmentWriter(
        store=app_store,
        tags=["chatgpt_export", "raw", agent_id],
        name="fragment_persister"
    )
    
    validator = ValidationTransform(
        name="validator",
        config={"min_messages": 2}
    )
    
    chunker = ConversationChunkerComponent(
        name="chunker",
        config={"max_tokens": 5000}
    )
    
    summarizer = SummarizerTransform(
        name="summarizer",
        llm_provider=local_llm,
        config={"max_length": 150}
    )
    
    embedder = EmbeddingTransform(
        name="embedder",
        embedding_provider=local_embedder
    )
    
    # Memory block writer for final agent memory storage
    memory_writer = MemoryBlockWriter(
        store=agent_store,
        agent_id=agent_id,
        tags=["conversation", "chatgpt_export", "processed"],
        name="memory_persister"
    )
    
    # Build the pipeline with integrated persistence
    pipeline = (
        PipelineBuilder("ChatGPT Processing with Persistence")
        .add_component(pipeline_manager)      # Start tracking
        .add_component(reader)                # Read ChatGPT export
        .add_component(fragment_writer)       # Store raw ChatFragments
        .add_component(validator)             # Validate fragments
        .add_component(chunker)               # Chunk large conversations
        .add_component(summarizer)            # Summarize with local LLM
        .add_component(embedder)              # Generate embeddings
        .add_component(memory_writer)         # Store final memories
        .build()
    )
    
    return pipeline


def create_simple_chatgpt_pipeline_with_fragment_storage(
    neo4j_config: Neo4jConfig,
    run_name: Optional[str] = None
) -> Pipeline:
    """
    Create a simpler ChatGPT processing pipeline that only stores ChatFragments.
    
    This pipeline:
    1. Tracks pipeline execution
    2. Reads ChatGPT export JSON files
    3. Stores ChatFragments transparently
    4. Validates and chunks conversations
    
    Args:
        neo4j_config: Neo4j database configuration
        run_name: Optional name for the pipeline run
        
    Returns:
        Configured Pipeline for basic processing with fragment storage
    """
    run_name = run_name or "Simple ChatGPT Fragment Processing"
    
    # Create application store
    app_store = ApplicationStore(neo4j_config)
    
    # Create pipeline manager
    pipeline_manager = PipelineRunManager(
        store=app_store,
        run_name=run_name,
        auto_link_fragments=True
    )
    
    # Create components
    reader = ChatGPTExportReader("chatgpt_reader")
    
    fragment_writer = ChatFragmentWriter(
        store=app_store,
        tags=["chatgpt_export", "simple_processing"],
        name="fragment_storage"
    )
    
    validator = ValidationTransform(
        name="validator",
        config={"min_messages": 2}
    )
    
    chunker = ConversationChunkerComponent(
        name="chunker", 
        config={"max_tokens": 5000}
    )
    
    # Build simple pipeline
    pipeline = (
        PipelineBuilder("Simple ChatGPT Fragment Processing")
        .add_component(pipeline_manager)
        .add_component(reader)
        .add_component(fragment_writer)
        .add_component(validator)
        .add_component(chunker)
        .build()
    )
    
    return pipeline


def create_memory_only_pipeline(
    neo4j_config: Neo4jConfig,
    agent_id: str,
    run_name: Optional[str] = None
) -> Pipeline:
    """
    Create a pipeline that processes existing ChatFragments into agent memories.
    
    This pipeline is useful for post-processing already stored ChatFragments:
    1. Reads ChatFragments from application store
    2. Summarizes with local LLM
    3. Generates embeddings
    4. Stores as agent memories
    
    Args:
        neo4j_config: Neo4j database configuration
        agent_id: Agent identifier for memory storage
        run_name: Optional name for the pipeline run
        
    Returns:
        Pipeline for converting ChatFragments to agent memories
    """
    run_name = run_name or f"Memory Generation for Agent: {agent_id}"
    
    # Create stores
    app_store = ApplicationStore(neo4j_config)
    agent_store = AgentMemoryStore(neo4j_config, agent_id)
    
    # Create providers
    local_llm = LocalTransformersLLM(
        model_name="microsoft/DialoGPT-small",
        device="auto"
    )
    
    local_embedder = SentenceTransformerEmbeddings(
        "sentence-transformers/all-MiniLM-L6-v2",
        trust_remote_code=True
    )
    
    # Create pipeline manager
    pipeline_manager = PipelineRunManager(
        store=app_store,
        run_name=run_name,
        config={"agent_id": agent_id, "mode": "memory_generation"}
    )
    
    # Create processing components
    summarizer = SummarizerTransform(
        name="summarizer",
        llm_provider=local_llm,
        config={"max_length": 150}
    )
    
    embedder = EmbeddingTransform(
        name="embedder", 
        embedding_provider=local_embedder
    )
    
    memory_writer = MemoryBlockWriter(
        store=agent_store,
        agent_id=agent_id,
        tags=["conversation", "processed", "memory_generation"],
        name="memory_writer"
    )
    
    # Build memory processing pipeline
    pipeline = (
        PipelineBuilder("ChatFragment to Memory Processing")
        .add_component(pipeline_manager)
        .add_component(summarizer)
        .add_component(embedder)
        .add_component(memory_writer)
        .build()
    )
    
    return pipeline