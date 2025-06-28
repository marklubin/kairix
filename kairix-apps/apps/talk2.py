from kairix_core.runtime.logging import LoggingRuntime

logger = LoggingRuntime().logger

import asyncio
import json
import os
from collections.abc import AsyncGenerator

import gradio as gr
import numpy as np
from elevenlabs import ElevenLabs
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastrtc import (
    AdditionalOutputs,
    AlgoOptions,
    ReplyOnPause,
    Stream,
    get_stt_model,
)
from kairix_core.runtime.agent import AgentRuntime
from kairix_core.tts import ElevenLabsTTS
from kairix_core.types.cognition import Stimulus, StimulusType
from kairix_core.util.utils import get_or_raise
from pydantic import BaseModel

from kairix_apps.engine import KairixEngine

elevenlabs_api_key = get_or_raise("ELEVENLABS_API_KEY")
tts_client = ElevenLabs(api_key=elevenlabs_api_key)
stt = get_stt_model()

tts = ElevenLabsTTS(
    api_key=elevenlabs_api_key,
)

persona = KairixEngine.conversational_persona_for_environment()

phrase_triggers = ["-", ",", ".", "?"]

# Global state for audio control
current_audio_task = None
audio_cancelled = False


def is_completed_phrase(tts_buffer):
    return tts_buffer and (
        tts_buffer[-1] == "," or tts_buffer[-1] == "." or tts_buffer[-1] == "-" or tts_buffer[-1] == "?"
    )


async def cancel_current_audio():
    """Cancel the current audio playback"""
    global current_audio_task, audio_cancelled
    if current_audio_task and not current_audio_task.done():
        audio_cancelled = True
        current_audio_task.cancel()
        try:
            await current_audio_task
        except asyncio.CancelledError:
            pass


async def play_audio_with_cancellation(audio_generator: AsyncGenerator):
    """Play audio with cancellation support"""
    global audio_cancelled
    audio_cancelled = False
    try:
        async for audio in audio_generator:
            if audio_cancelled:
                break
            yield audio
    except asyncio.CancelledError:
        logger.info("Audio playback cancelled")
        raise


async def response(
    audio: tuple[int, np.ndarray],
    current_messages: list[dict] | None = None,
):
    """Handle audio inputs with interruption support"""
    global current_audio_task
    
    current_messages = current_messages or []
    messages = [{"role": d["role"], "content": d["content"]} for d in current_messages]

    # Cancel any ongoing audio when new input is detected
    await cancel_current_audio()

    tts_buffer = ""

    os.system("clear")
    try:
        prompt = stt.stt(audio)
        logger.info(f"Transcribed: {prompt}")
        messages.append({"role": "user", "content": prompt})
        yield AdditionalOutputs(messages)

        messages.append({"role": "assistant", "content": "..."})

        async for full, chunk in persona.react(
            Stimulus(prompt, StimulusType.user_message)
        ):
            logger.info(f"Got next chunk {chunk}.")

            logger.info("Emitting present full message")
            messages[-1]["content"] = full
            yield AdditionalOutputs(messages)

            tts_buffer += chunk
            logger.info(f"Present TTS Buffer is: {tts_buffer}")

            if is_completed_phrase(tts_buffer):
                logger.info("Detected Phrase Completion Rendering Audio...")
                current_audio_task = asyncio.create_task(
                    play_audio_with_cancellation(tts.stream_tts(tts_buffer))
                )
                try:
                    async for audio_chunk in current_audio_task:
                        yield audio_chunk
                except asyncio.CancelledError:
                    logger.info("Audio interrupted by new input")
                tts_buffer = ""
            else:
                logger.info("No phrase ending detected, proceeding to next chunk.")

        if tts_buffer:
            logger.warning("TTS buffer not empty, playing remaining audio.")
            current_audio_task = asyncio.create_task(
                play_audio_with_cancellation(tts.stream_tts(tts_buffer))
            )
            try:
                async for audio_chunk in current_audio_task:
                    yield audio_chunk
            except asyncio.CancelledError:
                logger.info("Final audio interrupted by new input")

    except Exception as e:
        logger.error(f"Error in response handler: {e}", exc_info=True)
        messages.append({"role": "assistant", "content": f"Error: {e!s}"})
        yield AdditionalOutputs(messages)


# Custom handler that cancels audio on new input
class InterruptibleReplyOnPause(ReplyOnPause):
    async def __call__(self, *args, **kwargs):
        # Cancel any ongoing audio when VAD detects speech
        await cancel_current_audio()
        # Call the parent handler
        async for result in super().__call__(*args, **kwargs):
            yield result


chatbot = gr.Chatbot(type="messages")
stream = Stream(
    modality="audio",
    mode="send-receive",
    handler=InterruptibleReplyOnPause(
        response,
        algo_options=AlgoOptions(
            audio_chunk_duration=1,
            started_talking_threshold=0.5,
            speech_threshold=0.1,
        ),
    ),
    additional_outputs_handler=lambda old, new: new,
    additional_inputs=[chatbot],
    additional_outputs=[chatbot],
)


class Message(BaseModel):
    role: str
    content: str


class InputData(BaseModel):
    webrtc_id: str
    chatbot: list[Message]


app = FastAPI()
stream.mount(app)


@app.post("/input_hook")
async def _(body: InputData):
    stream.set_input(body.webrtc_id, body.model_dump()["chatbot"])
    return {"status": "ok"}


@app.get("/outputs")
def _(webrtc_id: str):
    async def output_stream():
        async for output in stream.output_stream(webrtc_id):
            chatbot = output.args[0]
            yield f"event: output\ndata: {json.dumps(chatbot[-1])}\n\n"

    return StreamingResponse(output_stream(), media_type="text/event-stream")


async def main():
    """Main entry point with proper async context manager usage"""
    agent_runtime = AgentRuntime()
    
    # Use the MCP server as an async context manager
    async with agent_runtime.mcp_server:
        # Launch the stream UI
        stream.ui.launch(server_port=8000)


if __name__ == "__main__":
    asyncio.run(main())