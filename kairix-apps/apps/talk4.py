from kairix_core.runtime.logging import LoggingRuntime

logger = LoggingRuntime().logger

import asyncio
import json
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
current_model = "gpt-4"


def create_message_display(msg):
    """Format message with timestamp for display."""
    timestamp = msg.get('timestamp', '')
    if timestamp:
        try:
            dt = datetime.fromisoformat(timestamp)
            time_str = dt.strftime('%I:%M %p').lstrip('0')
        except:
            time_str = ''
    else:
        time_str = ''
    
    content = msg['content']
    
    # Return formatted message with metadata
    return {
        'role': msg['role'],
        'content': content,
        'metadata': {'time': time_str}
    }


async def process_audio(audio_data, history_json):
    """Process audio and maintain history."""
    if audio_data is None:
        return None, history_json, history_json
    
    # Parse history
    try:
        full_history = json.loads(history_json) if history_json else []
    except:
        full_history = []
    
    sample_rate, audio_array = audio_data
    
    try:
        from fastrtc import get_stt_model
        stt = get_stt_model()
        
        # Transcribe
        prompt = stt.stt((sample_rate, audio_array))
        logger.info(f"Transcribed: {prompt}")
        
        if not prompt or prompt.strip() == "":
            return None, history_json, history_json
        
        # Add timestamped user message
        user_msg = {
            "role": "user",
            "content": prompt,
            "timestamp": datetime.now().isoformat()
        }
        full_history.append(user_msg)
        
        # Get response
        response_text = ""
        async for full, chunk in persona.react(Stimulus(prompt, StimulusType.user_message)):
            response_text = full
        
        # Add timestamped assistant message
        assistant_msg = {
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now().isoformat()
        }
        full_history.append(assistant_msg)
        
        # Generate audio
        audio_chunks = []
        async for audio_chunk in tts.stream_tts(response_text):
            audio_chunks.append(audio_chunk)
        
        # Update history JSON
        history_json = json.dumps(full_history)
        
        # Return audio and updated history
        if audio_chunks:
            combined_audio = np.concatenate(audio_chunks)
            return (24000, combined_audio), history_json, history_json
        
        return None, history_json, history_json
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        error_msg = {
            "role": "assistant",
            "content": f"Error: {e!s}",
            "timestamp": datetime.now().isoformat()
        }
        full_history.append(error_msg)
        history_json = json.dumps(full_history)
        return None, history_json, history_json


def format_chat_display(history_json):
    """Format last 20 messages for display with timestamps."""
    try:
        full_history = json.loads(history_json) if history_json else []
        # Get last 20 messages
        display_messages = full_history[-20:]
        
        # Format for display
        formatted = []
        for msg in display_messages:
            formatted_msg = create_message_display(msg)
            formatted.append(formatted_msg)
        
        return formatted
    except:
        return []


