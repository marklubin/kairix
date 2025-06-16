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
    get_tts_model,
)
from pydantic import BaseModel

from kairix_engine.basic_chat import Chat

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Set specific loggers
logging.getLogger("kairix_engine").setLevel(logging.DEBUG)
logging.getLogger("cognition_engine").setLevel(logging.DEBUG)
logging.getLogger("fastrtc").setLevel(logging.DEBUG)
logging.getLogger("gradio").setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)


tts_client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
stt = get_stt_model()
tts = get_tts_model()

chat = Chat.get_chat_for_provider("openai")
chat_initialized = False


def response(
    audio: tuple[int, np.ndarray],
    current_messages: list[dict] | None = None,
):
    current_messages = current_messages or []
    messages = [{"role": d["role"], "content": d["content"]} for d in current_messages]

    try:
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

        logger.info(f"Response: {full_response}")

        messages.append({"role": "assistant", "content": full_response})
        yield AdditionalOutputs(messages)

        # Convert text to speech
        yield from tts.stream_tts_sync(full_response)

    except Exception as e:
        logger.error(f"Error in response handler: {e}", exc_info=True)
        # Yield error message
        messages.append({"role": "assistant", "content": f"Error: {e!s}"})
        yield AdditionalOutputs(messages)


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
    import os

    import uvicorn

    stream.ui.launch(server_port=8000)
    uvicorn.run(app, host="0.0.0.0", port=8000)
