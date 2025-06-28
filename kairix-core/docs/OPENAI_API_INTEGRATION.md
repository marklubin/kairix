# OpenAI API Integration for Kairix Personas

## Overview

The Kairix OpenAI-compatible API provides a seamless way to interact with Kairix personas using any OpenAI client. The implementation uses the official OpenAI Python package types directly, ensuring perfect compatibility and type safety.

## Key Features

1. **Full Type Compatibility**: Uses actual OpenAI types (`ChatCompletion`, `ChatCompletionChunk`, etc.) from the `openai` package
2. **Streaming Support**: Real-time streaming responses with proper Server-Sent Events format
3. **Decoupled Architecture**: Clean separation between API layer and Kairix internals
4. **Zero Configuration**: Works with any OpenAI client by just changing the base URL

## Architecture

```
kairix_core/api/
├── adapters/
│   ├── openai.py          # Uses OpenAI types directly
│   └── persona_wrapper.py # Adapts Kairix personas to protocol
└── server_minimal.py      # FastAPI server implementation
```

### Design Principles

1. **Use Official Types**: All request/response objects are actual OpenAI types
2. **Protocol-Based**: Defines clear interfaces without coupling
3. **Adapter Pattern**: Translates between OpenAI format and Kairix internals
4. **Type Safety**: Full typing support with mypy/pylance

## Usage Examples

### Basic Usage

```python
import openai

# Point to your Kairix server
client = openai.OpenAI(
    api_key="not-needed",
    base_url="http://localhost:8000/v1"
)

# Use exactly like OpenAI - returns real ChatCompletion object
response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello!"}]
)

# response is openai.types.chat.ChatCompletion
print(response.choices[0].message.content)
```

### Streaming

```python
# Streaming returns real ChatCompletionChunk objects
stream = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Tell me a story"}],
    stream=True
)

for chunk in stream:
    # chunk is openai.types.chat.ChatCompletionChunk
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end='')
```

### Type Safety

Since we use real OpenAI types, you get full IDE support:

```python
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types import CompletionUsage

response = client.chat.completions.create(...)

# All these type checks pass
assert isinstance(response, ChatCompletion)
assert isinstance(response.choices[0].message, ChatCompletionMessage)
assert isinstance(response.usage, CompletionUsage)
```

## Implementation Details

### OpenAI Adapter

The adapter (`adapters/openai.py`) handles all translation:

```python
class OpenAIAdapter(PersonaAdapter):
    def convert_messages(self, messages: List[ChatCompletionMessageParam]) -> tuple[str, dict]:
        # Converts OpenAI message format to Kairix format
        
    async def stream_response(self, ...) -> AsyncIterator[ChatCompletionChunk]:
        # Returns real ChatCompletionChunk objects
        
    async def complete_response(self, ...) -> ChatCompletion:
        # Returns real ChatCompletion object
```

### Message Handling

- Supports all OpenAI message formats including multipart content
- Extracts conversation history automatically
- Handles custom names and user identifiers

### Streaming Implementation

- Calculates deltas between response chunks
- Sends proper SSE format: `data: {json}\n\n`
- Ends with `data: [DONE]\n\n`

## Running the Server

```bash
# Install dependencies
uv sync

# Start the server
uv run uvicorn kairix_core.api.server_minimal:app --reload

# Or use the module directly
uv run python -m kairix_core.api.server_minimal
```

## Testing

Comprehensive test suite with 31 tests covering:

- Request/response conversion
- Streaming functionality
- Error handling
- Type compatibility

Run tests:
```bash
uv run pytest tests/unit/kairix_core/api/ -v
```

## Benefits of Using OpenAI Types

1. **No Custom Types**: No need to maintain our own request/response models
2. **Automatic Updates**: When OpenAI updates their types, we get them automatically
3. **Client Compatibility**: Any OpenAI client works without modification
4. **Type Checking**: Full mypy/pylance support out of the box
5. **Documentation**: Can reference official OpenAI docs

## Future Enhancements

- Add support for more OpenAI endpoints (embeddings, etc.)
- Implement token counting with tiktoken
- Add authentication/rate limiting
- Support for function calling
- Vision model support (beyond text extraction)