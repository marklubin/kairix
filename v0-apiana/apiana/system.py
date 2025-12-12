"""
Global System Dependencies

This module initializes and provides all system-level dependencies
(Neo4j, LLM clients, embeddings, etc.) that pipelines need.
These are initialized once at startup and made available globally.
"""

from apiana import runtime_config
from apiana.stores import ApplicationStore, AgentMemoryStore
from apiana.core.providers.local import LocalTransformersLLM
from neo4j_graphrag.embeddings.sentence_transformers import SentenceTransformerEmbeddings
import logging

logger = logging.getLogger(__name__)

# Global system dependencies
app_store: ApplicationStore = None
llm_provider: LocalTransformersLLM = None
embedding_provider: SentenceTransformerEmbeddings = None


def initialize_system():
    """Initialize all system dependencies."""
    global app_store, llm_provider, embedding_provider
    
    logger.info("Initializing system dependencies...")
    
    # Initialize stores
    app_store = ApplicationStore(runtime_config.neo4j)
    logger.info(f"Initialized ApplicationStore with Neo4j at {runtime_config.neo4j.host}:{runtime_config.neo4j.port}")
    
    # Initialize LLM provider
    llm_model = runtime_config.summarizer.model_name
    llm_provider = LocalTransformersLLM(
        model_name=llm_model,
        device="auto"
    )
    logger.info(f"Initialized LLM provider with model: {llm_model}")
    
    # Initialize embedding provider
    embedding_model = runtime_config.embedding_model_name
    embedding_provider = SentenceTransformerEmbeddings(
        embedding_model,
        trust_remote_code=True
    )
    logger.info(f"Initialized embedding provider with model: {embedding_model}")
    
    logger.info("System dependencies initialized successfully")


def get_agent_store(agent_id: str) -> AgentMemoryStore:
    """Get or create an agent-specific memory store."""
    _ensure_initialized()
    return AgentMemoryStore(runtime_config.neo4j, agent_id)


def _ensure_initialized():
    """Ensure system dependencies are initialized."""
    global app_store
    if app_store is None:
        initialize_system()


# Initialization will be done when first accessed