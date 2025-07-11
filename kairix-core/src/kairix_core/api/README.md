# Kairix OpenAI-Compatible API

This package provides an OpenAI-compatible API wrapper for Kairix personas, allowing any OpenAI client to interact with the Kairix cognitive system.

## Architecture

The API is designed with a clean, decoupled architecture:

```
api/
├── adapters/           # Protocol adapters (decoupled from core)
│   ├── openai.py      # OpenAI format translation
│   └── persona_wrapper.py  # Wraps Kairix personas to match protocols
├── server.py          # Original server (for reference)
└── server_minimal.py  # Minimal server using adapter layer
```

## Key Components

### 1. OpenAI Adapter (`adapters/openai.py`)
- Translates between OpenAI API format and Kairix internal format
- Handles streaming delta conversion
- Completely decoupled from Kairix internals
- Uses Protocol pattern for flexibility

### 2. Persona Wrapper (`adapters/persona_wrapper.py`)
- Adapts Kairix Persona to match PersonaProtocol interface
- Provides factory pattern for persona creation
- Keeps core implementation uncoupled from API layer

### 3. Minimal Server (`server_minimal.py`)
- FastAPI application
- Uses adapter layer for all translations
- Supports both streaming and non-streaming responses
- OpenAI-compatible endpoints

## Usage

### Starting the Server

```bash
# Install dependencies
uv sync

# Run the server
uv run uvicorn kairix_core.api.server_minimal:app --reload

# Or run directly
uv run python -m kairix_core.api.server_minimal
```

### Using with OpenAI Client

```python
import openai

client = openai.OpenAI(
    api_key="not-needed",  # No auth required for local
    base_url="http://localhost:8000/v1"
)

# Non-streaming
response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)

# Streaming
stream = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello!"}],
    stream=True
)
for chunk in stream:
    print(chunk.choices[0].delta.content, end='')
```

### Available Endpoints

- `GET /v1/models` - List available personas
- `POST /v1/chat/completions` - Chat completion (streaming/non-streaming)
- `GET /health` - Health check

## Testing

Run the comprehensive test suite:

```bash
# Run all API tests
uv run pytest tests/unit/kairix_core/api/ -v

# Run specific test modules
uv run pytest tests/unit/kairix_core/api/adapters/test_openai.py -v
uv run pytest tests/unit/kairix_core/api/test_server_minimal.py -v
```

## Design Principles

1. **Decoupling**: The adapter layer is completely independent of Kairix internals
2. **Protocol-based**: Uses Python protocols for maximum flexibility
3. **Testability**: All components are independently testable with mocks
4. **Extensibility**: Easy to add new API formats or persona types

## Adding New Personas

To add a new persona type, register it in the factory:

```python
def build_custom_persona():
    # Configure your persona
    return ConversationalPersona(...)

persona_factory.register("custom-model", build_custom_persona)
```

## Future Enhancements

- Authentication/authorization support
- Usage tracking and rate limiting
- Multiple concurrent persona instances
- Additional OpenAI endpoints (embeddings, etc.)
- WebSocket support for real-time streaming