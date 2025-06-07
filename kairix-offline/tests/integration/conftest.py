import pytest
import os
import sys
import numpy as np
from unittest.mock import MagicMock, patch
from dotenv import load_dotenv

# Remove any mocked modules from unit tests
for module in list(sys.modules.keys()):
    if module.startswith('kairix'):
        del sys.modules[module]

from neomodel import config as neomodel_config, db, clear_neo4j_database

load_dotenv()


@pytest.fixture(scope="session")
def neo4j_db():
    """Setup Neo4j connection for integration tests"""
    neo4j_url = os.getenv("NEO4J_URL")
    if not neo4j_url:
        pytest.skip("NEO4J_URL not set, skipping integration tests")
    
    neomodel_config.DATABASE_URL = neo4j_url
    yield db
    

# Define test data constants
TEST_AGENT_NAMES = [
    "test-agent-001",
    "test-agent-002", 
    "test-agent-003",
    "test-agent-multi-001",
    "test-agent-long-001",
    "test-agent-rel-001",
    "test-agent-empty-001",
    "test-agent-idem-001"
]

TEST_DOC_UIDS = [
    "test-doc-001",
    "test-doc-002",
    "test-doc-003",
    "test-doc-004",
    "test-doc-005",
    "test-doc-long-001",
    "test-doc-rel-001",
    "test-doc-empty-001",
    "test-doc-idem-001"
]

TEST_MEMORY_SHARD_UID_PREFIX = "test-shard-"
TEST_SUMMARY_UID_PREFIX = "test-summary-"
TEST_EMBEDDING_UID_PREFIX = "test-embedding-"


@pytest.fixture(autouse=True)
def clean_db(neo4j_db):
    """Clean test-specific records before and after each test"""
    def cleanup():
        # Delete all test agents
        for agent_name in TEST_AGENT_NAMES:
            neo4j_db.cypher_query(
                "MATCH (n:Agent {name: $name}) DETACH DELETE n",
                {"name": agent_name}
            )
        
        # Delete all test documents and related nodes
        for doc_uid in TEST_DOC_UIDS:
            neo4j_db.cypher_query(
                "MATCH (n:SourceDocument {uid: $uid}) DETACH DELETE n",
                {"uid": doc_uid}
            )
        
        # Delete all test memory shards, summaries, and embeddings
        neo4j_db.cypher_query("""
            MATCH (n)
            WHERE (n:MemoryShard AND n.uid STARTS WITH $shard_prefix)
               OR (n:Summary AND n.uid STARTS WITH $summary_prefix)
               OR (n:Embedding AND n.uid STARTS WITH $embedding_prefix)
            DETACH DELETE n
        """, {
            "shard_prefix": TEST_MEMORY_SHARD_UID_PREFIX,
            "summary_prefix": TEST_SUMMARY_UID_PREFIX,
            "embedding_prefix": TEST_EMBEDDING_UID_PREFIX
        })
        
        # Also clean up any chatgpt source documents from GPT loader tests
        neo4j_db.cypher_query(
            "MATCH (n:SourceDocument {source_type: 'chatgpt'}) DETACH DELETE n"
        )
        
        # Clean up the smoke test document
        neo4j_db.cypher_query(
            "MATCH (n:SourceDocument {uid: '1'}) DETACH DELETE n"
        )
    
    # Clean before test
    cleanup()
    
    yield
    
    # Clean after test
    cleanup()


@pytest.fixture
def mock_llm():
    """Mock LLM that returns predictable summaries"""
    mock = MagicMock()
    
    def mock_generator(user_prompt, batch_size=1, max_length=512):
        # Return a simple summary based on the prompt
        return [{
            "generated_text": f"Summary: This is a summary of the content about {user_prompt[:50]}..."
        }]
    
    mock.side_effect = mock_generator
    return mock


@pytest.fixture
def mock_embedder():
    """Mock embedder that returns predictable embeddings"""
    mock = MagicMock()
    
    def encode(texts, batch_size=32, show_progress_bar=True):
        if isinstance(texts, str):
            texts = [texts]
        # Return random but consistent embeddings as numpy arrays
        # For a single text, return a single array (not nested)
        if len(texts) == 1:
            return np.random.rand(768)
        return np.array([np.random.rand(768) for _ in texts])
    
    mock.encode = encode
    return mock


@pytest.fixture
def mock_chunker():
    """Mock chunker that splits text into simple chunks"""
    def chunker(text):
        # Simple chunking by splitting every 100 characters
        chunk_size = 100
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunks.append(text[i:i+chunk_size])
        return chunks
    
    return chunker


@pytest.fixture
def mock_kairix_module(mock_llm, mock_embedder, mock_chunker):
    """Patch the kairix module with mocked components"""
    with patch('kairix.summary_generator', mock_llm), \
         patch('kairix.LLMTextGenerator', mock_llm), \
         patch('kairix.embedding_transformer', mock_embedder), \
         patch('kairix.chunker', mock_chunker):
        yield