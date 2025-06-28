# Kairix OpenAI-Compatible API

This document describes how to run and use the OpenAI-compatible API wrapper for Kairix personas.

## Quick Start

1. Install dependencies:
```bash
uv sync
```

2. Start the API server:
```bash
uv run uvicorn kairix_core.api.server:app --reload
```

3. The API will be available at `http://localhost:8000`

## API Endpoints

### List Models
```bash
GET /v1/models
```

Returns available persona models:
- `gpt-3.5-turbo` - Default persona
- `gpt-4` - Advanced persona

### Chat Completions
```bash
POST /v1/chat/completions
```

Supports both streaming and non-streaming responses.

Request body:
```json
{
  "model": "gpt-3.5-turbo",
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "stream": false,
  "temperature": 0.7,
  "max_tokens": 1000
}
```

## Client Examples

### Using OpenAI Python SDK

```python
import openai

client = openai.OpenAI(
    api_key="not-needed",
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
```

### Using curl

Non-streaming:
```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

Streaming:
```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -N \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": true
  }'
```

## Architecture

The API server:
1. Accepts OpenAI-format requests
2. Converts messages to Kairix Stimulus objects
3. Routes to ConversationalPersona instances
4. Streams responses in OpenAI-compatible format

Key components:
- `server.py` - FastAPI application and endpoints
- Persona initialization with all perceptors
- Streaming delta conversion for compatibility
- Message history handling

## Configuration

To add new personas, modify the `startup_event` function in `server.py`:

```python
PERSONAS["custom-model"] = initialize_persona("custom-name")
```

## Differences from OpenAI

- Authentication is not required (set any value for api_key)
- Token counting is not implemented (usage stats are placeholder)
- Only chat completion endpoints are supported
- Model names map to persona configurations
- System messages are treated as user messages

## Running Tests

See `examples/openai_api_client.py` for comprehensive client examples that test:
- Model listing
- Non-streaming completions
- Streaming completions
- Multi-turn conversations