def create_interface():
    """Create interface with chat history and timestamps."""
    
    custom_css = """
    .message {
        position: relative;
        margin-bottom: 12px;
    }
    
    .message .time {
        font-size: 0.75em;
        color: #888;
        margin-top: 4px;
    }
    
    /* Custom timestamp display */
    .message.user .time {
        text-align: right;
    }
    
    .message.bot .time {
        text-align: left;
    }
    """
    
    with gr.Blocks(title="Kairix Voice Assistant", css=custom_css) as demo:
        gr.Markdown("# Kairix Voice Assistant")
        gr.Markdown("🎤 **Hold SPACE** to record | 💬 Chat history saved locally")
        
        # Hidden state for full history JSON
        history_json = gr.State("")
        
        # Create toolbar with model change handler
        def handle_model_change(new_model):
            global current_model
            current_model = new_model
            logger.info(f"Model changed to: {new_model}")
            # The JavaScript will detect this change and load appropriate history
            return new_model
        
        toolbar, model_selector = create_slideout_toolbar(
            default_model=current_model,
            on_model_change=handle_model_change
        )
        
        with gr.Row():
            with gr.Column():
                audio_input = gr.Audio(
                    sources=["microphone"],
                    type="numpy",
                    label="Voice Input (Hold SPACE)"
                )
                
                audio_output = gr.Audio(
                    label="Response",
                    type="numpy",
                    autoplay=True
                )
            
            with gr.Column():
                # Chat display with custom rendering
                chatbot = gr.Chatbot(
                    label="Conversation",
                    type="messages",
                    height=500,
                    show_copy_button=True,
                    elem_id="chatbot-display"
                )
                
                with gr.Row():
                    clear_btn = gr.Button("Clear Chat")
                    export_btn = gr.Button("Export History")
                
                # Hidden download component
                download = gr.File(visible=False)
        
        # Audio processing
        audio_input.stop_recording(
            fn=process_audio,
            inputs=[audio_input, history_json],
            outputs=[audio_output, history_json, gr.State()]
        ).then(
            fn=format_chat_display,
            inputs=[history_json],
            outputs=[chatbot]
        )
        
        # Clear chat
        def clear_chat():
            return None, "", [], None
            
        clear_btn.click(
            fn=clear_chat,
            outputs=[audio_input, history_json, chatbot, audio_output]
        )
        
        # Export history
        def export_history(history_json):
            if not history_json:
                return None
            
            # Create formatted export
            try:
                history = json.loads(history_json)
                export_text = "Kairix Chat Export\n" + "="*50 + "\n\n"
                
                for msg in history:
                    timestamp = msg.get('timestamp', '')
                    if timestamp:
                        try:
                            dt = datetime.fromisoformat(timestamp)
                            time_str = dt.strftime('%Y-%m-%d %I:%M %p')
                        except:
                            time_str = timestamp
                    else:
                        time_str = 'Unknown time'
                    
                    role = msg['role'].upper()
                    content = msg['content']
                    
                    export_text += f"[{time_str}] {role}:\n{content}\n\n"
                
                # Save to file
                filename = f"kairix_chat_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(filename, 'w') as f:
                    f.write(export_text)
                
                return filename
            except Exception as e:
                logger.error(f"Export error: {e}")
                return None
        
        export_btn.click(
            fn=export_history,
            inputs=[history_json],
            outputs=[download]
        )
        
        # JavaScript for persistence and PTT
        demo.load(js="""
        () => {
            let currentModel = 'gpt-4';
            
            function getStorageKey() {
                const modelDropdown = document.querySelector('#hidden-model-dropdown input');
                const model = (modelDropdown && modelDropdown.value) || currentModel;
                return 'kairix_chat_history_' + window.location.origin + '_' + model;
            }
            
            // Load history on startup
            function loadHistory() {
                try {
                    const stored = localStorage.getItem(getStorageKey());
                    if (stored) {
                        // Will be picked up by Gradio state
                        return stored;
                    }
                } catch (e) {
                    console.error('Failed to load history:', e);
                }
                return '';
            }
            
            // Save history whenever it updates
            window.saveHistory = function(historyJson) {
                try {
                    if (historyJson) {
                        localStorage.setItem(getStorageKey(), historyJson);
                    }
                } catch (e) {
                    console.error('Failed to save history:', e);
                }
            };
            
            // Clear storage when clear button clicked
            document.addEventListener('click', (e) => {
                if (e.target.textContent === 'Clear Chat') {
                    try {
                        localStorage.removeItem(getStorageKey());
                    } catch (e) {
                        console.error('Failed to clear storage:', e);
                    }
                }
            });
            
            // Listen for model changes
            setTimeout(() => {
                const modelDropdown = document.querySelector('#hidden-model-dropdown input');
                if (modelDropdown) {
                    // Save current model
                    currentModel = modelDropdown.value || currentModel;
                    
                    // Listen for changes
                    const observer = new MutationObserver(() => {
                        const newModel = modelDropdown.value;
                        if (newModel && newModel !== currentModel) {
                            currentModel = newModel;
                            // Load history for new model
                            const newHistory = loadHistory();
                            // Update the history state
                            if (window.gradio_config) {
                                // This will trigger a state update in Gradio
                                console.log('Switched to model:', currentModel);
                                // Return the new history to update the state
                                window.loadedHistory = newHistory;
                            }
                        }
                    });
                    
                    observer.observe(modelDropdown, {
                        attributes: true,
                        attributeFilter: ['value']
                    });
                }
            }, 1000);
            
            // Spacebar PTT
            let isRecording = false;
            document.addEventListener('keydown', (e) => {
                if (e.code === 'Space' && !isRecording && 
                    e.target.tagName !== 'INPUT' && 
                    e.target.tagName !== 'TEXTAREA') {
                    e.preventDefault();
                    isRecording = true;
                    const recordBtn = document.querySelector('.record-button');
                    if (recordBtn) recordBtn.click();
                }
            });
            
            document.addEventListener('keyup', (e) => {
                if (e.code === 'Space' && isRecording) {
                    e.preventDefault();
                    isRecording = false;
                    const stopBtn = document.querySelector('.stop-button');
                    if (stopBtn) stopBtn.click();
                }
            });
            
            // Custom message rendering with timestamps
            setInterval(() => {
                const messages = document.querySelectorAll('.message');
                messages.forEach(msg => {
                    if (!msg.querySelector('.time')) {
                        const metadata = msg.getAttribute('data-metadata');
                        if (metadata) {
                            try {
                                const meta = JSON.parse(metadata);
                                if (meta.time) {
                                    const timeDiv = document.createElement('div');
                                    timeDiv.className = 'time';
                                    timeDiv.textContent = meta.time;
                                    msg.appendChild(timeDiv);
                                }
                            } catch (e) {}
                        }
                    }
                });
            }, 100);
            
            return loadHistory();
        }
        """, outputs=[history_json])
        
        # Auto-save history on updates
        history_json.change(
            fn=None,
            inputs=[history_json],
            js="(h) => { window.saveHistory(h); return h; }"
        )
    
    return demo


async def main():
    agent_runtime = AgentRuntime()
    
    async with agent_runtime.mcp_server:
        demo = create_interface()
        demo.launch(server_port=8000)


if __name__ == "__main__":
    asyncio.run(main())