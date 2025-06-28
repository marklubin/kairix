"""Comprehensive unit tests for OpenAI adapter."""

import pytest
from typing import AsyncIterator

from openai.types.chat import (
    ChatCompletionChunk,
    ChatCompletion,
)

from kairix_core.api.adapters.openai import (
    OpenAIAdapter, StreamingDeltaConverter, PersonaProtocol
)


class MockPersona:
    """Mock persona implementing PersonaProtocol for testing."""
    
    def __init__(self, responses: list[str]):
        self.responses = responses
        self.last_message = None
        self.last_context = None
    
    async def respond(self, message: str, context: dict) -> AsyncIterator[str]:
        """Mock streaming response."""
        self.last_message = message
        self.last_context = context
        
        for response in self.responses:
            yield response


class TestOpenAIAdapter:
    """Test cases for OpenAI adapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create adapter instance."""
        return OpenAIAdapter()
    
    @pytest.fixture
    def simple_messages(self):
        """Create simple message list."""
        return [
            {"role": "user", "content": "Hello"}
        ]
    
    @pytest.fixture
    def conversation_messages(self):
        """Create messages with conversation history."""
        return [
            {"role": "user", "content": "Hi, I'm Alice"},
            {"role": "assistant", "content": "Nice to meet you, Alice!"},
            {"role": "user", "content": "What's my name?"}
        ]
    
    def test_convert_simple_messages(self, adapter, simple_messages):
        """Test converting simple messages."""
        message, context = adapter.convert_messages(simple_messages)
        
        assert message == "Hello"
        assert context["conversation_history"] == ""
    
    def test_convert_conversation_messages(self, adapter, conversation_messages):
        """Test converting messages with history."""
        message, context = adapter.convert_messages(conversation_messages)
        
        assert message == "What's my name?"
        assert context["conversation_history"] == "User: Hi, I'm Alice\nAssistant: Nice to meet you, Alice!"
    
    def test_convert_messages_with_names(self, adapter):
        """Test converting messages with custom names."""
        messages = [
            {"role": "user", "content": "Hello", "name": "Bob"},
            {"role": "assistant", "content": "Hi Bob!", "name": "AI"},
            {"role": "user", "content": "How are you?"}
        ]
        
        message, context = adapter.convert_messages(messages)
        
        assert message == "How are you?"
        assert context["conversation_history"] == "Bob: Hello\nAI: Hi Bob!"
    
    def test_convert_multipart_content(self, adapter):
        """Test converting messages with multipart content."""
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Look at this"},
                    {"type": "text", "text": "image"},
                    {"type": "image_url", "image_url": {"url": "http://example.com/image.jpg"}}
                ]
            }
        ]
        
        message, context = adapter.convert_messages(messages)
        
        assert message == "Look at this image"
    
    def test_convert_empty_messages_error(self, adapter):
        """Test error on empty messages."""
        with pytest.raises(ValueError, match="Messages list cannot be empty"):
            adapter.convert_messages([])
    
    def test_convert_non_user_last_message_error(self, adapter):
        """Test error when last message is not from user."""
        messages = [{"role": "assistant", "content": "Hello"}]
        
        with pytest.raises(ValueError, match="Last message must be from user"):
            adapter.convert_messages(messages)
    
    @pytest.mark.asyncio
    async def test_stream_response(self, adapter, simple_messages):
        """Test streaming response generation."""
        persona = MockPersona(["Hello", "Hello there", "Hello there!"])
        
        chunks = []
        async for chunk in adapter.stream_response(persona, simple_messages, "test-model"):
            chunks.append(chunk)
        
        # Should have 4 chunks: 3 content + 1 final
        assert len(chunks) == 4
        
        # Check types
        assert all(isinstance(chunk, ChatCompletionChunk) for chunk in chunks)
        
        # Check first three are content chunks
        assert chunks[0].choices[0].delta.content == "Hello"
        assert chunks[1].choices[0].delta.content == " there"
        assert chunks[2].choices[0].delta.content == "!"
        
        # Check final chunk
        assert chunks[3].choices[0].delta.content is None
        assert chunks[3].choices[0].finish_reason == "stop"
        
        # Verify request was converted correctly
        assert persona.last_message == "Hello"
    
    @pytest.mark.asyncio
    async def test_complete_response(self, adapter, simple_messages):
        """Test non-streaming response."""
        persona = MockPersona(["Hello", "Hello there", "Hello there!"])
        
        response = await adapter.complete_response(persona, simple_messages, "test-model")
        
        # Check type
        assert isinstance(response, ChatCompletion)
        
        # Check content
        assert response.object == "chat.completion"
        assert response.choices[0].message.content == "Hello there!"
        assert response.choices[0].message.role == "assistant"
        assert response.choices[0].finish_reason == "stop"
        assert response.usage is not None
        assert response.usage.total_tokens > 0
    
    @pytest.mark.asyncio
    async def test_stream_response_empty(self, adapter, simple_messages):
        """Test streaming with no response."""
        persona = MockPersona([])
        
        chunks = []
        async for chunk in adapter.stream_response(persona, simple_messages, "test-model"):
            chunks.append(chunk)
        
        # Should only have final chunk
        assert len(chunks) == 1
        assert chunks[0].choices[0].finish_reason == "stop"
    
    @pytest.mark.asyncio
    async def test_response_ids_are_unique(self, adapter, simple_messages):
        """Test that response IDs are unique."""
        persona = MockPersona(["Test"])
        
        # Get two responses
        chunks1 = []
        async for chunk in adapter.stream_response(persona, simple_messages, "test-model"):
            chunks1.append(chunk)
        
        chunks2 = []
        async for chunk in adapter.stream_response(persona, simple_messages, "test-model"):
            chunks2.append(chunk)
        
        # IDs should be different
        assert chunks1[0].id != chunks2[0].id
        
        # But consistent within a stream
        assert all(chunk.id == chunks1[0].id for chunk in chunks1)


class TestStreamingDeltaConverter:
    """Test cases for streaming delta converter."""
    
    def test_basic_delta_conversion(self):
        """Test basic delta extraction."""
        converter = StreamingDeltaConverter()
        
        assert converter.get_delta("Hello") == "Hello"
        assert converter.get_delta("Hello ") == " "
        assert converter.get_delta("Hello world") == "world"
        assert converter.get_delta("Hello world!") == "!"
    
    def test_no_change_returns_empty(self):
        """Test that no change returns empty string."""
        converter = StreamingDeltaConverter()
        
        converter.get_delta("Hello")
        assert converter.get_delta("Hello") == ""
        assert converter.get_delta("Hell") == ""  # Shorter is ignored
    
    def test_reset_functionality(self):
        """Test reset clears accumulated content."""
        converter = StreamingDeltaConverter()
        
        converter.get_delta("Hello world")
        converter.reset()
        
        assert converter.get_delta("Hello") == "Hello"
    
    def test_unicode_handling(self):
        """Test handling of unicode characters."""
        converter = StreamingDeltaConverter()
        
        assert converter.get_delta("Hello 👋") == "Hello 👋"
        assert converter.get_delta("Hello 👋 World") == " World"
        assert converter.get_delta("Hello 👋 World 🌍") == " 🌍"


class TestPersonaProtocol:
    """Test PersonaProtocol interface."""
    
    @pytest.mark.asyncio
    async def test_protocol_implementation(self):
        """Test that MockPersona implements protocol correctly."""
        persona: PersonaProtocol = MockPersona(["Test"])
        
        # Should be able to call respond
        chunks = []
        async for chunk in persona.respond("Hello", {}):
            chunks.append(chunk)
        
        assert chunks == ["Test"]