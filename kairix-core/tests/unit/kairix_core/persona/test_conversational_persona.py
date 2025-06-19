import asyncio
import logging
from functools import wraps
from typing import List
from unittest.mock import Mock, AsyncMock, patch

import pytest
from agents import Agent

from kairix_core.cognition.configuration.runner import CognitionAgentRunner
from kairix_core.cognition.perceptor import Perceptor
from kairix_core.cognition.persona.conversational import ConversationalPersona
from kairix_core.types.cognition import Stimulus, Perception, StimulusType
from kairix_core.util.utils import MessageTurnFormatter


class MockResponseTextDeltaEvent:
    """Mock ResponseTextDeltaEvent for testing."""

    def __init__(self, delta: str):
        self.delta = delta


def patch_isinstance_for_response_events(func):
    """Decorator to patch isinstance for ResponseTextDeltaEvent checks."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        with patch("kairix_core.cognition.persona.conversational.isinstance") as mock_isinstance:

            def custom_isinstance(obj, cls):
                if hasattr(cls, "__name__") and cls.__name__ == "ResponseTextDeltaEvent":
                    return hasattr(obj, "delta")
                return isinstance(obj, cls)

            mock_isinstance.side_effect = custom_isinstance
            return await func(*args, **kwargs)

    return wrapper


class MockPerceptor(Perceptor):
    """Mock perceptor for testing."""

    def __init__(self, perceptions: List[Perception]):
        self.perceptions = perceptions
        self.perceive_called = False

    async def perceive(self, stimulus: Stimulus) -> List[Perception]:
        self.perceive_called = True
        return self.perceptions


@pytest.fixture
def mock_runner():
    """Create a mock CognitionAgentRunner."""
    runner = Mock(spec=CognitionAgentRunner)
    return runner


@pytest.fixture
def mock_agent():
    """Create a mock Agent."""
    agent = Mock(spec=Agent)
    agent.model = "test-model"
    return agent


@pytest.fixture
def mock_perceptors():
    """Create mock perceptors with test perceptions."""
    perception1 = Perception(source="TestPerceptor1", content="Test perception 1")
    perception2 = Perception(source="TestPerceptor2", content="Test perception 2")

    perceptor1 = MockPerceptor([perception1])
    perceptor2 = MockPerceptor([perception2])

    return [perceptor1, perceptor2]


@pytest.fixture
def mock_reflection_perceptors():
    """Create mock reflection perceptors."""
    perception = Perception(source="ReflectionPerceptor", content="Reflection perception")
    perceptor = MockPerceptor([perception])
    return [perceptor]


@pytest.fixture
def conversational_persona(mock_runner, mock_agent, mock_perceptors, mock_reflection_perceptors):
    """Create a ConversationalPersona instance with mocks."""
    # Disable logging for persona creation to avoid test interference
    persona_logger = logging.getLogger("kairix_core.cognition.persona.conversational")
    original_level = persona_logger.level
    persona_logger.setLevel(logging.WARNING)

    try:
        persona = ConversationalPersona(
            persona_name="TestPersona",
            user_name="TestUser",
            runner=mock_runner,
            perceptors=mock_perceptors,
            actuating_agent=mock_agent,
            reflection_perceptors=mock_reflection_perceptors,
        )
        return persona
    finally:
        persona_logger.setLevel(original_level)


class TestConversationalPersona:
    """Test suite for ConversationalPersona class."""

    def test_initialization(
        self, conversational_persona, mock_runner, mock_agent, mock_perceptors, mock_reflection_perceptors
    ):
        """Test that ConversationalPersona initializes correctly."""
        assert conversational_persona.persona_name == "TestPersona"
        assert conversational_persona.user_name == "TestUser"
        assert conversational_persona.runner == mock_runner
        assert conversational_persona.actuating_agent == mock_agent
        assert conversational_persona.perceptors == mock_perceptors
        assert conversational_persona.reflection_perceptors == mock_reflection_perceptors
        assert isinstance(conversational_persona.message_turn_formatter, MessageTurnFormatter)

    @pytest.mark.asyncio
    @patch_isinstance_for_response_events
    async def test_converse_method(self, conversational_persona, mock_runner):
        """Test the _converse method streams response correctly."""
        # Setup mock streaming response
        mock_event1 = Mock()
        mock_event1.type = "raw_response_event"
        mock_event1.data = MockResponseTextDeltaEvent(delta="Hello ")

        mock_event2 = Mock()
        mock_event2.type = "raw_response_event"
        mock_event2.data = MockResponseTextDeltaEvent(delta="world!")

        mock_event3 = Mock()
        mock_event3.type = "other_event"
        mock_event3.data = "should be ignored"

        mock_stream = Mock()
        mock_stream.stream_events = Mock(return_value=self._async_generator([mock_event1, mock_event2, mock_event3]))

        mock_runner.run_streamed.return_value = mock_stream

        # Test streaming
        stimulus = Stimulus(content="Test message", type=StimulusType.user_message)
        perceptions = [Perception(source="Test", content="Test perception")]

        chunks = []
        async for chunk in conversational_persona._converse(stimulus, perceptions):
            chunks.append(chunk)

        assert chunks == ["Hello ", "world!"]
        mock_runner.run_streamed.assert_called_once()

    @pytest.mark.asyncio
    @patch_isinstance_for_response_events
    async def test_react_with_user_message(
        self, conversational_persona, mock_runner, mock_perceptors, mock_reflection_perceptors
    ):
        """Test react method with user message stimulus."""
        # Setup mock streaming response
        mock_event = Mock()
        mock_event.type = "raw_response_event"
        mock_event.data = MockResponseTextDeltaEvent(delta="Test response")

        mock_stream = Mock()
        mock_stream.stream_events = Mock(return_value=self._async_generator([mock_event]))

        mock_runner.run_streamed.return_value = mock_stream

        # Test react
        stimulus = Stimulus(content="Hello!", type=StimulusType.user_message)

        chunks = []
        async for chunk in conversational_persona.react(stimulus):
            chunks.append(chunk)

        # Verify perceptors were called
        for perceptor in mock_perceptors:
            assert perceptor.perceive_called

        # Verify response was streamed
        assert chunks == ["Test response"]

        # Wait a bit for reflection tasks to complete
        await asyncio.sleep(0.1)

        # Verify reflection perceptors were triggered
        for reflector in mock_reflection_perceptors:
            assert reflector.perceive_called

    @pytest.mark.asyncio
    async def test_react_with_unsupported_stimulus(self, conversational_persona):
        """Test react method with unsupported stimulus type."""
        stimulus = Stimulus(content="Test", type=StimulusType.self_perception)

        with pytest.raises(NotImplementedError, match="Unsupported stimulus"):
            async for _ in conversational_persona.react(stimulus):
                pass

    @pytest.mark.asyncio
    @patch_isinstance_for_response_events
    async def test_perception_gathering(self, conversational_persona, mock_runner):
        """Test that all perceptions are gathered from perceptors."""
        # Setup custom perceptors with multiple perceptions
        perception1 = Perception(source="P1", content="P1")
        perception2 = Perception(source="P2", content="P2")
        perception3 = Perception(source="P3", content="P3")

        perceptor1 = MockPerceptor([perception1, perception2])
        perceptor2 = MockPerceptor([perception3])

        conversational_persona.perceptors = [perceptor1, perceptor2]

        # Setup mock streaming
        mock_event = Mock()
        mock_event.type = "raw_response_event"
        mock_event.data = MockResponseTextDeltaEvent(delta="Response")

        mock_stream = Mock()
        mock_stream.stream_events = Mock(return_value=self._async_generator([mock_event]))

        mock_runner.run_streamed.return_value = mock_stream

        # Test
        stimulus = Stimulus(content="Test", type=StimulusType.user_message)

        chunks = []
        async for chunk in conversational_persona.react(stimulus):
            chunks.append(chunk)

        # Verify all perceptions were gathered
        assert perceptor1.perceive_called
        assert perceptor2.perceive_called

    @pytest.mark.asyncio
    @patch_isinstance_for_response_events
    async def test_reflection_stimulus_creation(self, conversational_persona, mock_runner):
        """Test that reflection stimulus is created correctly."""
        # Setup mock streaming response
        mock_event1 = Mock()
        mock_event1.type = "raw_response_event"
        mock_event1.data = MockResponseTextDeltaEvent(delta="Hello ")

        mock_event2 = Mock()
        mock_event2.type = "raw_response_event"
        mock_event2.data = MockResponseTextDeltaEvent(delta="world!")

        mock_stream = Mock()
        mock_stream.stream_events = Mock(return_value=self._async_generator([mock_event1, mock_event2]))

        mock_runner.run_streamed.return_value = mock_stream

        # Mock reflection perceptor to capture the stimulus
        captured_stimulus = None

        async def capture_perceive(stimulus):
            nonlocal captured_stimulus
            captured_stimulus = stimulus
            return []

        mock_reflector = AsyncMock()
        mock_reflector.perceive.side_effect = capture_perceive

        conversational_persona.reflection_perceptors = [mock_reflector]

        # Test
        stimulus = Stimulus(content="Hello!", type=StimulusType.user_message)

        chunks = []
        async for chunk in conversational_persona.react(stimulus):
            chunks.append(chunk)

        # Wait for reflection tasks
        await asyncio.sleep(0.1)

        # Verify reflection stimulus
        assert captured_stimulus is not None
        assert captured_stimulus.type == StimulusType.self_perception
        assert "TestUser:\t Hello!" in captured_stimulus.content
        assert "TestPersona:\t Hello world!" in captured_stimulus.content

    @pytest.mark.asyncio
    async def test_message_turn_formatter_integration(self, conversational_persona):
        """Test that MessageTurnFormatter is used correctly."""
        formatter = conversational_persona.message_turn_formatter

        # Test formatting
        formatted = formatter.format_turn("User message", "Persona response")
        assert "TestUser:\t User message" in formatted
        assert "TestPersona:\t Persona response" in formatted

    @pytest.mark.asyncio
    @patch_isinstance_for_response_events
    async def test_empty_perceptions_handling(self, conversational_persona, mock_runner):
        """Test handling when perceptors return empty lists."""
        # Setup perceptors that return empty lists
        conversational_persona.perceptors = [MockPerceptor([]), MockPerceptor([])]

        # Setup mock streaming
        mock_event = Mock()
        mock_event.type = "raw_response_event"
        mock_event.data = MockResponseTextDeltaEvent(delta="Response")

        mock_stream = Mock()
        mock_stream.stream_events = Mock(return_value=self._async_generator([mock_event]))

        mock_runner.run_streamed.return_value = mock_stream

        # Test - should work fine with empty perceptions
        stimulus = Stimulus(content="Test", type=StimulusType.user_message)

        chunks = []
        async for chunk in conversational_persona.react(stimulus):
            chunks.append(chunk)

        assert chunks == ["Response"]

    @pytest.mark.asyncio
    @patch_isinstance_for_response_events
    async def test_reflection_task_error_handling(self, conversational_persona, mock_runner):
        """Test that errors in reflection tasks don't break the main flow."""
        # Setup mock streaming
        mock_event = Mock()
        mock_event.type = "raw_response_event"
        mock_event.data = MockResponseTextDeltaEvent(delta="Response")

        mock_stream = Mock()
        mock_stream.stream_events = Mock(return_value=self._async_generator([mock_event]))

        mock_runner.run_streamed.return_value = mock_stream

        # Setup reflection perceptor that raises an error
        async def failing_perceive(stimulus):
            raise Exception("Reflection failed")

        mock_reflector = AsyncMock()
        mock_reflector.perceive.side_effect = failing_perceive

        conversational_persona.reflection_perceptors = [mock_reflector]

        # Test - should complete successfully despite reflection error
        stimulus = Stimulus(content="Test", type=StimulusType.user_message)

        chunks = []
        async for chunk in conversational_persona.react(stimulus):
            chunks.append(chunk)

        assert chunks == ["Response"]

    @pytest.mark.asyncio
    @patch_isinstance_for_response_events
    async def test_multiple_reflection_perceptors(self, conversational_persona, mock_runner):
        """Test that all reflection perceptors are triggered."""
        # Setup mock streaming
        mock_event = Mock()
        mock_event.type = "raw_response_event"
        mock_event.data = MockResponseTextDeltaEvent(delta="Response")

        mock_stream = Mock()
        mock_stream.stream_events = Mock(return_value=self._async_generator([mock_event]))

        mock_runner.run_streamed.return_value = mock_stream

        # Setup multiple reflection perceptors
        reflector1 = MockPerceptor([])
        reflector2 = MockPerceptor([])
        reflector3 = MockPerceptor([])

        conversational_persona.reflection_perceptors = [reflector1, reflector2, reflector3]

        # Test
        stimulus = Stimulus(content="Test", type=StimulusType.user_message)

        chunks = []
        async for chunk in conversational_persona.react(stimulus):
            chunks.append(chunk)

        # Wait for reflection tasks
        await asyncio.sleep(0.1)

        # Verify all reflection perceptors were called
        assert reflector1.perceive_called
        assert reflector2.perceive_called
        assert reflector3.perceive_called

    @pytest.mark.asyncio
    @patch_isinstance_for_response_events
    async def test_stream_event_filtering(self, conversational_persona, mock_runner):
        """Test that only MockResponseTextDeltaEvent events are yielded."""
        # Setup mixed event types
        mock_event1 = Mock()
        mock_event1.type = "raw_response_event"
        mock_event1.data = MockResponseTextDeltaEvent(delta="Valid ")

        mock_event2 = Mock()
        mock_event2.type = "other_event"
        mock_event2.data = "Should be ignored"

        mock_event3 = Mock()
        mock_event3.type = "raw_response_event"
        mock_event3.data = "Not a MockResponseTextDeltaEvent"

        mock_event4 = Mock()
        mock_event4.type = "raw_response_event"
        mock_event4.data = MockResponseTextDeltaEvent(delta="chunk")

        mock_stream = Mock()
        mock_stream.stream_events = Mock(
            return_value=self._async_generator([mock_event1, mock_event2, mock_event3, mock_event4])
        )

        mock_runner.run_streamed.return_value = mock_stream

        # Test
        stimulus = Stimulus(content="Test", type=StimulusType.user_message)
        perceptions: List[Perception] = []

        chunks = []
        async for chunk in conversational_persona._converse(stimulus, perceptions):
            chunks.append(chunk)

        # Only valid MockResponseTextDeltaEvent chunks should be yielded
        assert chunks == ["Valid ", "chunk"]

    async def _async_generator(self, items):
        """Helper to create async generators for testing."""
        for item in items:
            yield item
