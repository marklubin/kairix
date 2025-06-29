"""FastAPI server implementation for KairixEngine with OpenAI-compatible API."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from kairix_core.api.adapters.openai import OpenAIAdapter
from kairix_core.api.models import CreateChatCompletionRequest, Model
from kairix_core.runtime.agent import AgentRuntime
from kairix_core.runtime.logging import LoggingRuntime

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletionMessageParam


logger = LoggingRuntime().logger
agent_runtime = AgentRuntime()

# Global instances
adapter: OpenAIAdapter | None = None
wrapped_persona: Any = None  # PersonaWrapper instance

# API Key configuration
API_KEY = "LosAngeles>Springfield"


async def verify_api_key(x_api_key: str = Header(...)):
    """Verify the API key from X-API-Key header."""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and cleanup resources."""
    global adapter, wrapped_persona
    
    try:
        logger.info("Starting Kairix API server...")

        from kairix_apps.engine import KairixEngine
        
        async with agent_runtime.mcp_server:
            logger.info("MCP server context entered")
            
            # Create persona using KairixEngine
            persona = KairixEngine.conversational_persona_for_environment()
            logger.info("Persona created successfully")
            
            # Create adapter
            adapter = OpenAIAdapter(persona)
            logger.info("OpenAI adapter initialized successfully")
            
            yield
            
    except Exception as e:
        logger.error(f"Failed to initialize server: {e}", exc_info=True)
        raise


app = FastAPI(
    title="Kairix OpenAI-Compatible API",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check(api_key: str = Depends(verify_api_key)):
    """Health check endpoint."""
    return {"status": "healthy", "service": "kairix-api"}


@app.options("/v1/models")
@app.get("/v1/models")
async def list_models(api_key: str = Depends(verify_api_key)) -> dict[str, Any]:
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
async def create_chat_completion(request: CreateChatCompletionRequest, api_key: str = Depends(verify_api_key)) -> Any:
    """Create a chat completion with streaming support."""
    logger.info(f"Received chat completion request: model={request.model}, stream={request.stream}")
    
    if adapter is None:
        logger.error("Adapter is None - service not initialized properly")
        raise HTTPException(status_code=500, detail="Service not initialized - adapter is None")
    
    try:
        # Convert messages to format expected by adapter
        messages: list[ChatCompletionMessageParam] = [
            msg.model_dump() for msg in request.messages  # type: ignore
        ]
        logger.info(f"Processing {len(messages)} messages")
        
        # Handle streaming response
        if request.stream:
            logger.info("Generating streaming response")
            
            async def stream_generator():
                try:
                    async for chunk in adapter.stream_response(
                        messages, request.model
                    ):
                        yield f"data: {chunk.model_dump_json()}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    logger.error(f"Error in stream generator: {e}", exc_info=True)
                    raise
            
            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream"
            )
        
        # Handle non-streaming response
        else:
            logger.info("Generating non-streaming response")
            completion = await adapter.complete_response(
                messages, request.model
            )
            logger.info("Response generated successfully")
            return completion
            
    except Exception as e:
        logger.error(f"Error processing chat completion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Kairix API server on port 8000...")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info",
        access_log=True
    )
