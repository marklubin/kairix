"""
Pytest configuration and fixtures for knowledge_db_demo tests
"""
import pytest
from unittest.mock import Mock, patch
import sys
import os

# Set PYTEST_RUN environment variable to prevent Neo4j connection
os.environ['PYTEST_RUN'] = '1'

# Add scripts directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

# Mock neomodel first
sys.modules['neomodel'] = Mock()
sys.modules['neomodel'].config = Mock()
sys.modules['neomodel'].db = Mock()

# Mock sentence_transformers
mock_embedder = Mock()
mock_embedder.encode = Mock(return_value=[0.1] * 128)
sys.modules['sentence_transformers'] = Mock()
sys.modules['sentence_transformers'].SentenceTransformer = Mock(return_value=mock_embedder)

# Mock rich logging
sys.modules['rich'] = Mock()
sys.modules['rich'].print = print
sys.modules['rich.logging'] = Mock()
sys.modules['rich.logging'].RichHandler = Mock

# Mock the external modules before importing knowledge_db_demo
sys.modules['kairix_core'] = Mock()
sys.modules['kairix_core.types'] = Mock()

# Mock the agents module
mock_agent = Mock()
mock_agent.name = "mock_agent"
mock_agent.instructions = "mock instructions"
mock_agent.output_type = Mock()
mock_agent.model = "mock-model"

sys.modules['agents'] = Mock()
sys.modules['agents'].Agent = Mock(return_value=mock_agent)
sys.modules['agents'].Runner = Mock()
sys.modules['agents'].ModelSettings = Mock()

# Import our mock types
from mock_types import SemanticUnit, SemanticRelationship, Summary

# Set the mock types in the mocked module
sys.modules['kairix_core.types'].SemanticUnit = SemanticUnit
sys.modules['kairix_core.types'].SemanticRelationship = SemanticRelationship
sys.modules['kairix_core.types'].Summary = Summary

# Patch Summary.nodes.all to prevent the module-level asyncio.run from executing
Summary.nodes = Mock()
Summary.nodes.all = Mock(return_value=[])


@pytest.fixture(autouse=True)
def mock_neo4j_connection():
    """Automatically mock Neo4j connection for all tests"""
    with patch('knowledge_db_demo.db') as mock_db:
        mock_db.set_connection = Mock()
        mock_db.cypher_query = Mock(return_value=([], None))
        yield mock_db


@pytest.fixture(autouse=True)
def mock_sentence_transformer():
    """Automatically mock sentence transformer for all tests"""
    with patch('knowledge_db_demo.SentenceTransformer') as mock_st:
        mock_instance = Mock()
        mock_instance.encode = Mock(return_value=[0.1] * 128)
        mock_st.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def sample_summary_texts():
    """Provide sample summary texts for testing"""
    return [
        "Mark is considering hosting AI servers at home. The servers require significant power and cooling.",
        "The user expressed concerns about noise levels. The assistant suggested sound dampening solutions.",
        "Technical discussion about network architecture. Powerline adapters were recommended for connectivity.",
        "Mark values privacy and wants to maintain control over his AI infrastructure.",
        "The assistant learned that the user prefers practical, cost-effective solutions."
    ]


@pytest.fixture
def mock_neo4j_models():
    """Mock the Neo4j model classes"""
    with patch('knowledge_db_demo.SemanticUnit') as mock_su:
        with patch('knowledge_db_demo.SemanticRelationship') as mock_sr:
            with patch('knowledge_db_demo.Summary') as mock_summary:
                yield {
                    'SemanticUnit': mock_su,
                    'SemanticRelationship': mock_sr,
                    'Summary': mock_summary
                }


@pytest.fixture
def async_mock_runner():
    """Provide a properly configured async mock for Runner"""
    from unittest.mock import AsyncMock
    
    with patch('knowledge_db_demo.Runner') as mock_runner:
        mock_runner.run = AsyncMock()
        yield mock_runner


# Test markers
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.slow = pytest.mark.slow