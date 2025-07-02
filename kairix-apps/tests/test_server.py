"""Tests for FastAPI server with mocked dependencies."""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from kairix_core.cognition.persona import ConversationalPersona

# Set required environment variables for tests
os.environ["KAIRIX_AGENT_CONFIGURATION_SET_KEY"] = "ollama-local"
# Don't set KAIRIX_MCP_SERVER to use dummy implementation

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
    """Mock ConversationalPersona and OpenAIAdapter."""
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
        
        # Mock OpenAIAdapter
        with patch(
            "kairix_apps.server.OpenAIAdapter"
        ) as mock_adapter_class:
            adapter_instance = MagicMock()
            
            # Mock complete_response for non-streaming
            async def mock_complete_response(messages, model):
                return {
                    "id": "chatcmpl-test",
                    "object": "chat.completion",
                    "created": 1234567890,
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "Hello from Kairix!"
                        },
                        "finish_reason": "stop"
                    }],
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 5,
                        "total_tokens": 15
                    }
                }
            
            # Mock stream_response for streaming
            async def mock_stream_response(messages, model):
                chunks = [
                    {"choices": [{"delta": {"content": "Hello"}, "index": 0}]},
                    {"choices": [{"delta": {"content": " from"}, "index": 0}]},
                    {"choices": [{"delta": {"content": " Kairix!"}, "index": 0}]},
                    {"choices": [{"delta": {}, "finish_reason": "stop", "index": 0}]}
                ]
                for _i, chunk_data in enumerate(chunks):
                    chunk = MagicMock()
                    chunk.model_dump_json.return_value = json.dumps({
                        "id": "chatcmpl-test",
                        "object": "chat.completion.chunk",
                        "created": 1234567890,
                        "model": model,
                        **chunk_data
                    })
                    yield chunk
            
            adapter_instance.complete_response = mock_complete_response
            adapter_instance.stream_response = mock_stream_response
            mock_adapter_class.return_value = adapter_instance
            
            # Patch the global adapter
            with patch("kairix_apps.server.adapter", adapter_instance):
                yield persona


@pytest.fixture
def client(mock_persona):
    """Create test client with mocked dependencies."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers():
    """Return authentication headers for API calls."""
    return {"X-API-Key": "LosAngeles>Springfield"}


def test_health_check(client, auth_headers):
    """Test health endpoint."""
    response = client.get("/health", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "kairix-api"}


def test_unauthorized_access(client):
    """Test endpoints without API key return 401."""
    # Test without header
    response = client.get("/health")
    assert response.status_code == 422  # FastAPI returns 422 for missing required header
    
    # Test with wrong API key
    response = client.get("/health", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401
    assert "Invalid API key" in response.json()["detail"]


def test_list_models(client, auth_headers):
    """Test models list endpoint."""
    response = client.get("/v1/models", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "list"
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == "kairix-conversational"


def test_chat_completion_non_streaming(client, auth_headers):
    """Test non-streaming chat completion."""
    request = {
        "model": "kairix-conversational",
        "messages": [
            {"role": "user", "content": "Hello"}
        ],
        "stream": False
    }
    
    response = client.post("/v1/chat/completions", json=request, headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["object"] == "chat.completion"
    assert data["model"] == "kairix-conversational"
    assert len(data["choices"]) == 1
    assert data["choices"][0]["message"]["content"] == "Hello from Kairix!"


def test_chat_completion_streaming(client, auth_headers):
    """Test streaming chat completion."""
    request = {
        "model": "kairix-conversational",
        "messages": [
            {"role": "user", "content": "Hello"}
        ],
        "stream": True
    }
    
    response = client.post("/v1/chat/completions", json=request, headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    # Parse SSE response
    chunks = []
    for line in response.iter_lines():
        line = line.decode('utf-8') if isinstance(line, bytes) else line
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


def test_chat_completion_with_tools(client, auth_headers):
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
    
    response = client.post("/v1/chat/completions", json=request, headers=auth_headers)
    assert response.status_code == 200


def test_realtime_audio_stub(client, auth_headers):
    """Test realtime audio endpoint stub."""
    request = {
        "audio_data": None,
        "format": "pcm16",
        "sample_rate": 16000
    }
    
    response = client.post("/v1/audio/realtime", json=request, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_implemented"
    assert "not yet implemented" in data["message"]


def test_realtime_audio_stream_not_implemented(client, auth_headers):
    """Test that streaming audio returns 501."""
    response = client.post("/v1/audio/realtime/stream", headers=auth_headers)
    assert response.status_code == 501
    assert "not yet implemented" in response.json()["detail"].lower()


def test_chat_completion_error_handling(client, mock_persona, auth_headers):
    """Test error handling in chat completion."""
    # Patch the adapter to simulate an error
    with patch("kairix_apps.server.adapter") as mock_adapter:
        async def mock_error_complete(messages, model):
            raise Exception("Test error")
        
        mock_adapter.complete_response = mock_error_complete
        
        request = {
            "model": "kairix-conversational",
            "messages": [{"role": "user", "content": "Error test"}],
            "stream": False
        }
        
        response = client.post("/v1/chat/completions", json=request, headers=auth_headers)
        assert response.status_code == 500


def test_context_update_success(client, auth_headers):
    """Test successful context update."""
    request = {
        "timestamp": 1234567890000,
        "session_id": "test-session-123",
        "device_id": "test-device-456",
        "geolocation": {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "accuracy": 10.0,
            "timestamp": 1234567890000
        },
        "device": {
            "platform": "iPhone",
            "os_version": "iOS 17.2",
            "battery_level": 0.15,
            "network_type": "wifi"
        },
        "activity": {
            "activity_type": "running",
            "confidence": 0.9
        }
    }
    
    response = client.post("/context/update", json=request, headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert "Context update received successfully" in data["message"]
    assert "context_id" in data
    assert isinstance(data["recommendations"], list)
    assert len(data["recommendations"]) == 2  # Running + low battery recommendations
    assert "Stay hydrated during your run!" in data["recommendations"]
    assert "Your battery is low, consider charging soon." in data["recommendations"]


def test_context_update_minimal(client, auth_headers):
    """Test context update with minimal required fields."""
    request = {
        "timestamp": 1234567890000,
        "session_id": "test-session-minimal"
    }
    
    response = client.post("/context/update", json=request, headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert "context_id" in data
    assert data["recommendations"] == []


def test_context_update_invalid_data(client, auth_headers):
    """Test context update with invalid data."""
    # Missing required fields
    request = {
        "timestamp": 1234567890000
        # Missing session_id
    }
    
    response = client.post("/context/update", json=request, headers=auth_headers)
    assert response.status_code == 422  # Validation error
    
    # Invalid geolocation data
    request = {
        "timestamp": 1234567890000,
        "session_id": "test-session",
        "geolocation": {
            "latitude": 200,  # Invalid latitude > 90
            "longitude": -122.4194,
            "timestamp": 1234567890000
        }
    }
    
    response = client.post("/context/update", json=request, headers=auth_headers)
    assert response.status_code == 422


def test_context_update_unauthorized(client):
    """Test context update without authentication."""
    request = {
        "timestamp": 1234567890000,
        "session_id": "test-session"
    }
    
    # No auth header
    response = client.post("/context/update", json=request)
    assert response.status_code == 422
    
    # Wrong API key
    response = client.post("/context/update", json=request, headers={"X-API-Key": "wrong"})
    assert response.status_code == 401