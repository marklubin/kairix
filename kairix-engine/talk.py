import json
import logging
import os

import gradio as gr
import numpy as np
from dotenv import load_dotenv
from elevenlabs import ElevenLabs
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastrtc import (
    AdditionalOutputs,
    ReplyOnPause,
    Stream,
    get_stt_model,
)
from pydantic import BaseModel
from pyinstrument import Profiler
from rich import pretty
from rich.logging import RichHandler

from kairix_engine.engine import KairixEngine
from kairix_engine.tts import ElevenLabsTTS

logging.basicConfig(datefmt="[%X]", handlers=[RichHandler()], force=True)

logging.getLogger("kairix_engine").setLevel(logging.DEBUG)
logging.getLogger("cognition_engine").setLevel(logging.DEBUG)
logging.getLogger("fastrtc").setLevel(logging.INFO)
logging.getLogger("gradio").setLevel(logging.DEBUG)

pretty.install()

logger = logging.getLogger(__name__)


# Load .env file if not already loaded by justfile
if not os.environ.get("ELEVENLABS_API_KEY") and not load_dotenv():
    # Try to load from env/ directory if available
    env_name = os.environ.get("ENV", "mac")
    env_path = f"env/{env_name}.env"
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        raise ValueError(
            f"No environment variables loaded and {env_path} not found."
        )


elevenlabs_api_key = os.environ["ELEVENLABS_API_KEY"]
tts_client = ElevenLabs(api_key=elevenlabs_api_key)
stt = get_stt_model()
# Use ElevenLabs TTS instead of default
tts = ElevenLabsTTS(
    api_key=elevenlabs_api_key,
    voice_id=os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),
    model_id=os.environ.get("ELEVENLABS_MODEL_ID", "eleven_monolingual_v1"),
    stability=float(os.environ.get("ELEVENLABS_STABILITY", "0.5")),
    similarity_boost=float(os.environ.get("ELEVENLABS_SIMILARITY_BOOST", "0.5")),
    style=float(os.environ.get("ELEVENLABS_STYLE", "0.5")),
    use_speaker_boost=(
        os.environ.get("ELEVENLABS_USE_SPEAKER_BOOST", "true").lower() == "true"
    ),
)

chat = KairixEngine.get_chat_for_environment()
chat_initialized = False


def response(
    audio: tuple[int, np.ndarray],
    current_messages: list[dict] | None = None,
):
    current_messages = current_messages or []
    messages = [{"role": d["role"], "content": d["content"]} for d in current_messages]

    p = Profiler()
    try:
        p.start()
        prompt = stt.stt(audio)
        logger.info(f"Transcribed: {prompt}")
        messages.append({"role": "user", "content": prompt})
        yield AdditionalOutputs(messages)

        # Create a new thread to run async code
        import asyncio
        import concurrent.futures

        async def get_response():
            global chat_initialized
            if not chat_initialized:
                await chat.initialize()
                chat_initialized = True
                logger.info("Chat initialized successfully")
            return await chat.chat(prompt)

        # Run async code in thread pool to avoid event loop conflicts
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, get_response())
            full_response = future.result()

        logger.info("Received LLM response starting TTS.")

        messages.append({"role": "assistant", "content": full_response})
        yield AdditionalOutputs(messages)

        # Convert text to speech
        yield from tts.stream_tts_sync(full_response)

    except Exception as e:
        logger.error(f"Error in response handler: {e}", exc_info=True)
        # Yield error message
        messages.append({"role": "assistant", "content": f"Error: {e!s}"})
        yield AdditionalOutputs(messages)

    finally:
        p.stop()
        p.open_in_browser(timeline=True)


chatbot = gr.Chatbot(type="messages")
stream = Stream(
    modality="audio",
    mode="send-receive",
    handler=ReplyOnPause(response),
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


if __name__ == "__main__":
    stream.ui.launch(server_port=8000)
