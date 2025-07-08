"""Shared pytest fixtures and mocks for testing Kairix components.

This module provides mock implementations of all runtime components and services
that can be used in tests. It's designed to be imported by both internal tests
and external packages that depend on kairix-core.

Usage:
    # In your test file or conftest.py
    from kairix_core.testing.conftest import *
    
    # Or import specific fixtures
    from kairix_core.testing.conftest import mock_agent_runtime
"""

import asyncio
from typing import AsyncIterator, List, Optional, Dict, Any
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import pytest
from dataclasses import dataclass

from kairix_core.types.cognition import Stimulus, Perception
from kairix_core.cognition.perceptor import Perceptor
from kairix_core.cognition.persona import Persona
from kairix_core.configuration.types import AgentConfig, AgentConfigurationSet
from kairix_core.inference.inference_provider import InferenceProvider, InferenceParams


# ============================================================================
# Mock Data Classes
# ============================================================================

@dataclass
class MockAgent:
    """Mock Agent for testing."""
    name: str = "test_agent"
    model: str = "gpt-4"
    
    
@dataclass
class MockRunResult:
    """Mock run result for agent execution."""
    data: str
    
    def __init__(self, data: str = "Mock response"):
        self.data = data


@dataclass 
class MockRunResultStreaming:
    """Mock streaming result for agent execution."""
    _chunks: List[str]
    
    def __init__(self, chunks: Optional[List[str]] = None):
        self._chunks = chunks or ["Mock ", "streaming ", "response"]
        
    async def __aiter__(self):
        for chunk in self._chunks:
            yield chunk


# ============================================================================
# Perceptor Mocks
# ============================================================================

class MockPerceptor(Perceptor):
    """Mock perceptor for testing."""
    
    def __init__(self, name: str = "mock_perceptor", perceptions: Optional[List[Perception]] = None):
        self.name = name
        self._perceptions = perceptions or [
            Perception(source=name, content="Mock perception", confidence=0.9)
        ]
        
    async def perceive(self, stimulus: Stimulus) -> List[Perception]:
        """Return mock perceptions."""
        return self._perceptions


@pytest.fixture
def mock_conversation_history_perceptor():
    """Mock ConversationHistoryPerceptor."""
    perceptor = MockPerceptor("conversation_history")
    perceptor.get_recent_turns = AsyncMock(return_value=[  # type: ignore[attr-defined]
        ("User: Hello", "Assistant: Hi there!"),
        ("User: How are you?", "Assistant: I'm doing well, thanks!")
    ])
    return perceptor


@pytest.fixture
def mock_environmental_context_perceptor():
    """Mock EnvironmentalContextPerceptor."""
    return MockPerceptor(
        "environmental_context",
        [Perception(
            source="environmental_context",
            content="Current time: 2024-01-01 12:00 PM, Location: San Francisco, Weather: Sunny 72°F",
            confidence=1.0
        )]
    )


@pytest.fixture
def mock_semantic_graph_perceptor():
    """Mock SemanticGraphPerceptor."""
    return MockPerceptor(
        "semantic_graph",
        [Perception(
            source="semantic_graph",
            content="Related concepts: AI, machine learning, neural networks",
            confidence=0.85
        )]
    )


@pytest.fixture
def mock_summary_insight_perceptor():
    """Mock SummaryInsightPerceptor."""
    return MockPerceptor(
        "summary_insight",
        [Perception(
            source="summary_insight",
            content="Previous conversations discussed: project planning, code review",
            confidence=0.85
        )]
    )


# ============================================================================
# Persona Mocks
# ============================================================================

class MockPersona(Persona):
    """Mock persona for testing."""
    
    def __init__(self, responses: Optional[List[str]] = None):
        self._responses = responses or ["Hello", " from", " mock", " persona!"]
        
    async def react(self, stimulus: Stimulus) -> AsyncIterator[str]:  # type: ignore
        """Generate mock response."""
        for response in self._responses:
            yield response


@pytest.fixture
def mock_conversational_persona():
    """Mock ConversationalPersona."""
    persona = MockPersona()
    persona.reflect = AsyncMock()  # type: ignore[attr-defined]
    return persona


# ============================================================================
# Runtime Mocks
# ============================================================================

@pytest.fixture
def mock_agent_runtime(monkeypatch):
    """Mock AgentRuntime singleton."""
    mock_runtime = Mock()
    
    # Configuration
    mock_runtime.configuration_set = AgentConfigurationSet(
        name="test_config",
        default_provider="openai",
        description="Test configuration",
        agent_configs={
            "default": AgentConfig(name="default", model="gpt-4"),
            "test_agent": AgentConfig(name="test_agent", model="gpt-4")
        }
    )
    
    # Methods
    mock_runtime._get_agent_config = Mock(return_value=AgentConfig(
        name="test_agent", model="gpt-4", temperature=0.7, max_tokens=256
    ))
    mock_runtime.run = Mock(return_value=MockRunResult())
    mock_runtime.run_async = AsyncMock(return_value=MockRunResult())
    mock_runtime.run_stream = Mock(return_value=MockRunResultStreaming())
    
    # Patch the singleton
    with patch('kairix_core.runtime.agent.AgentRuntime') as mock_class:
        mock_class.return_value = mock_runtime
        mock_class._instance = mock_runtime
        yield mock_runtime


@pytest.fixture
def mock_cache_runtime():
    """Mock CacheRuntime."""
    mock_cache = Mock()
    mock_cache.cache_index = MagicMock()
    mock_cache.pp_cache_keys = Mock()
    
    # Make cache_index behave like a dict
    cache_data: Dict[str, Any] = {}
    mock_cache.cache_index.__getitem__ = lambda _, k: cache_data.get(k)
    mock_cache.cache_index.__setitem__ = lambda _, k, v: cache_data.__setitem__(k, v)
    mock_cache.cache_index.__contains__ = lambda _, k: k in cache_data
    mock_cache.cache_index.get = lambda k, default=None: cache_data.get(k, default)
    
    return mock_cache


