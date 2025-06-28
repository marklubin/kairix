# FastAPI OpenAI-Compatible Server

This implementation provides an OpenAI-compatible API server for KairixEngine.

## Features

- **OpenAI-compatible endpoints**:
  - `/v1/models` - List available models
  - `/v1/chat/completions` - Chat completions (streaming and non-streaming)
  - `/v1/audio/realtime` - Stubbed for future realtime audio support
  - `/v1/audio/realtime/stream` - Stubbed for future bidirectional audio streaming
  - `/health` - Health check endpoint

- **Tool usage support** through the OpenAI chat completion API
- **Streaming support** with Server-Sent Events (SSE)
- **Comprehensive test suite** with mocked Neo4j and inference connections

## Usage

```bash
# Run the server
uv run python -m kairix_apps.server

# Or with uvicorn directly
uv run uvicorn kairix_apps.server:app --host 0.0.0.0 --port 8000
```

## Environment Variables

Set `KAIRIX_AGENT_CONFIGURATION_SET_KEY` to one of:
- `openai` - Use OpenAI API
- `ollama-local` - Use local Ollama
- `ollama-remote` - Use remote Ollama

## Testing

```bash
# Run tests
uv run pytest tests/test_server.py -v
```

## Implementation Notes

- Uses the existing `OpenAIAdapter` from kairix-core
- Wraps personas with `PersonaWrapper` to match the protocol
- Delegates to `KairixEngine.conversational_persona_for_environment()`
- All dependencies are properly mocked in tests