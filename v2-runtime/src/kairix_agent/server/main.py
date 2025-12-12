"""Main entry point for the agent server."""

import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

import aiohttp
import dotenv
import uvicorn
from deepgram import LiveOptions
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.services.piper.tts import PiperTTSService
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat_whisker import WhiskerObserver
from saq import Queue

from kairix_agent.config import Config
from kairix_agent.logging_config import setup_logging
from kairix_agent.server.events import connection_manager, start_event_listener
from kairix_agent.server.model import InputChunk, ResponseChunk, ResponseDone, ResponseStart
from kairix_agent.server.pipecat import LettaLLMService, UserTurnAggregator
from kairix_agent.server.provider import AnthropicProvider, LettaProvider

dotenv.load_dotenv()

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


def get_or_die(env_var: str) -> str:
    maybe_env_var = os.environ.get(env_var)
    if maybe_env_var is None:
        raise RuntimeError(f"Missing environment variable {env_var}")
    return maybe_env_var


# Config from environment
agent_id = get_or_die("LETTA_AGENT_ID")
deepgram_api_key = get_or_die("DEEPGRAM_API_KEY")


anthropic_provider = AnthropicProvider()
letta_provider = LettaProvider(agent_id=agent_id)


@app.get("/hello")
async def hello() -> str:
    return "hello world"


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
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
    """
    await websocket.accept()
    await connection_manager.register(agent_id, websocket)

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
async def voice_endpoint(websocket: WebSocket) -> None:
    """Voice pipeline endpoint using Pipecat."""
    await websocket.accept()

    # Create transport for this WebSocket connection
    # ProtobufFrameSerializer defines the wire format for audio/text frames
    # VAD config: quick to start, patient on pauses
    vad = SileroVADAnalyzer(
        sample_rate=16000,
        params=VADParams(
            start_secs=0.2,  # Quick to detect speech start (default 0.2)
            stop_secs=1.5,  # Wait 1.5s of silence before "done speaking" (default 0.8)
        ),
    )

    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=vad,
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
            utterance_end_ms="2000",  # Wait 2s of silence before finalizing (default ~1s)
            vad_events=True,
            profanity_filter=False,
        ),
    )

    tts = DeepgramTTSService(api_key=deepgram_api_key, voice="aura-2-phoebe-en")
    user_turn_aggregator = UserTurnAggregator()

    # Create SAQ queue for background jobs
    job_queue = Queue.from_url(Config.REDIS_URL.value)

    llm = LettaLLMService(agent_id=agent_id, name="letta", queue=job_queue)

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

        # WhiskerObserver starts a WebSocket server on port 9090 for the Whisker debugger
        whisker = WhiskerObserver(pipeline)

        task = PipelineTask(
            pipeline,
            params=PipelineParams(allow_interruptions=True),
            observers=[whisker],
        )

        runner = PipelineRunner()
        await runner.run(task)


def main() -> None:
    """Run the agent server."""
    setup_logging("server")
    logger.info("Starting agent server...")

    # Hot reload disabled by default, enable with RELOAD=1
    reload_enabled = os.environ.get("RELOAD", "").lower() in ("1", "true", "yes")

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