@pytest.fixture
def mock_logging_runtime():
    """Mock LoggingRuntime."""
    mock_logging = Mock()
    mock_logging.logger = Mock()
    mock_logging.logger.debug = Mock()
    mock_logging.logger.info = Mock()
    mock_logging.logger.warning = Mock()
    mock_logging.logger.error = Mock()
    mock_logging.logger.exception = Mock()
    return mock_logging




# ============================================================================
# Inference Provider Mocks
# ============================================================================

class MockInferenceProvider(InferenceProvider):
    """Mock inference provider for testing."""
    
    def __init__(self, response: str = "Mock inference response"):
        self.response = response
        
    def predict(self, content: str, inference_params: InferenceParams) -> str:
        """Return mock prediction."""
        return self.response


@pytest.fixture
def mock_openai_provider():
    """Mock OpenAI inference provider."""
    provider = MockInferenceProvider("OpenAI mock response")
    provider.client = Mock()  # type: ignore[attr-defined]
    return provider


@pytest.fixture
def mock_llama_cpp_provider():
    """Mock llama.cpp provider."""
    provider = Mock()
    provider.create_model = Mock()
    provider.create_pooled_model = Mock()
    
    # Mock model
    mock_model = Mock()
    mock_model.sync_complete = Mock(return_value="Llama.cpp response")
    provider.create_model.return_value = mock_model
    
    # Mock pooled model
    mock_pooled = AsyncMock()
    mock_pooled.borrow = AsyncMock()
    mock_pooled.return_model = AsyncMock()
    provider.create_pooled_model.return_value = mock_pooled
    
    return provider


# ============================================================================
# Store Mocks
# ============================================================================

@pytest.fixture
def mock_embedded_data_store():
    """Mock EmbeddedDataStore."""
    store = Mock()
    store.search = AsyncMock(return_value=[
        {"content": "Result 1", "similarity": 0.95},
        {"content": "Result 2", "similarity": 0.90}
    ])
    store.model = Mock()
    store.model.encode = Mock(return_value=[[0.1] * 768])  # Mock embedding
    return store


# ============================================================================
# Database Mocks
# ============================================================================

@pytest.fixture
def mock_storage_runtime():
    """Mock SQLite StorageRuntime."""
    from kairix_core.runtime.storage import StorageRuntime
    
    mock_storage = Mock(spec=StorageRuntime)
    mock_storage.session = Mock()
    mock_storage.engine = Mock()
    mock_storage.get_dao = Mock()
    mock_storage.vector_dao = Mock()
    
    # Mock session context manager
    mock_session = Mock()
    mock_session.__enter__ = Mock(return_value=mock_session)
    mock_session.__exit__ = Mock(return_value=None)
    mock_storage.session.return_value = mock_session
    
    return mock_storage





# ============================================================================
# Utility Mocks
# ============================================================================

@pytest.fixture
def mock_environment_variables(monkeypatch):
    """Mock common environment variables."""
    env_vars = {
        'KAIRIX_AGENT_CONFIGURATION_SET_KEY': 'test_config',
        'KAIRIX_INFERENCE_PROVIDER': 'openai',
        'KAIRIX_INFERENCE_API_KEY': 'test-api-key',
        'KAIRIX_INFERENCE_BASE_URL': 'http://localhost:11434',
        'DATABASE_URL': 'sqlite:///test_kairix.db',
        'OPENAI_API_KEY': 'test-openai-key',
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    return env_vars


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for API calls."""
    client = AsyncMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    
    # Mock responses
    client.get.return_value = Mock(
        status_code=200,
        json=Mock(return_value={
            "city": "San Francisco",
            "temperature": 72,
            "weather": "Sunny"
        })
    )
    
    return client


# ============================================================================
# Static Method Mocks
# ============================================================================

@pytest.fixture
def mock_static_methods():
    """Mock common static methods."""
    mocks = {}
    
    # Mock get_or_raise
    with patch('kairix_core.util.utils.get_or_raise') as mock_get:
        mock_get.side_effect = lambda key: {
            'KAIRIX_AGENT_CONFIGURATION_SET_KEY': 'test_config',
            'KAIRIX_INFERENCE_PROVIDER': 'openai'
        }.get(key, f"mock-{key}")
        mocks['get_or_raise'] = mock_get
    
    return mocks


# ============================================================================
# Complete Test Environment
# ============================================================================

@pytest.fixture
def complete_mock_environment(
    mock_agent_runtime,
    mock_cache_runtime,
    mock_logging_runtime,
    mock_environment_variables,
    mock_static_methods
):
    """Complete mock environment with all components."""
    return {
        'agent_runtime': mock_agent_runtime,
        'cache_runtime': mock_cache_runtime,
        'logging_runtime': mock_logging_runtime,
        'env_vars': mock_environment_variables,
        'static_methods': mock_static_methods
    }


# ============================================================================
# Async Utilities
# ============================================================================

@pytest.fixture
def async_test_utils():
    """Utilities for async testing."""
    
    async def collect_async_iter(async_iter):
        """Collect all items from an async iterator."""
        items = []
        async for item in async_iter:
            items.append(item)
        return items
    
    async def timeout_after(coro, seconds=1.0):
        """Run coroutine with timeout."""
        return await asyncio.wait_for(coro, timeout=seconds)
    
    return {
        'collect_async_iter': collect_async_iter,
        'timeout_after': timeout_after
    }