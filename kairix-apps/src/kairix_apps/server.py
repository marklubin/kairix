"""FastAPI server implementation for KairixEngine with OpenAI-compatible API."""
import os

os.putenv("KAIRIX_APP_ID", "server")

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from kairix_core.api.adapters.openai import OpenAIAdapter
from kairix_core.api.models import CreateChatCompletionRequest, Model
from kairix_core.cognition import ConversationalPersona
from kairix_core.runtime.agent import AgentRuntime
from kairix_core.runtime.logging import LoggingRuntime
from kairix_core.types.environmental_context import PersonaEnvironment
from kairix_core.util.utils import get_or_raise
from typing_extensions import Any

from kairix_apps.service_types import ContextUpdateRequest, ContextUpdateResponse

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletionMessageParam

logging_runtime = LoggingRuntime()
logger = logging_runtime.logger
agent_runtime = AgentRuntime()

# Global instances
adapter: OpenAIAdapter | None = None
persona: ConversationalPersona | None = None

# Container specific configurations
port: int = int(get_or_raise("KAIRIX_SERVER_PORT"))
env_var_log_level: str | None = os.getenv("KAIRIX_LOG_LEVEL")
log_level: str = str(env_var_log_level) if os.getenv("KAIRIX_LOG_LEVEL") else "debug"


async def verify_api_key(x_api_key: str = Header(...)) -> str:
    """Verify API key from header."""
    maybe_api_key = os.environ.get("KAIRIX_API_KEY")

    if not maybe_api_key:
        logger.info("No API Key configured for server allowing all requests.")
        return "ok"

    if x_api_key != maybe_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and cleanup resources."""
    global adapter, persona

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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Log validation errors with full details."""
    logger.error(f"Validation error for {request.url}: {exc.errors()}")
    logger.error(f"Request body: {exc.body}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": str(exc.body)}
    )


@app.get("/health")
async def health_check() -> dict \
        :
    """Health check endpoint."""
    return {"status": "healthy", "service": "kairix-api"}


@app.options("/v1/models")
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
                    assert hasattr(adapter, "stream_response")

                    maybe_generator = adapter.stream_response(messages, request.model)

                    async for chunk in maybe_generator:
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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat completion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/context/update", dependencies=[Depends(verify_api_key)])
async def update_context(
        request: ContextUpdateRequest,
        api_key: str = Depends(verify_api_key)
) -> ContextUpdateResponse:
    if not persona:
        raise OSError("Environment is not initialized correctly.")

    """Update context information from client."""
    logger.info(f"Received context update for session {request.session_id}")
    logger.debug(f"Full request data: {request.model_dump()}")

    try:
        # Log context data for debugging
        if request.geolocation:
            logger.info(f"Geolocation: lat={request.geolocation.latitude}, lon={request.geolocation.longitude}")
        if request.device:
            logger.info(f"Device: platform={request.device.platform}, os={request.device.os_version}")
        if request.activity:
            logger.info(f"Activity: type={request.activity.activity_type}, confidence={request.activity.confidence}")

        environment = PersonaEnvironment(
            geolocation=request.geolocation,
            device_info=request.device,
            physical_environment=request.environment,
            user_activity=request.activity
        )

        await persona.environment_updated(environment)
        return ContextUpdateResponse(
            success=True,
            message="Context update received successfully"
        )

    except Exception as e:
        logger.error(f"Error processing context update: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting Kairix API server on port {port} with log level {log_level}...")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level=log_level.lower(),
        access_log=True
    )
