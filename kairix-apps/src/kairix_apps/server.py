"""FastAPI server implementation for KairixEngine with OpenAI-compatible API."""
import os
import time

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
from kairix_core.runtime.storage import StorageRuntime
from kairix_core.types.environmental_context import PersonaEnvironment
from kairix_core.util.utils import get_or_raise
from starlette.middleware.base import BaseHTTPMiddleware
from typing_extensions import Any

from kairix_apps.db_wrapper import is_shadow_environment
from kairix_apps.service_types import ContextUpdateRequest, ContextUpdateResponse
from kairix_apps.telemetry_manager import TelemetryManager

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletionMessageParam

    from kairix_apps.model_manager import ModelManager
    from kairix_apps.prompt_manager import SystemPromptManager

logging_runtime = LoggingRuntime()
logger = logging_runtime.logger
agent_runtime = AgentRuntime()
storage_runtime = StorageRuntime()

# Global instances
adapter: OpenAIAdapter | None = None
persona: ConversationalPersona | None = None
model_manager: "ModelManager | None" = None
prompt_manager: "SystemPromptManager | None" = None
telemetry_manager: TelemetryManager | None = None

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


class TelemetryMiddleware(BaseHTTPMiddleware):
    """Middleware to track request telemetry."""

    async def dispatch(self, request: Request, call_next):
        """Track request metrics."""
        if telemetry_manager is None:
            return await call_next(request)

        # Extract client information
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        # Start tracking request
        request_id = telemetry_manager.start_request(
            endpoint=str(request.url.path),
            method=request.method,
            client_ip=client_ip,
            user_agent=user_agent,
        )

        # Track timing
        start_time = time.time()
        status_code = 500  # Default to error if something goes wrong
        error_type = None
        error_message = None

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response

        except Exception as e:
            error_type = type(e).__name__
            error_message = str(e)
            logger.error(f"Request {request_id} failed with error: {e}", exc_info=True)
            raise

        finally:
            # Calculate duration and end tracking
            duration_ms = (time.time() - start_time) * 1000

            try:
                telemetry_manager.end_request(
                    request_id=request_id,
                    status_code=status_code,
                    duration_ms=duration_ms,
                    error_type=error_type,
                    error_message=error_message,
                )
            except Exception as telemetry_error:
                logger.warning(f"Failed to record telemetry for request {request_id}: {telemetry_error}")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and cleanup resources."""
    global adapter, persona, model_manager, prompt_manager, telemetry_manager

    try:
        logger.info("Starting Kairix API server...")

        # Initialize telemetry manager
        telemetry_manager = TelemetryManager()
        if is_shadow_environment():
            logger.info("Running in SHADOW environment - telemetry active, DB access read-only")
        else:
            logger.info("Running in PRODUCTION environment - telemetry active")
        logger.info("Telemetry manager initialized")

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
            from typing import Optional

            from openai.types.responses.response_text_delta_event import Logprob, ResponseTextDeltaEvent

            # Get the pydantic model fields
            if hasattr(ResponseTextDeltaEvent, 'model_fields'):
                # Pydantic v2
                ResponseTextDeltaEvent.model_fields['logprobs'].annotation = Optional[list[Logprob]]
                ResponseTextDeltaEvent.model_fields['logprobs'].default = None
                # Rebuild the model to apply changes
                ResponseTextDeltaEvent.model_rebuild()
                logger.info("Successfully patched ResponseTextDeltaEvent.logprobs to be optional")
            else:
                logger.warning("Could not patch ResponseTextDeltaEvent - model_fields not found")
        except Exception as patch_error:
            logger.warning(f"Could not patch ResponseTextDeltaEvent: {patch_error}")

        from kairix_apps.engine import KairixEngine

        # Create persona using KairixEngine
        persona = KairixEngine.conversational_persona_for_environment()
        logger.info("Persona created successfully")

        # Connect MCP servers
        await persona.connect()
        logger.info("MCP servers connected successfully")

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

# Add telemetry middleware
app.add_middleware(TelemetryMiddleware)


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
                "message": f"System prompt updated in database but persona reload failed: {e!s}",
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


@app.get("/admin/reflections")
async def get_reflections(
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 100,
    offset: int = 0
):
    """Get all reflective summaries with optional date filtering."""
    if not storage_runtime:
        raise HTTPException(status_code=500, detail="Storage runtime not initialized")

    try:
        from datetime import datetime as dt

        from kairix_core.types.db import Agent, MemoryShard

        with storage_runtime.session() as session:
            # Query memory shards
            query = session.query(MemoryShard).join(Agent)

            # Apply date filters if provided
            if start_date:
                start_dt = dt.fromisoformat(start_date)
                query = query.filter(MemoryShard.created_at >= start_dt)

            if end_date:
                end_dt = dt.fromisoformat(end_date)
                query = query.filter(MemoryShard.created_at <= end_dt)

            # Order by most recent first
            query = query.order_by(MemoryShard.created_at.desc())

            # Apply pagination
            total = query.count()
            shards = query.offset(offset).limit(limit).all()

            # Format results
            results = []
            for shard in shards:
                results.append({
                    "id": shard.id,
                    "contents": shard.contents,
                    "created_at": shard.created_at.isoformat(),
                    "agent_name": shard.agent.name if shard.agent else "Unknown"
                })

            return {
                "reflections": results,
                "total": total,
                "limit": limit,
                "offset": offset
            }

    except Exception as e:
        logger.error(f"Error fetching reflections: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/admin/reflections/search")
async def search_reflections(
    query: str = Form(...),
    limit: int = Form(10)
):
    """Search reflective summaries using vector similarity."""
    if not storage_runtime:
        raise HTTPException(status_code=500, detail="Storage runtime not initialized")

    if not persona:
        raise HTTPException(status_code=500, detail="Persona not initialized")

    try:
        import numpy as np
        from kairix_core.embedding.nomic import NomicEmbedding
        from kairix_core.types.db import Agent, MemoryShard

        # Generate embedding for the search query
        embedder = NomicEmbedding()
        query_embedding = embedder.encode(query).tolist()

        with storage_runtime.session() as session:
            # Get all memory shards
            shards = session.query(MemoryShard).join(Agent).all()

            # Calculate cosine similarity for each shard
            results = []
            for shard in shards:
                # Convert stored embedding to numpy array
                shard_embedding = np.array(shard.embedding)
                query_vec = np.array(query_embedding)

                # Calculate cosine similarity
                similarity = np.dot(shard_embedding, query_vec) / (
                    np.linalg.norm(shard_embedding) * np.linalg.norm(query_vec)
                )

                results.append({
                    "id": shard.id,
                    "contents": shard.contents,
                    "created_at": shard.created_at.isoformat(),
                    "agent_name": shard.agent.name if shard.agent else "Unknown",
                    "similarity": float(similarity)
                })

            # Sort by similarity (highest first)
            results.sort(key=lambda x: x["similarity"], reverse=True)

            # Return top results
            return {
                "results": results[:limit],
                "query": query,
                "total_searched": len(shards)
            }

    except Exception as e:
        logger.error(f"Error searching reflections: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/admin/mcp-tools")
async def get_mcp_tools():
    """Get all registered MCP tools from the persona."""
    if not persona:
        raise HTTPException(status_code=500, detail="Persona not initialized")

    try:
        # Get the actuating agent from persona
        agent = persona.actuating_agent

        # Collect all MCP tools grouped by server
        mcp_tools_by_server = {}

        if hasattr(agent, 'mcp_servers') and agent.mcp_servers:
            for server in agent.mcp_servers:
                server_name = server.name if hasattr(server, 'name') else str(server)

                # Get tools from this server
                if hasattr(server, 'list_tools'):
                    try:
                        tools_list = await server.list_tools()
                        mcp_tools_by_server[server_name] = [
                            {
                                "name": tool.name if hasattr(tool, 'name') else str(tool),
                                "description": tool.description if hasattr(tool, 'description') else "No description",
                                "input_schema": tool.inputSchema if hasattr(tool, 'inputSchema') else {}
                            }
                            for tool in (tools_list.tools if hasattr(tools_list, 'tools') else tools_list)
                        ]
                    except Exception as e:
                        logger.warning(f"Could not list tools for server {server_name}: {e}")
                        mcp_tools_by_server[server_name] = []

        # Also collect native tools
        native_tools = []
        if hasattr(agent, 'tools') and agent.tools:
            for tool in agent.tools:
                tool_name = tool.name if hasattr(tool, 'name') else str(tool)
                tool_desc = tool.description if hasattr(tool, 'description') else "No description"
                native_tools.append({
                    "name": tool_name,
                    "description": tool_desc
                })

        return {
            "mcp_tools": mcp_tools_by_server,
            "native_tools": native_tools,
            "total_mcp_servers": len(mcp_tools_by_server),
            "total_native_tools": len(native_tools)
        }

    except Exception as e:
        logger.error(f"Error fetching MCP tools: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/admin/telemetry/metrics")
async def get_telemetry_metrics(
    start_time: str | None = None,
    end_time: str | None = None,
    endpoint: str | None = None,
    model_id: str | None = None,
    range_hours: int | None = 24,
):
    """Get aggregated telemetry metrics for a time range.

    Args:
        start_time: ISO format datetime string (optional)
        end_time: ISO format datetime string (optional)
        endpoint: Filter by specific endpoint (optional)
        model_id: Filter by specific model (optional)
        range_hours: Number of hours to look back if start_time not provided (default: 24)
    """
    if telemetry_manager is None:
        raise HTTPException(status_code=503, detail="Telemetry not initialized")

    try:
        from datetime import datetime, timedelta

        # Parse or calculate time range
        if start_time:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        else:
            start_dt = datetime.utcnow() - timedelta(hours=range_hours)

        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00')) if end_time else datetime.utcnow()

        # Get metrics from telemetry manager
        metrics = telemetry_manager.get_metrics(
            start_time=start_dt,
            end_time=end_dt,
            endpoint=endpoint,
            model_id=model_id,
        )

        return {
            "metrics": metrics,
            "time_range": {
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "hours": (end_dt - start_dt).total_seconds() / 3600,
            },
            "filters": {
                "endpoint": endpoint,
                "model_id": model_id,
            }
        }

    except Exception as e:
        logger.error(f"Error getting telemetry metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/admin/telemetry/timeseries")
async def get_telemetry_timeseries(
    start_time: str | None = None,
    end_time: str | None = None,
    endpoint: str | None = None,
    interval_minutes: int = 5,
    range_hours: int | None = 24,
):
    """Get time-series telemetry data for charting.

    Args:
        start_time: ISO format datetime string (optional)
        end_time: ISO format datetime string (optional)
        endpoint: Filter by specific endpoint (optional)
        interval_minutes: Time bucket size in minutes (default: 5)
        range_hours: Number of hours to look back if start_time not provided (default: 24)
    """
    if telemetry_manager is None:
        raise HTTPException(status_code=503, detail="Telemetry not initialized")

    try:
        from datetime import datetime, timedelta

        # Parse or calculate time range
        if start_time:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        else:
            start_dt = datetime.utcnow() - timedelta(hours=range_hours)

        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00')) if end_time else datetime.utcnow()

        # Get timeseries from telemetry manager
        timeseries = telemetry_manager.get_timeseries(
            start_time=start_dt,
            end_time=end_dt,
            interval_minutes=interval_minutes,
            endpoint=endpoint,
        )

        return {
            "data": timeseries,
            "time_range": {
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "hours": (end_dt - start_dt).total_seconds() / 3600,
            },
            "config": {
                "interval_minutes": interval_minutes,
                "endpoint": endpoint,
            }
        }

    except Exception as e:
        logger.error(f"Error getting telemetry timeseries: {e}", exc_info=True)
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
