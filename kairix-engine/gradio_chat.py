import logging
import os

import gradio as gr
import numpy as np
from agents import Runner
from cognition_engine.perceptor.conversation_remembering_perceptor import (
    ConversationRememberingPerceptor,
)
from dotenv import load_dotenv
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

from kairix_engine.basic_chat import Chat
from kairix_engine.summary_store import SummaryStore

# Load environment variables from .env file
load_dotenv()

NEO4J_URL = "bolt://neo4j:password@cayucos.thrush-escalator.ts.net:7687"

# Configure logging
logging.basicConfig(level=logging.WARNING)
logging.getLogger("kairix_engine").setLevel(logging.DEBUG)
logging.getLogger("cognition_engine").setLevel(logging.DEBUG)

# Initialize ElevenLabs client
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = "0NkECxcbkydDMspBKvQp"  # From eleven.py
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
# Initialize components
store = SummaryStore(store_url=NEO4J_URL)
perceptor = ConversationRememberingPerceptor(
    Runner(),
    memory_provider=lambda query, k: [
        content for content, score in store.search(query, k)
    ],
    k_memories=10,
)
chat = Chat(user_name="Mark", agent_name="Apiana", perceptor=perceptor)

def play_audio(text):

def do_chat(message, history):
    result = ""
    async for chunk in chat.run():
        result += chunk
        yield result
        play_audio(chunk)

demo = gr.ChatInterface(
    fn=do_chat, 
    type="messages"
).launch()

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7875,
        share=False,
    )