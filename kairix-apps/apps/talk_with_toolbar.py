from kairix_core.runtime.logging import LoggingRuntime

logger = LoggingRuntime().logger

import asyncio
from datetime import datetime

import gradio as gr
import numpy as np
from kairix_core.runtime.agent import AgentRuntime
from kairix_core.tts import ElevenLabsTTS
from kairix_core.types.cognition import Stimulus, StimulusType
from kairix_core.util.utils import get_or_raise

from kairix_apps.engine import KairixEngine
from kairix_apps.ui_components import create_slideout_toolbar

# Initialize components
elevenlabs_api_key = get_or_raise("ELEVENLABS_API_KEY")
tts = ElevenLabsTTS(api_key=elevenlabs_api_key)
persona = KairixEngine.conversational_persona_for_environment()

# Global state
current_model = "gpt-4"  # Default model


def format_message_with_timestamp(message):
    """Format a message with timestamp for display."""
    timestamp = message.get('timestamp', datetime.now().isoformat())
    
    # Parse timestamp and format for display
    try:
        dt = datetime.fromisoformat(timestamp)
        time_str = dt.strftime('%I:%M %p').lstrip('0')
    except:
        time_str = ''
    
    # Format message with timestamp
    content = message['content']
    role = message['role']
    
    if time_str:
        # Add timestamp as small grey text
        if role == 'user':
            return f"{content}\n<span style='font-size: 0.75em; color: #888;'>{time_str}</span>"
        else:
            return f"<span style='font-size: 0.75em; color: #888;'>{time_str}</span>\n{content}"
    return content


async def process_audio(audio_data, chat_history):
    """Process recorded audio through STT -> Persona -> TTS"""
    if audio_data is None:
        return None, chat_history
    
    sample_rate, audio_array = audio_data
    
    try:
        # Import STT model
        from fastrtc import get_stt_model
        stt = get_stt_model()
        
        # Transcribe audio
        prompt = stt.stt((sample_rate, audio_array))
        logger.info(f"Transcribed: {prompt}")
        logger.info(f"Using model: {current_model}")
        
        if not prompt or prompt.strip() == "":
            return None, chat_history
        
        # Create timestamped messages
        timestamp = datetime.now().isoformat()
        
        # Add user message
        user_msg = {
            "role": "user", 
            "content": prompt,
            "timestamp": timestamp
        }
        
        # Update chat history
        if chat_history is None:
            chat_history = []
        chat_history.append(user_msg)
        
        # Get response from persona
        response_text = ""
        async for full, chunk in persona.react(Stimulus(prompt, StimulusType.user_message)):
            response_text = full
        
        # Add assistant message with timestamp
        assistant_msg = {
            "role": "assistant", 
            "content": response_text,
            "timestamp": datetime.now().isoformat()
        }
        chat_history.append(assistant_msg)
        
        # Generate TTS audio
        audio_chunks = []
        async for audio_chunk in tts.stream_tts(response_text):
            audio_chunks.append(audio_chunk)
        
        if audio_chunks:
            combined_audio = np.concatenate(audio_chunks)
            return (24000, combined_audio), chat_history
        
        return None, chat_history
        
    except Exception as e:
        logger.error(f"Error processing audio: {e}", exc_info=True)
        error_msg = {
            "role": "assistant", 
            "content": f"Error: {e!s}",
            "timestamp": datetime.now().isoformat()
        }
        if chat_history is None:
            chat_history = []
        chat_history.append(error_msg)
        return None, chat_history


