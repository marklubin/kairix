"""Main entry point for the agent server."""

import asyncio
import logging
import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aiohttp
import uvicorn
from deepgram import LiveOptions
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat.utils.tracing.setup import setup_tracing
from saq import Queue

try:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    HAS_OTLP = True
except ImportError:
    HAS_OTLP = False

from kairix_agent.config import Config
from kairix_agent.events import emit_context_state
from kairix_agent.logging_config import setup_logging
from kairix_agent.server.events import connection_manager
from kairix_agent.server.events.listener import start_event_listener
from kairix_agent.server.model import InputChunk, ResponseChunk, ResponseDone, ResponseStart
from kairix_agent.server.pipecat import LettaLLMService, UserTurnAggregator
from kairix_agent.server.provider import LettaProvider
from kairix_agent.server.voice.pipeline_manager import voice_pipeline_manager
from kairix_agent.voices import service as voice_service
from kairix_agent.voices.router import router as voices_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler - starts background tasks."""
    # Start the Postgres event listener
    listener_task = asyncio.create_task(start_event_listener())
    logger.info("Event listener task started")

    yield

    # Shutdown: cancel the listener task
    listener_task.cancel()
    try:
        await listener_task
    except asyncio.CancelledError:
        pass
    logger.info("Event listener task stopped")


app = FastAPI(lifespan=lifespan)
app.include_router(voices_router)


def get_or_die(env_var: str) -> str:
    maybe_env_var = os.environ.get(env_var)
    if maybe_env_var is None:
        raise RuntimeError(f"Missing environment variable {env_var}")
    return maybe_env_var


# Config from environment
deepgram_api_key = get_or_die("DEEPGRAM_API_KEY")
cartesia_api_key = get_or_die("CARTESIA_API_KEY")

# Initialize OpenTelemetry tracing if configured
TRACING_ENABLED = os.environ.get("ENABLE_TRACING", "").lower() in ("1", "true", "yes")
if TRACING_ENABLED and HAS_OTLP:
    import base64

    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

    # OpenObserve requires Basic auth + organization/stream headers for OTLP ingestion
    # Note: gRPC metadata keys must be lowercase
    otel_user = os.environ.get("OTEL_EXPORTER_OTLP_USER", "admin@kairix.local")
    otel_pass = os.environ.get("OTEL_EXPORTER_OTLP_PASSWORD", "kairix123")
    auth_string = f"{otel_user}:{otel_pass}"
    auth_bytes = base64.b64encode(auth_string.encode()).decode()
    headers = (
        ("authorization", f"Basic {auth_bytes}"),
        ("organization", "default"),
        ("stream-name", "kairix_traces"),
    )

    otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True, headers=headers)
    setup_tracing(
        service_name="kairix-voice",
        exporter=otlp_exporter,
        console_export=os.environ.get("OTEL_CONSOLE_EXPORT", "").lower() in ("1", "true"),
    )
    logger.info("OpenTelemetry tracing enabled, exporting to %s", otlp_endpoint)
elif TRACING_ENABLED:
    # Console-only tracing for debugging without OTLP collector
    setup_tracing(service_name="kairix-voice", console_export=True)
    logger.info("OpenTelemetry tracing enabled (console only)")


@app.get("/hello")
async def hello() -> str:
    return "hello world"


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, agent_id: str) -> None:
    """Text-based WebSocket endpoint for streaming responses.

    Args:
        websocket: The WebSocket connection.
        agent_id: Required agent ID query param.
    """
    await websocket.accept()
    letta_provider = LettaProvider(agent_id=agent_id)
    try:
        while True:
            text = await websocket.receive_text()
            input_chunk = InputChunk.model_validate_json(text)
            logger.info(f"Received input chunk: {input_chunk.text}")

            response_id = f"response-{uuid.uuid4()}"
            logger.info("Sending response start")
            response_start = ResponseStart(id=response_id, timestamp=1)
            await websocket.send_text(response_start.model_dump_json())

            chunk_cnt = 0
            async for chunk in letta_provider.stream_response(user_message=input_chunk.text):
                logger.info(f"Received chunk {chunk_cnt}. Content: {chunk}")
                response_chunk = ResponseChunk(
                    chunk_id=f"chunk-{chunk_cnt}",
                    response_id=response_id,
                    timestamp=2,
                    text=chunk,
                )
                await websocket.send_text(response_chunk.model_dump_json())
                chunk_cnt += 1

            logger.info("Sending response end")
            response_done = ResponseDone(id=response_id, timestamp=3)
            await websocket.send_text(response_done.model_dump_json())
    except WebSocketDisconnect:
        logger.info("Disconnected from websocket")


@app.websocket("/events/{agent_id}")
async def events_endpoint(websocket: WebSocket, agent_id: str) -> None:
    """WebSocket endpoint for streaming background events for a specific agent.

    Events are pushed as JSON:
    {
        "id": "uuid",
        "agent_id": "agent-123",
        "event_type": "summary_complete",
        "payload": {...},
        "created_at": "2025-12-06T10:30:00Z"
    }

    On connect, immediately sends the current context_state so the client
    has the latest memory blocks.
    """
    await websocket.accept()
    await connection_manager.register(agent_id, websocket)

    # Send initial context state on connect (ephemeral, no DB storage)
    try:
        await emit_context_state(
            agent_id=agent_id,
            letta_url=Config.LETTA_BASE_URL.value,
            persist=False,
        )
        logger.info(
            "Sent initial context_state to client for agent %s", agent_id)
    except Exception:
        logger.exception(
            "Failed to send initial context state for agent %s", agent_id)

    try:
        # Keep connection open, events are pushed via ConnectionManager
        while True:
            # Wait for client messages (ping/pong or close)
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await connection_manager.unregister(agent_id, websocket)


@app.websocket("/voice")
async def voice_endpoint(
    websocket: WebSocket,
    agent_id: str,
) -> None:
    """Voice pipeline endpoint using Pipecat.

    Args:
        websocket: The WebSocket connection.
        agent_id: Required agent ID query param.
    """
    await websocket.accept()

    # Look up voice from database (required)
    db_voice = await voice_service.get_agent_voice(agent_id)
    if db_voice is None:
        await websocket.close(code=4000, reason=f"No voice configured for agent {agent_id}")
        return
    voice_id = db_voice.provider_voice_id

    # Create transport for this WebSocket connection
    # ProtobufFrameSerializer defines the wire format for audio/text frames
    # VAD config: stop_secs=0.2 required for smart turn detection to work properly
    vad = SileroVADAnalyzer(
        sample_rate=16000,
        params=VADParams(
            start_secs=0.2,  # Quick to detect speech start
            stop_secs=0.2,  # Low value required for smart turn model analysis
        ),
    )

    # Smart turn detection uses ML to determine when user is done speaking
    # (vs just pausing mid-thought), enabling more natural conversation flow
    turn_analyzer = LocalSmartTurnAnalyzerV3()

    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=vad,
            turn_analyzer=turn_analyzer,
            serializer=ProtobufFrameSerializer(),
        ),
    )

    # Create services
    # Deepgram STT with generous utterance detection
    stt = DeepgramSTTService(
        api_key=deepgram_api_key,
        live_options=LiveOptions(
            model="nova-2",
            language="en-US",
            punctuate=True,
            interim_results=True,
            # Wait 2s of silence before finalizing (default ~1s)
            utterance_end_ms="1000",
            vad_events=True,
            profanity_filter=False,
        ),
    )

    tts = CartesiaTTSService(
        api_key=cartesia_api_key,
        voice_id=voice_id,
        sample_rate=22050,  # Match KMP app playback rate
    )
    user_turn_aggregator = UserTurnAggregator()

    # Create SAQ queue for background jobs
    job_queue = Queue.from_url(Config.REDIS_URL.value)

    llm = LettaLLMService(agent_id=agent_id, name="letta", queue=job_queue)

    # Register TTS with pipeline manager for live voice updates
    await voice_pipeline_manager.register(agent_id, tts)

    try:
        async with aiohttp.ClientSession():
            # Build the pipeline
            pipeline = Pipeline(
                [
                    transport.input(),  # Audio from client
                    stt,  # Speech-to-text
                    user_turn_aggregator,
                    llm,  # Letta LLM
                    tts,  # Text-to-speech
                    transport.output(),  # Audio back to client
                ]
            )

            task = PipelineTask(
                pipeline,
                params=PipelineParams(
                    allow_interruptions=True,
                    enable_metrics=True,
                    enable_usage_metrics=True,
                ),
                enable_tracing=TRACING_ENABLED,
                enable_turn_tracking=True,
                conversation_id=f"voice-{agent_id}",
            )

            runner = PipelineRunner()
            await runner.run(task)
    finally:
        # Unregister on disconnect
        await voice_pipeline_manager.unregister(agent_id, tts)


def main() -> None:
    """Run the agent server."""
    setup_logging("server")
    logger.info("Starting agent server...")

    # Hot reload disabled by default, enable with RELOAD=1
    reload_enabled = os.environ.get(
        "RELOAD", "").lower() in ("1", "true", "yes")

    uvicorn_kwargs: dict[str, object] = {
        "host": "0.0.0.0",
        "port": 8000,
    }

    if reload_enabled:
        logger.info("Hot reload enabled")
        uvicorn_kwargs["reload"] = True
        uvicorn_kwargs["reload_includes"] = ["src/kairix_agent/server/**/*.py"]
        uvicorn_kwargs["reload_excludes"] = [
            "src/kairix_agent/worker/*",
            "src/kairix_agent/provisioning/*",
            "src/kairix_agent/memory/*",
        ]

    uvicorn.run("kairix_agent.server.main:app", **uvicorn_kwargs)


if __name__ == "__main__":
    main()
