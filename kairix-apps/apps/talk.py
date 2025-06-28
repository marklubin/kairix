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
    AlgoOptions,
    ReplyOnPause,
    Stream,
    get_stt_model,
)
from pydantic import BaseModel
from rich import pretty
from rich.logging import RichHandler

from kairix_apps.engine import KairixEngine
from kairix_core.tts import ElevenLabsTTS
from kairix_core.types.cognition import Stimulus, StimulusType

logging.basicConfig(level=logging.INFO)


pretty.install()

logger = logging.getLogger()
logger.addHandler(RichHandler())


# Load .env file if not already loaded by justfile
if not os.environ.get("ELEVENLABS_API_KEY") and not load_dotenv():
    # Try to load from env/ directory if available
    env_name = os.environ.get("ENV", "mac")
    env_path = f"env/{env_name}.env"
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        raise ValueError(f"No environment variables loaded and {env_path} not found.")


elevenlabs_api_key = os.environ["ELEVENLABS_API_KEY"]
tts_client = ElevenLabs(api_key=elevenlabs_api_key)
stt = get_stt_model()
# Use ElevenLabs TTS instead of default
tts = ElevenLabsTTS(
    api_key=elevenlabs_api_key,
)


persona = KairixEngine.conversational_persona_for_environment()

phrase_triggers = ['-', ',', '.']


def is_completed_phrase(tts_buffer):
    return tts_buffer and (tts_buffer[-1] == ','
                           or tts_buffer[-1] == '.'
                           or tts_buffer[-1] == "-")

async def response(
    audio: tuple[int, np.ndarray],
    current_messages: list[dict] | None = None,
):
    current_messages = current_messages or []
    messages = [{"role": d["role"], "content": d["content"]} for d in current_messages]

    tts_buffer = ""

    os.system("clear")
    try:
        prompt = stt.stt(audio)
        logger.info(f"Transcribed: {prompt}")
        messages.append({"role": "user", "content": prompt})
        yield AdditionalOutputs(messages)

        messages.append({"role":"assistant", "content": "..."})

        async for full, chunk in persona.react(Stimulus(prompt,
                                                        StimulusType.user_message)):
            logger.info(f"Got next chunk {chunk}.")


            logger.info("Emitting present full message")
            messages[-1]['content'] = full
            yield AdditionalOutputs(messages)


            tts_buffer += chunk
            logger.info(f"Present TTS Buffer is: {tts_buffer}")

            if is_completed_phrase(tts_buffer):
                logger.info("Deteected Phrase Completion Rendering Audio...")
                async for audio in tts.stream_tts(tts_buffer):
                    yield audio
                tts_buffer = ""
            else:
                logger.info("No phrase ending detected, proceeding to next chunk.")


        if tts_buffer:
            logger.warning("TTS buffer unexpectedly empty.")
            async for audio in tts.stream_tts(tts_buffer):
                yield audio


    except Exception as e:
        logger.error(f"Error in response handler: {e}", exc_info=True)
        # Yield error message
        messages.append({"role": "assistant", "content": f"Error: {e!s}"})
        yield AdditionalOutputs(messages)


chatbot = gr.Chatbot(type="messages")
stream = Stream(
    modality="audio",
    mode="send-receive",
    handler=ReplyOnPause(
        response,
        algo_options=AlgoOptions(
            audio_chunk_duration=1, started_talking_threshold=.5, speech_threshold=.1
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


if __name__ == "__main__":
    stream.ui.launch(server_port=8000)
