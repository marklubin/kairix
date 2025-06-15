import logging
import os
from collections import deque
from datetime import datetime

import gradio as gr
from agents import Runner
from cognition_engine.perceptor.conversation_remembering_perceptor import (
    ConversationRememberingPerceptor,
)
from elevenlabs import VoiceSettings
from elevenlabs.client import AsyncElevenLabs, ElevenLabs

from kairix_engine.basic_chat import Chat
from kairix_engine.summary_store import SummaryStore

NEO4J_URL = "bolt://neo4j:password@cayucos.thrush-escalator.ts.net:7687"

# Configure logging
logging.basicConfig(level=logging.WARNING)
logging.getLogger("kairix_engine").setLevel(logging.INFO)
logging.getLogger("cognition_engine").setLevel(logging.INFO)

# Initialize ElevenLabs clients
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = "0NkECxcbkydDMspBKvQp"  # From eleven.py
elevenlabs_client = None
async_elevenlabs_client = None

# Error log buffer for UI
error_logs = deque(maxlen=100)

if ELEVENLABS_API_KEY:
    elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    async_elevenlabs_client = AsyncElevenLabs(api_key=ELEVENLABS_API_KEY)
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


def log_error(error_msg: str):
    """Log error to both logging system and UI error buffer."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted_error = f"[{timestamp}] {error_msg}"
    logging.error(error_msg)
    error_logs.append(formatted_error)


async def text_to_speech_stream(text: str):
    """Stream text to speech and yield audio chunks immediately."""
    if not async_elevenlabs_client:
        return
    
    try:
        # Use the fastest model with optimized settings
        audio_stream = await async_elevenlabs_client.text_to_speech.stream(
            voice_id=VOICE_ID,
            optimize_streaming_latency="0",  # Maximum optimization
            output_format="mp3_22050_32",
            text=text,
            model_id="eleven_flash_v2_5",  # Fastest model (~75ms latency)
            voice_settings=VoiceSettings(
                stability=0.5,  # Recommended default
                similarity_boost=0.75,  # Recommended default
                style=0.0,  # Keep at 0 for lower latency
                use_speaker_boost=False,  # Disable for lower latency
            ),
        )
        
        # Yield chunks immediately as they arrive
        async for chunk in audio_stream:
            if chunk:
                yield chunk
                
    except Exception as e:
        error_msg = f"Error in text-to-speech: {e!s}"
        log_error(error_msg)


async def respond(message, history, enable_voice):
    await ensure_initialized()
    """Stream responses from the chat engine"""
    history = history or []
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": ""})
    
    full_response = ""
    
    # Stream text and optionally convert to audio
    if enable_voice and async_elevenlabs_client:
        # Stream each chunk directly to TTS without buffering
        async for chunk in chat.run(message):
            full_response += chunk
            history[-1]["content"] = full_response
            
            # Start TTS streaming immediately for each chunk
            audio_data = b""
            async for audio_chunk in text_to_speech_stream(chunk):
                audio_data += audio_chunk
            
            # Yield update with audio if available
            if audio_data:
                yield "", history, (22050, audio_data), True, get_error_logs()
            else:
                yield "", history, None, True, get_error_logs()
        
        # Final update
        yield "", history, None, False, get_error_logs()
    else:
        # No voice - just stream text
        async for chunk in chat.run(message):
            full_response += chunk
            history[-1]["content"] = full_response
            yield "", history, None, False, get_error_logs()


def get_error_logs():
    """Get formatted error logs for display."""
    if error_logs:
        return "\n".join(error_logs)
    return "No errors logged."


# Create Gradio interface with tabs
with gr.Blocks(
    title="Kairix Chat",
    css="""
    .contain { max-width: 900px !important; }
    footer { display: none !important; }
    #component-0 { height: calc(100vh - 350px) !important; }
    .message-wrap { padding: 8px !important; }
    #streaming-indicator {
        display: inline-block;
        margin-left: 10px;
        color: #666;
    }
    #error-logs {
        font-family: monospace;
        font-size: 12px;
        background: #f5f5f5;
        padding: 10px;
        border-radius: 5px;
        max-height: 300px;
        overflow-y: auto;
    }
    .error-indicator {
        color: red;
        font-weight: bold;
        margin-left: 10px;
    }
    """
) as demo:
    with gr.Tabs():
        with gr.Tab("Chat"):
            with gr.Column():
                chatbot = gr.Chatbot(
                    height=450,
                    bubble_full_width=False,
                    avatar_images=(None, "🐝"),
                    show_label=False,
                    elem_id="component-0",
                    autoscroll=True,
                    type="messages",
                )
                
                # Audio player for voice output - now visible
                audio_output = gr.Audio(
                    visible=True,
                    autoplay=True,
                    elem_id="audio-player",
                    label="Voice Output",
                    show_label=True,
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
                    error_indicator = gr.HTML(
                        value="",
                        elem_classes="error-indicator"
                    )
                
                with gr.Row():
                    msg = gr.Textbox(
                        placeholder=(
                            "Message Apiana... "
                            "(Enter to send, Shift+Enter for new line)"
                        ),
                        lines=1,
                        max_lines=3,
                        show_label=False,
                        autofocus=True,
                    )
                    
                    clear = gr.Button("Clear", scale=0, min_width=60)
        
        with gr.Tab("Logs"):
            gr.Markdown("### Error Logs")
            error_log_display = gr.Textbox(
                value=get_error_logs(),
                label="System Logs",
                lines=15,
                max_lines=20,
                elem_id="error-logs",
                interactive=False,
            )
            refresh_logs = gr.Button("Refresh Logs", scale=0)
    
    # Handle message submission with streaming
    def update_streaming_indicator(is_streaming):
        return "🎵 Streaming..." if is_streaming else ""
    
    def check_for_errors(logs):
        """Check if there are recent errors and update indicator."""
        if logs != "No errors logged." and len(logs.split('\n')) > 0:
            # Check if there's a recent error (in the last line)
            last_line = logs.split('\n')[-1]
            if last_line and not last_line.startswith("No errors"):
                return '<span class="error-indicator">⚠️ Error</span>'
        return ""
    
    msg.submit(
        respond, 
        [msg, chatbot, voice_toggle], 
        [msg, chatbot, audio_output, streaming_indicator, error_log_display],
        queue=True
    ).then(
        lambda: gr.update(value=""),
        None,
        msg
    )
    
    streaming_indicator.change(
        update_streaming_indicator,
        streaming_indicator,
        streaming_indicator
    )
    
    error_log_display.change(
        check_for_errors,
        error_log_display,
        error_indicator
    )
    
    clear.click(
        lambda: (None, None, None, "", get_error_logs()), 
        outputs=[msg, chatbot, audio_output, streaming_indicator, error_log_display]
    )
    
    refresh_logs.click(
        lambda: get_error_logs(),
        outputs=[error_log_display]
    )


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
    )