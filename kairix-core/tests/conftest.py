"""Root conftest.py for kairix-core tests.

This file imports all fixtures from the shared testing module, making them
available to all tests in this project.
"""

# Import all fixtures from the shared testing module
from kairix_core.testing.conftest import *  # noqa: F403

# You can add project-specific test fixtures here that aren't needed
# by external packages

import pytest
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_data_dir(tmp_path):
    """Create a temporary directory for test data."""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def sample_conversation():
    """Sample conversation data for testing."""
    return [
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you! How can I help you today?"},
        {"role": "user", "content": "Can you explain quantum computing?"},
        {"role": "assistant", "content": "Quantum computing uses quantum mechanical phenomena..."}
    ]


@pytest.fixture
def sample_stimuli():
    """Sample stimuli for testing."""
    from kairix_core.types.cognition import Stimulus, StimulusType
    
    return {
        'user_message': Stimulus(
            content="What's the weather like?",
            type=StimulusType.user_message
        ),
        'time_tick': Stimulus(
            content="2024-01-01T12:00:00",
            type=StimulusType.time_tick
        ),
        'world_event': Stimulus(
            content="System update available",
            type=StimulusType.world_event
        )
    }


@pytest.fixture
def sample_perceptions():
    """Sample perceptions for testing."""
    from kairix_core.types.cognition import Perception
    
    return [
        Perception(
            source="conversation_history",
            content="Recent discussion about AI ethics",
            confidence=0.95
        ),
        Perception(
            source="environmental_context", 
            content="Current time: 3:00 PM, Weather: Sunny",
            confidence=1.0
        ),
        Perception(
            source="semantic_graph",
            content="Related concepts: machine learning, neural networks",
            confidence=0.85
        )
    ]