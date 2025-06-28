"""Unit tests for persona wrapper."""

import pytest
from typing import AsyncIterator

from kairix_core.api.adapters.persona_wrapper import PersonaWrapper, PersonaFactory
from kairix_core.cognition.persona import Persona
from kairix_core.types.cognition import Stimulus, StimulusType


class MockPersona(Persona):
    """Mock persona for testing."""
    
    def __init__(self, responses: list[str]):
        self.responses = responses
        self.last_stimulus = None
    
    async def react(self, stimulus: Stimulus) -> AsyncIterator[str]:
        """Mock react method."""
        self.last_stimulus = stimulus
        for response in self.responses:
            yield response


class TestPersonaWrapper:
    """Test cases for PersonaWrapper."""
    
    @pytest.mark.asyncio
    async def test_wrapper_forwards_to_persona(self):
        """Test that wrapper correctly forwards calls to persona."""
        mock_persona = MockPersona(["Hello", "Hello world", "Hello world!"])
        wrapper = PersonaWrapper(mock_persona)
        
        context = {
            "user": "TestUser",
            "conversation_history": "Previous messages",
            "temperature": 0.8
        }
        
        responses = []
        async for chunk in wrapper.respond("Test message", context):
            responses.append(chunk)
        
        # Check responses match
        assert responses == ["Hello", "Hello world", "Hello world!"]
        
        # Check stimulus was created correctly
        assert mock_persona.last_stimulus is not None
        # Content should include conversation history
        expected_content = "Previous messages\nUser: Test message"
        assert mock_persona.last_stimulus.content == expected_content
        assert mock_persona.last_stimulus.type == StimulusType.user_message
    
    @pytest.mark.asyncio
    async def test_wrapper_with_empty_context(self):
        """Test wrapper with empty context."""
        mock_persona = MockPersona(["Response"])
        wrapper = PersonaWrapper(mock_persona)
        
        responses = []
        async for chunk in wrapper.respond("Message", {}):
            responses.append(chunk)
        
        assert responses == ["Response"]
        # With empty context, content should just be the message
        assert mock_persona.last_stimulus.content == "Message"
    
    @pytest.mark.asyncio
    async def test_wrapper_preserves_async_iteration(self):
        """Test that wrapper preserves async iteration behavior."""
        mock_persona = MockPersona(["Chunk1", "Chunk2", "Chunk3"])
        wrapper = PersonaWrapper(mock_persona)
        
        # Collect responses one by one
        response_iter = wrapper.respond("Test", {})
        
        chunk1 = await response_iter.__anext__()
        assert chunk1 == "Chunk1"
        
        chunk2 = await response_iter.__anext__()
        assert chunk2 == "Chunk2"
        
        chunk3 = await response_iter.__anext__()
        assert chunk3 == "Chunk3"
        
        # Should raise StopAsyncIteration
        with pytest.raises(StopAsyncIteration):
            await response_iter.__anext__()


class TestPersonaFactory:
    """Test cases for PersonaFactory."""
    
    @pytest.fixture
    def factory(self):
        """Create factory instance."""
        return PersonaFactory()
    
    def test_register_and_create(self, factory):
        """Test registering and creating personas."""
        # Register a builder
        def build_test_persona():
            return MockPersona(["Test response"])
        
        factory.register("test-persona", build_test_persona)
        
        # Create persona
        wrapper = factory.create("test-persona")
        
        assert isinstance(wrapper, PersonaWrapper)
        assert isinstance(wrapper.persona, MockPersona)
    
    def test_create_unregistered_error(self, factory):
        """Test error when creating unregistered persona."""
        with pytest.raises(ValueError, match="No persona registered with name: unknown"):
            factory.create("unknown")
    
    def test_list_available(self, factory):
        """Test listing available personas."""
        assert factory.list_available() == []
        
        factory.register("persona1", lambda: MockPersona([]))
        factory.register("persona2", lambda: MockPersona([]))
        
        available = factory.list_available()
        assert len(available) == 2
        assert "persona1" in available
        assert "persona2" in available
    
    def test_multiple_instances_are_independent(self, factory):
        """Test that multiple instances are independent."""
        def build_persona():
            return MockPersona(["Response"])
        
        factory.register("test", build_persona)
        
        wrapper1 = factory.create("test")
        wrapper2 = factory.create("test")
        
        # Should be different instances
        assert wrapper1 is not wrapper2
        assert wrapper1.persona is not wrapper2.persona
    
    @pytest.mark.asyncio
    async def test_factory_with_complex_builder(self, factory):
        """Test factory with more complex builder function."""
        # Builder that takes configuration
        def build_configurable_persona(responses=None):
            return MockPersona(responses or ["Default response"])
        
        # Register with custom configuration
        factory.register(
            "custom",
            lambda: build_configurable_persona(["Custom1", "Custom2"])
        )
        
        wrapper = factory.create("custom")
        
        responses = []
        async for chunk in wrapper.respond("Test", {}):
            responses.append(chunk)
        
        assert responses == ["Custom1", "Custom2"]