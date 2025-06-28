"""FastAPI server implementation for KairixEngine with OpenAI-compatible API."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from kairix_core.api.adapters.openai import OpenAIAdapter
from kairix_core.api.models import CreateChatCompletionRequest, Model
from pydantic import BaseModel

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletionMessageParam

logger = logging.getLogger(__name__)


# Request/Response models
class RealtimeAudioRequest(BaseModel):
    """Placeholder for future realtime audio implementation."""
    audio_data: bytes | None = None
    format: str = "pcm16"
    sample_rate: int = 16000


class RealtimeAudioResponse(BaseModel):
    """Placeholder for future realtime audio response."""
    status: str = "not_implemented"
    message: str = "Realtime audio mode is not yet implemented"


# Global instances
adapter: OpenAIAdapter | None = None
wrapped_persona: Any = None  # PersonaWrapper instance


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and cleanup resources."""
    global adapter, wrapped_persona
    
    # Import here to avoid initialization at module level
    from kairix_core.api.adapters.persona_wrapper import PersonaWrapper

    from kairix_apps.engine import KairixEngine
    
    # Create persona using KairixEngine
    persona = KairixEngine.conversational_persona_for_environment()
    
    # Wrap it to match the protocol expected by OpenAIAdapter
    wrapped_persona = PersonaWrapper(persona)  # type: ignore[arg-type]
    
    # Create adapter
    adapter = OpenAIAdapter()
    
    yield
    
    # Cleanup if needed
    adapter = None
    wrapped_persona = None


app = FastAPI(
    title="Kairix OpenAI-Compatible API",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "kairix-api"}


@app.get("/v1/models")
async def list_models() -> dict[str, Any]:
    """List available models."""
    models = [
        Model(
            id="kairix-conversational",
            object="model",
            created=1700000000,
            owned_by="kairix"
        )
    ]
    return {"object": "list", "data": models}


@app.post("/v1/chat/completions")
async def create_chat_completion(request: CreateChatCompletionRequest) -> Any:
    """Create a chat completion with streaming support."""
    if adapter is None or wrapped_persona is None:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    try:
        # Convert messages to format expected by adapter
        messages: list[ChatCompletionMessageParam] = [
            msg.model_dump() for msg in request.messages  # type: ignore
        ]
        
        # Handle streaming response
        if request.stream:
            async def stream_generator():
                assert adapter is not None  # for type checker
                async for chunk in adapter.stream_response(
                    wrapped_persona, messages, request.model
                ):
                    yield f"data: {chunk.model_dump_json()}\n\n"
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream"
            )
        
        # Handle non-streaming response
        else:
            assert adapter is not None  # for type checker
            completion = await adapter.complete_response(
                wrapped_persona, messages, request.model
            )
            return completion
            
    except Exception as e:
        logger.error(f"Error processing chat completion: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/v1/audio/realtime")
async def realtime_audio_mode(request: RealtimeAudioRequest) -> RealtimeAudioResponse:
    """Stub for future realtime audio mode implementation."""
    logger.info("Realtime audio mode requested but not implemented")
    return RealtimeAudioResponse()


@app.post("/v1/audio/realtime/stream")
async def realtime_audio_stream():
    """Stub for future bidirectional audio streaming."""
    raise HTTPException(
        status_code=501,
        detail="Bidirectional audio streaming not yet implemented"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)