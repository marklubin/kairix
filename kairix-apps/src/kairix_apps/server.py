"""FastAPI server implementation for KairixEngine with OpenAI-compatible API."""
import os

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["KAIRIX_APP_ID"] = "server"

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import Depends, FastAPI, Form, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
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
    from kairix_apps.model_manager import ModelManager
    from kairix_apps.prompt_manager import SystemPromptManager

logging_runtime = LoggingRuntime()
logger = logging_runtime.logger
agent_runtime = AgentRuntime()

# Global instances
adapter: OpenAIAdapter | None = None
persona: ConversationalPersona | None = None
model_manager: "ModelManager | None" = None
prompt_manager: "SystemPromptManager | None" = None

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
    global adapter, persona, model_manager, prompt_manager

    try:
        logger.info("Starting Kairix API server...")

        # Validate MCP servers (required for server startup)
        import subprocess
        from pathlib import Path

        mcp_config_path = Path(__file__).parent.parent.parent / "mcp_config.json"
        if mcp_config_path.exists():
            logger.info("Validating MCP server configuration...")
            validate_script = Path(__file__).parent.parent.parent / "validate_mcp_servers.py"

            result = subprocess.run(
                ["python", str(validate_script)],
                cwd=str(validate_script.parent),
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                logger.error(f"MCP validation failed:\n{result.stdout}\n{result.stderr}")
                raise RuntimeError("MCP server validation failed. Server cannot start.")

            logger.info("MCP servers validated successfully")
        else:
            logger.warning(f"No MCP config found at {mcp_config_path}, skipping validation")

        # Initialize model manager
        from kairix_apps.model_manager import ModelManager
        model_manager = ModelManager()
        logger.info(f"Model manager initialized, current model: {model_manager.get_selected_model()}")

        # Initialize prompt manager
        from kairix_apps.prompt_manager import SystemPromptManager
        prompt_manager = SystemPromptManager()
        selected_prompt = prompt_manager.get_selected_prompt()
        if selected_prompt:
            logger.info(f"Prompt manager initialized, current prompt: {selected_prompt.prompt_id}")
        else:
            logger.warning("No system prompt selected")

        # Monkey-patch ResponseTextDeltaEvent to make logprobs optional
        # This fixes validation error with openai-agents library
        try:
            from openai.types.responses.response_text_delta_event import ResponseTextDeltaEvent, Logprob
            from typing import List, Optional

            # Get the pydantic model fields
            if hasattr(ResponseTextDeltaEvent, 'model_fields'):
                # Pydantic v2
                ResponseTextDeltaEvent.model_fields['logprobs'].annotation = Optional[List[Logprob]]
                ResponseTextDeltaEvent.model_fields['logprobs'].default = None
                # Rebuild the model to apply changes
                ResponseTextDeltaEvent.model_rebuild()
                logger.info("Successfully patched ResponseTextDeltaEvent.logprobs to be optional")
            else:
                logger.warning("Could not patch ResponseTextDeltaEvent - model_fields not found")
        except Exception as patch_error:
            logger.warning(f"Could not patch ResponseTextDeltaEvent: {patch_error}")

        from kairix_apps.engine import KairixEngine

        # Try to start MCP server, but don't fail if it's not available
        mcp_context = None
        try:
            mcp_context = agent_runtime.mcp_server
            await mcp_context.__aenter__()
            logger.info("MCP server context entered")
        except Exception as mcp_error:
            logger.warning(f"MCP server not available, continuing without it: {mcp_error}")

        try:
            # Create persona using KairixEngine
            persona = KairixEngine.conversational_persona_for_environment()
            logger.info("Persona created successfully")

            # Create adapter
            adapter = OpenAIAdapter(persona)
            logger.info("OpenAI adapter initialized successfully")

            yield
        finally:
            if mcp_context:
                try:
                    await mcp_context.__aexit__(None, None, None)
                except Exception as e:
                    logger.warning(f"Error closing MCP context: {e}")

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
async def create_chat_completion(request: CreateChatCompletionRequest) -> Any:
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


@app.get("/admin", response_class=HTMLResponse)
async def admin_panel():
    """Simple admin panel for server management."""
    from pathlib import Path
    template_path = Path(__file__).parent / "admin_template.html"
    html_content = template_path.read_text()
    return HTMLResponse(content=html_content)


@app.get("/admin/info")
async def admin_info():
    """Get server information for admin panel."""
    current_model = model_manager.get_selected_model() if model_manager else "Unknown"

    return {
        "status": "online",
        "persona_name": os.getenv("KAIRIX_PERSONA_NAME", "Unknown"),
        "user_name": os.getenv("KAIRIX_USER_NAME", "Unknown"),
        "port": port,
        "adapter_initialized": adapter is not None,
        "persona_initialized": persona is not None,
        "current_model": current_model
    }


@app.get("/admin/models")
async def get_models():
    """Get all available models."""
    if not model_manager:
        raise HTTPException(status_code=500, detail="Model manager not initialized")

    models = model_manager.get_all_models()
    return {
        "models": [m.to_dict() for m in models],
        "current_model": model_manager.get_selected_model()
    }


@app.post("/admin/models/validate")
async def validate_model(model_id: str = Form(...)):
    """Validate a model by sending a test request."""
    if not adapter or not persona:
        raise HTTPException(status_code=500, detail="Service not initialized")

    logger.info(f"Validating model: {model_id}")

    try:
        # Temporarily set the model in environment for testing
        original_model = os.environ.get("KAIRIX_AGENT_MODEL")
        os.environ["KAIRIX_AGENT_MODEL"] = model_id

        # Send a simple test message
        from openai.types.chat import ChatCompletionMessageParam
        test_messages: list[ChatCompletionMessageParam] = [
            {"role": "user", "content": "Respond with exactly one word: OK"}  # type: ignore
        ]

        # Test the model with a timeout
        import asyncio
        try:
            completion = await asyncio.wait_for(
                adapter.complete_response(test_messages, "kairix-conversational"),
                timeout=20.0
            )

            # Restore original model
            if original_model:
                os.environ["KAIRIX_AGENT_MODEL"] = original_model

            # Check if we got a valid response
            if completion.choices and len(completion.choices) > 0:
                response_text = completion.choices[0].message.content or ""
                logger.info(f"Model {model_id} validated successfully: {response_text[:50]}")
                return {
                    "valid": True,
                    "model_id": model_id,
                    "test_response": response_text[:100]  # First 100 chars
                }
            else:
                logger.error(f"Model {model_id} returned no choices")
                return {
                    "valid": False,
                    "model_id": model_id,
                    "error": "Model returned no response"
                }

        except asyncio.TimeoutError:
            # Restore original model
            if original_model:
                os.environ["KAIRIX_AGENT_MODEL"] = original_model
            logger.error(f"Model {model_id} validation timed out")
            return {
                "valid": False,
                "model_id": model_id,
                "error": "Model validation timed out (20s)"
            }

    except Exception as e:
        # Restore original model
        original_model = os.environ.get("KAIRIX_AGENT_MODEL")
        if original_model:
            os.environ["KAIRIX_AGENT_MODEL"] = original_model

        logger.error(f"Model {model_id} validation failed: {e}", exc_info=True)
        return {
            "valid": False,
            "model_id": model_id,
            "error": str(e)
        }


@app.post("/admin/models/select")
async def select_model(model_id: str = Form(...)):
    """Select a model and update Doppler config."""
    if not model_manager:
        raise HTTPException(status_code=500, detail="Model manager not initialized")

    logger.info(f"Received request to change model to: {model_id}")

    success = model_manager.set_selected_model(model_id)

    if success:
        # Trigger environment reload
        os.environ["KAIRIX_AGENT_MODEL"] = model_id
        logger.info(f"Model changed to {model_id}, environment updated")

        return {
            "success": True,
            "message": f"Model updated to {model_id}",
            "current_model": model_id
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to update model configuration")


# ====== System Prompt Management Endpoints ======

@app.get("/admin/prompts")
async def get_prompts():
    """Get all available system prompts."""
    if not prompt_manager:
        raise HTTPException(status_code=500, detail="Prompt manager not initialized")

    prompts = prompt_manager.get_all_prompts()
    selected = prompt_manager.get_selected_prompt()
    return {
        "prompts": [p.to_dict() for p in prompts],
        "current_prompt": selected.prompt_id if selected else None
    }


@app.post("/admin/prompts/select")
async def select_prompt(prompt_id: str = Form(...)):
    """Select a system prompt."""
    if not prompt_manager:
        raise HTTPException(status_code=500, detail="Prompt manager not initialized")

    logger.info(f"Received request to change system prompt to: {prompt_id}")

    success = prompt_manager.set_selected_prompt(prompt_id)

    if success:
        logger.info(f"System prompt changed to {prompt_id} in database")

        # Recreate persona with new prompt
        global persona, adapter
        try:
            from kairix_apps.engine import KairixEngine
            logger.info("Recreating persona with new system prompt...")
            persona = KairixEngine.conversational_persona_for_environment()

            # Recreate adapter with new persona
            from kairix_core.api.adapters.openai import OpenAIAdapter
            adapter = OpenAIAdapter(persona)

            logger.info(f"Successfully reloaded persona with prompt: {prompt_id}")
            return {
                "success": True,
                "message": f"System prompt updated to {prompt_id} and persona reloaded",
                "current_prompt": prompt_id,
                "persona_reloaded": True
            }
        except Exception as e:
            logger.error(f"Failed to reload persona: {e}", exc_info=True)
            return {
                "success": True,
                "message": f"System prompt updated in database but persona reload failed: {str(e)}",
                "current_prompt": prompt_id,
                "persona_reloaded": False,
                "error": str(e)
            }
    else:
        raise HTTPException(status_code=500, detail="Failed to update system prompt")


@app.post("/admin/prompts/save")
async def save_prompt(
    prompt_id: str = Form(...),
    name: str = Form(...),
    description: str = Form(...),
    content: str = Form(...),
    version: str = Form("custom")
):
    """Save a new or updated system prompt."""
    if not prompt_manager:
        raise HTTPException(status_code=500, detail="Prompt manager not initialized")

    logger.info(f"Saving system prompt: {prompt_id}")

    try:
        success = prompt_manager.save_prompt(prompt_id, name, description, content, version)

        if success:
            return {
                "success": True,
                "message": f"System prompt '{name}' saved successfully",
                "prompt_id": prompt_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save system prompt")

    except Exception as e:
        logger.error(f"Error saving system prompt: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/admin/prompts/generate")
async def generate_prompt(requirements: str = Form(...)):
    """Generate a system prompt using AI based on user requirements."""
    if not prompt_manager:
        raise HTTPException(status_code=500, detail="Prompt manager not initialized")

    logger.info("Generating system prompt with AI")

    try:
        agent_name = os.getenv("KAIRIX_PERSONA_NAME", "AI Assistant")
        user_name = os.getenv("KAIRIX_USER_NAME", "User")

        generated_prompt = await prompt_manager.generate_prompt_with_ai(
            requirements, agent_name, user_name
        )

        return {
            "success": True,
            "generated_prompt": generated_prompt,
            "message": "Prompt generated successfully. Review and edit before saving."
        }

    except Exception as e:
        logger.error(f"Error generating prompt: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting Kairix API server on port {port} with log level {log_level}...")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level=log_level.lower(),
        access_log=True,
        log_config=None
    )