def create_interface():
    """Create Gradio interface with integrated toolbar"""
    
    # Custom CSS for timestamps and chat styling
    custom_css = """
    .gradio-container {
        position: relative;
    }
    
    /* Custom timestamp styling in chatbot */
    .message-wrap .message {
        line-height: 1.5;
    }
    
    .message-wrap .message span {
        display: inline-block;
    }
    """
    
    # JavaScript for chat history persistence
    history_js = """
    <script>
    let fullChatHistory = [];
    let currentEndpoint = window.location.origin;
    
    function getStorageKey() {
        const model = document.querySelector('#hidden-model-dropdown input')?.value || 'default';
        return `kairix_chat_${currentEndpoint}_${model}`;
    }
    
    function saveFullHistory(messages) {
        try {
            fullChatHistory = messages;
            localStorage.setItem(getStorageKey(), JSON.stringify(messages));
        } catch (e) {
            console.error('Failed to save chat history:', e);
        }
    }
    
    function loadFullHistory() {
        try {
            const key = getStorageKey();
            const stored = localStorage.getItem(key);
            if (stored) {
                fullChatHistory = JSON.parse(stored);
                return fullChatHistory.slice(-20); // Return last 20 messages
            }
        } catch (e) {
            console.error('Failed to load chat history:', e);
        }
        return [];
    }
    
    function clearHistory() {
        fullChatHistory = [];
        try {
            localStorage.removeItem(getStorageKey());
        } catch (e) {
            console.error('Failed to clear history:', e);
        }
    }
    
    // Listen for model changes to update storage key
    document.addEventListener('DOMContentLoaded', () => {
        setTimeout(() => {
            const modelDropdown = document.querySelector('#hidden-model-dropdown input');
            if (modelDropdown) {
                modelDropdown.addEventListener('change', () => {
                    // Load history for new model
                    const history = loadFullHistory();
                    // Update chatbot display
                    if (window.updateChatDisplay) {
                        window.updateChatDisplay(history);
                    }
                });
            }
        }, 1000);
    });
    </script>
    """
    
    with gr.Blocks(title="Kairix Assistant with Toolbar", css=custom_css, head=history_js) as demo:
        gr.Markdown("# Kairix Voice Assistant")
        gr.Markdown("🎤 **Hold SPACE** to record | 🔧 **Hover right edge** for settings")
        
        # Create the slideout toolbar
        def on_model_change(model):
            global current_model
            current_model = model
            logger.info(f"Model changed to: {model}")
            return model
        
        toolbar, model_selector = create_slideout_toolbar(
            model_options=[
                "gpt-4-turbo",
                "gpt-4", 
                "gpt-3.5-turbo",
                "claude-3-opus",
                "claude-3-sonnet",
                "llama-3-70b"
            ],
            default_model=current_model,
            on_model_change=on_model_change
        )
        
        with gr.Row():
            with gr.Column(scale=1):
                # Audio input
                audio_input = gr.Audio(
                    sources=["microphone"],
                    type="numpy",
                    label="Voice Input (Hold SPACE)",
                    elem_id="audio_input"
                )
                
                # Audio output
                audio_output = gr.Audio(
                    label="Response Audio",
                    type="numpy",
                    autoplay=True
                )
                
                # Current model display
                model_display = gr.Textbox(
                    label="Current Model",
                    value=current_model,
                    interactive=False
                )
            
            with gr.Column(scale=1):
                # Chat history with custom rendering
                chatbot = gr.Chatbot(
                    label="Conversation",
                    type="messages",
                    height=400,
                    render_markdown=True,
                    show_copy_button=True
                )
                
                clear_btn = gr.Button("Clear Chat")
        
        # Handle audio input
        audio_input.stop_recording(
            fn=process_audio,
            inputs=[audio_input, chatbot],
            outputs=[audio_output, chatbot]
        )
        
        # Update model display when changed
        model_selector.change(
            fn=lambda m: m,
            inputs=[model_selector],
            outputs=[model_display]
        )
        
        # Clear button with history clearing
        def clear_all():
            return None, [], current_model, None
            
        clear_btn.click(
            fn=clear_all,
            outputs=[audio_input, chatbot, model_display, audio_output]
        ).then(
            fn=None,
            js="() => { clearHistory(); }"
        )
        
        # JavaScript for spacebar PTT and history management
        demo.load(js="""
        () => {
            // Load chat history on startup
            const history = loadFullHistory();
            if (history.length > 0) {
                // Format messages for display
                const formattedHistory = history.map(msg => ({
                    ...msg,
                    content: msg.content // Timestamps will be added by Python
                }));
                
                // Update chatbot - Gradio will handle the update
                setTimeout(() => {
                    const chatbot = document.querySelector('.chatbot');
                    if (chatbot && window.gradio_config) {
                        // This will trigger Gradio to update with loaded history
                        console.log('Loaded', formattedHistory.length, 'messages from history');
                    }
                }, 500);
            }
            
            // Spacebar PTT functionality
            let isRecording = false;
            const audioInput = document.querySelector('#audio_input audio');
            const recordButton = document.querySelector('#audio_input button');
            
            document.addEventListener('keydown', (e) => {
                if (e.code === 'Space' && !isRecording && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
                    e.preventDefault();
                    isRecording = true;
                    if (recordButton) recordButton.click();
                }
            });
            
            document.addEventListener('keyup', (e) => {
                if (e.code === 'Space' && isRecording) {
                    e.preventDefault();
                    isRecording = false;
                    if (recordButton) recordButton.click();
                }
            });
            
            // Save history whenever chatbot updates
            window.updateChatDisplay = (messages) => {
                saveFullHistory(messages);
            };
            
            // Monitor chatbot changes
            const observer = new MutationObserver(() => {
                const messages = Array.from(document.querySelectorAll('.message')).map(el => {
                    const role = el.classList.contains('user') ? 'user' : 'assistant';
                    const content = el.querySelector('.message-text')?.textContent || el.textContent;
                    return { role, content, timestamp: new Date().toISOString() };
                });
                if (messages.length > 0) {
                    saveFullHistory(messages);
                }
            });
            
            setTimeout(() => {
                const chatbot = document.querySelector('.chatbot');
                if (chatbot) {
                    observer.observe(chatbot, { childList: true, subtree: true });
                }
            }, 1000);
            
            return history;
        }
        """)
    
    return demo


async def main():
    """Main entry point"""
    agent_runtime = AgentRuntime()
    
    async with agent_runtime.mcp_server:
        demo = create_interface()
        demo.launch(server_port=8000)


if __name__ == "__main__":
    asyncio.run(main())