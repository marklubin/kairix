"""Tests for FastAPI server with mocked dependencies."""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from kairix_core.cognition.persona import ConversationalPersona

# Set required environment variable for tests
os.environ["KAIRIX_AGENT_CONFIGURATION_SET_KEY"] = "ollama-local"

from kairix_apps.server import app


@pytest.fixture
def mock_neo4j():
    """Mock Neo4j runtime."""
    with patch("kairix_core.runtime.neo4j.Neo4jRuntime") as mock:
        instance = MagicMock()
        instance.session = MagicMock()
        instance.driver = MagicMock()
        mock.return_value = instance
        yield instance


@pytest.fixture
def mock_inference():
    """Mock inference provider."""
    with patch("kairix_core.inference.inference_provider.InferenceProvider") as mock:
        instance = MagicMock()
        instance.generate = AsyncMock(return_value="Test response")
        mock.get_provider.return_value = instance
        yield instance


@pytest.fixture
def mock_agent_runtime():
    """Mock AgentRuntime to avoid initialization issues."""
    with patch("kairix_apps.engine.AgentRuntime") as mock_runtime:
        instance = MagicMock()
        mock_runtime.return_value = instance
        yield instance


@pytest.fixture
def mock_persona(mock_neo4j, mock_inference, mock_agent_runtime):
    """Mock ConversationalPersona and PersonaWrapper."""
    with patch(
        "kairix_apps.engine.KairixEngine.conversational_persona_for_environment"
    ) as mock_engine:
        # Mock the persona
        persona = MagicMock(spec=ConversationalPersona)
        
        async def mock_react(stimulus):
            yield "Hello"
            yield " from"
            yield " Kairix!"
        
        persona.react = mock_react
        mock_engine.return_value = persona
        
        # Mock PersonaWrapper to return a wrapped persona with respond method
        with patch(
            "kairix_core.api.adapters.persona_wrapper.PersonaWrapper"
        ) as mock_wrapper:
            wrapped_persona = MagicMock()
            
            async def mock_respond(message, context):
                # Return accumulated responses for complete_response
                responses = ["Hello", "Hello from", "Hello from Kairix!"]
                for response in responses:
                    yield response
            
            wrapped_persona.respond = mock_respond
            mock_wrapper.return_value = wrapped_persona
            
            yield persona


@pytest.fixture
def client(mock_persona):
    """Create test client with mocked dependencies."""
    with TestClient(app) as c:
        yield c


def test_health_check(client):
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "kairix-api"}


def test_list_models(client):
    """Test models list endpoint."""
    response = client.get("/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "list"
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == "kairix-conversational"


def test_chat_completion_non_streaming(client):
    """Test non-streaming chat completion."""
    request = {
        "model": "kairix-conversational",
        "messages": [
            {"role": "user", "content": "Hello"}
        ],
        "stream": False
    }
    
    response = client.post("/v1/chat/completions", json=request)
    assert response.status_code == 200
    
    data = response.json()
    assert data["object"] == "chat.completion"
    assert data["model"] == "kairix-conversational"
    assert len(data["choices"]) == 1
    assert data["choices"][0]["message"]["content"] == "Hello from Kairix!"


def test_chat_completion_streaming(client):
    """Test streaming chat completion."""
    request = {
        "model": "kairix-conversational",
        "messages": [
            {"role": "user", "content": "Hello"}
        ],
        "stream": True
    }
    
    response = client.post("/v1/chat/completions", json=request)
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    # Parse SSE response
    chunks = []
    for line in response.iter_lines():
        if line.startswith("data: "):
            data = line[6:]
            if data != "[DONE]":
                chunks.append(json.loads(data))
    
    assert len(chunks) == 4  # 3 content chunks + 1 finish chunk
    assert all(chunk["object"] == "chat.completion.chunk" for chunk in chunks)
    
    # Reconstruct message (filter out None content)
    content = "".join(
        chunk["choices"][0]["delta"].get("content") or "" for chunk in chunks
    )
    assert content == "Hello from Kairix!"


def test_chat_completion_with_tools(client):
    """Test chat completion with tool usage."""
    request = {
        "model": "kairix-conversational",
        "messages": [
            {"role": "user", "content": "Call a function"}
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string"}
                        }
                    }
                }
            }
        ],
        "stream": False
    }
    
    response = client.post("/v1/chat/completions", json=request)
    assert response.status_code == 200


def test_realtime_audio_stub(client):
    """Test realtime audio endpoint stub."""
    request = {
        "audio_data": None,
        "format": "pcm16",
        "sample_rate": 16000
    }
    
    response = client.post("/v1/audio/realtime", json=request)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_implemented"
    assert "not yet implemented" in data["message"]


def test_realtime_audio_stream_not_implemented(client):
    """Test that streaming audio returns 501."""
    response = client.post("/v1/audio/realtime/stream")
    assert response.status_code == 501
    assert "not yet implemented" in response.json()["detail"].lower()


def test_chat_completion_error_handling(client, mock_persona):
    """Test error handling in chat completion."""
    # Patch the global wrapped_persona to simulate an error
    with patch("kairix_apps.server.wrapped_persona") as mock_wrapped:
        async def mock_error_respond(message, context):
            raise Exception("Test error")
            yield  # Never reached
        
        mock_wrapped.respond = mock_error_respond
        
        request = {
            "model": "kairix-conversational",
            "messages": [{"role": "user", "content": "Error test"}],
            "stream": False
        }
        
        response = client.post("/v1/chat/completions", json=request)
        assert response.status_code == 500