import logging
import os

import gradio as gr
from agents import Runner
from cognition_engine.perceptor.conversation_remembering_perceptor import (
    ConversationRememberingPerceptor,
)
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

from kairix_engine.basic_chat import Chat
from kairix_engine.summary_store import SummaryStore

NEO4J_URL = "bolt://neo4j:password@cayucos.thrush-escalator.ts.net:7687"

# Configure logging
logging.basicConfig(level=logging.WARNING)
logging.getLogger("kairix_engine").setLevel(logging.INFO)
logging.getLogger("cognition_engine").setLevel(logging.INFO)

# Initialize ElevenLabs client
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = "0NkECxcbkydDMspBKvQp"  # From eleven.py
elevenlabs_client = None

if ELEVENLABS_API_KEY:
    elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
else:
    logging.warning("ELEVENLABS_API_KEY not set, voice feature will be disabled")

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

# Flag to track initialization
_initialized = False


async def ensure_initialized():
    """Ensure chat is initialized."""
    global _initialized
    if not _initialized:
        await chat.initialize()
        _initialized = True


def text_to_speech(text: str):
    """Convert text to speech and return audio bytes."""
    if not elevenlabs_client:
        return None
    
    try:
        # Perform the text-to-speech conversion
        response = elevenlabs_client.text_to_speech.convert(
            voice_id=VOICE_ID,
            optimize_streaming_latency="0",
            output_format="mp3_22050_32",
            text=text,
            model_id="eleven_multilingual_v2",
            voice_settings=VoiceSettings(
                stability=0.0,
                similarity_boost=1.0,
                style=0.0,
                use_speaker_boost=True,
            ),
        )
        
        # Collect audio chunks
        audio_data = b""
        for chunk in response:
            if chunk:
                audio_data += chunk
        
        return audio_data
                
    except Exception as e:
        logging.error(f"Error in text-to-speech: {e}")
        return None


async def respond(message, history, enable_voice):
    await ensure_initialized()
    """Stream responses from the chat engine"""
    history = history or []
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": ""})
    
    full_response = ""
    sentence_buffer = ""
    
    # Stream text chunks
    async for chunk in chat.run(message):
        full_response += chunk
        history[-1]["content"] = full_response
        
        # If voice is enabled, buffer sentences for TTS
        if enable_voice and elevenlabs_client:
            sentence_buffer += chunk
            
            # Check for sentence boundaries
            if any(punct in sentence_buffer for punct in ['.', '!', '?']):
                # Get the last complete sentence
                for punct in ['.', '!', '?']:
                    if punct in sentence_buffer:
                        parts = sentence_buffer.split(punct)
                        if len(parts) > 1:
                            complete_sentence = parts[0] + punct
                            sentence_buffer = punct.join(parts[1:])
                            
                            # Generate audio for complete sentence
                            audio_data = text_to_speech(complete_sentence.strip())
                            if audio_data:
                                yield "", history, (44100, audio_data), True
                            else:
                                yield "", history, None, True
                            break
                else:
                    yield "", history, None, True
            else:
                yield "", history, None, True
        else:
            yield "", history, None, False
    
    # Process any remaining text for TTS
    if enable_voice and elevenlabs_client and sentence_buffer.strip():
        audio_data = text_to_speech(sentence_buffer.strip())
        if audio_data:
            yield "", history, (44100, audio_data), False
        else:
            yield "", history, None, False
    else:
        yield "", history, None, False


# Create Gradio interface with custom CSS for compact layout
with gr.Blocks(
    title="Kairix Chat",
    css="""
    .contain { max-width: 900px !important; }
    footer { display: none !important; }
    #component-0 { height: calc(100vh - 300px) !important; }
    .message-wrap { padding: 8px !important; }
    #streaming-indicator {
        display: inline-block;
        margin-left: 10px;
        color: #666;
    }
    """
) as demo, gr.Column():
    chatbot = gr.Chatbot(
        height=450,
        bubble_full_width=False,
        avatar_images=(None, "🐝"),
        show_label=False,
        elem_id="component-0",
        autoscroll=True,
        type="messages",
    )
    
    # Audio player for voice output
    audio_output = gr.Audio(
        visible=False,
        autoplay=True,
        elem_id="audio-player"
    )
    
    # Voice controls and streaming indicator
    with gr.Row():
        voice_toggle = gr.Checkbox(
            label="🔊 Voice",
            value=bool(ELEVENLABS_API_KEY),
            scale=0,
            min_width=100,
            interactive=ELEVENLABS_API_KEY is not None
        )
        streaming_indicator = gr.HTML(
            value="",
            elem_id="streaming-indicator"
        )
    
    with gr.Row():
        msg = gr.Textbox(
            placeholder=(
                "Message Apiana... (Enter to send, Shift+Enter for new line)"
            ),
            lines=1,
            max_lines=3,
            show_label=False,
            autofocus=True,
        )
        
        clear = gr.Button("Clear", scale=0, min_width=60)
    
    # Handle message submission with streaming
    def update_streaming_indicator(is_streaming):
        return "🎵 Streaming..." if is_streaming else ""
    
    msg.submit(
        respond, 
        [msg, chatbot, voice_toggle], 
        [msg, chatbot, audio_output, streaming_indicator],
        queue=True
    ).then(
        lambda: gr.update(value=""),
        None,
        streaming_indicator
    )
    
    streaming_indicator.change(
        update_streaming_indicator,
        streaming_indicator,
        streaming_indicator
    )
    
    clear.click(
        lambda: (None, None, None, ""), 
        outputs=[msg, chatbot, audio_output, streaming_indicator]
    )


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
    )