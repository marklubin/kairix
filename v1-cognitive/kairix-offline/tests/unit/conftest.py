"""
Pytest configuration for unit tests
"""

import sys
import os
from unittest.mock import Mock, MagicMock

import pytest

# Set test environment variables
os.environ["KAIRIX_SUMMARY_EXTRACTION_PARALLELISM"] = "5"
os.environ["KAIRIX_SEMANTIC_EMBEDDING_SCORE_MERGE_THRESHOLD"] = "0.95"
os.environ["KAIRIX_SEMANTIC_EMBEDDING_MODEL"] = "all-MiniLM-L6-v2"
os.environ["KAIRIX_SEMANTIC_EMBEDDING_DIMS"] = "384"
os.environ["KAIRIX_AGENT_CONFIGURATION_SET_KEY"] = "test"

# Mock the runtime components IMMEDIATELY before any imports can happen
# This ensures that when modules are imported, they get the mocked versions

# Mock the runtime components
mock_agent_runtime = Mock()


# Create an async mock for the run method
async def mock_run(*args, **kwargs):
    return mock_agent_runtime.run.return_value


mock_agent_runtime.run = MagicMock(side_effect=mock_run)
sys.modules["kairix_core.runtime.agent"] = Mock()
sys.modules["kairix_core.runtime.agent"].AgentRuntime = Mock(
    return_value=mock_agent_runtime
)


@pytest.fixture
def agents():
    return mock_agent_runtime


mock_cache_runtime = Mock()
mock_cache_runtime.extracted_facts = {}
mock_cache_runtime.extraction_processing_records = {}
sys.modules["kairix_core.runtime.cache"] = Mock()
sys.modules["kairix_core.runtime.cache"].CacheRuntime = Mock(
    return_value=mock_cache_runtime
)

mock_cache_runtime.extraction_processing_records = dict()
mock_cache_runtime.extracted_facts = dict()


@pytest.fixture
def cache():
    return mock_cache_runtime


mock_logging_runtime = Mock()
mock_logging_runtime.logger = Mock()
sys.modules["kairix_core.runtime.logging"] = Mock()
sys.modules["kairix_core.runtime.logging"].LoggingRuntime = Mock(
    return_value=mock_logging_runtime
)


@pytest.fixture
def logging():
    return mock_logging_runtime


# Mock Neo4j runtime
mock_neo4j_runtime = Mock()
sys.modules["kairix_core.runtime.neo4j"] = Mock()
sys.modules["kairix_core.runtime.neo4j"].Neo4jRuntime = Mock(
    return_value=mock_neo4j_runtime
)


@pytest.fixture
def neo4j():
    return mock_neo4j_runtime


# Mock neomodel to prevent database connections
sys.modules["neomodel"] = Mock()
sys.modules["neomodel"].config = Mock()
sys.modules["neomodel"].db = Mock()

# Mock Summary with nodes attribute
mock_summary = Mock()
mock_summary.nodes = Mock()
mock_all = Mock()
mock_summary.nodes.all = mock_all

sys.modules["kairix_core.types.neo4j"] = Mock()
sys.modules["kairix_core.types.neo4j"].Summary = mock_summary

# Mock the extraction agents  
sys.modules["kairix_offline.semantic_graph.agents"] = Mock()
sys.modules["kairix_offline.semantic_graph.agents"].world_facts_extractor = Mock()
sys.modules["kairix_offline.semantic_graph.agents"].user_profile_extractor = Mock()
sys.modules["kairix_offline.semantic_graph.agents"].assistant_cognitive_extractor = Mock()


@pytest.fixture
def mock_all():
    return mock_all


# Mock sentence_transformers to prevent model loading
mock_embedder = Mock()
mock_embedder.encode = Mock(return_value=[0.1] * 384)
sys.modules["sentence_transformers"] = Mock()
sys.modules["sentence_transformers"].SentenceTransformer = Mock(
    return_value=mock_embedder
)
