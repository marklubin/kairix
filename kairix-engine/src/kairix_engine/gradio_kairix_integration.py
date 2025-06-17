"""
Integration example showing how to stream logs from Kairix engine to Gradio interface.
"""

import asyncio
import logging
from typing import TYPE_CHECKING

import gradio as gr

from kairix_engine.engine import KairixEngine
from kairix_engine.gradio_log_streamer import LogStreamer, QueueHandler

if TYPE_CHECKING:
    from kairix_engine.basic_chat import Chat


class KairixGradioInterface:
    """Gradio interface for Kairix engine with real-time log streaming."""
    
    def __init__(self):
        self.log_streamer = LogStreamer(max_logs=2000)
        self.chat: Chat | None = None
        self.engine: KairixEngine | None = None
        self.setup_logging()
        
    def setup_logging(self):
        """Configure logging for Kairix components."""
        # Get loggers for Kairix components
        kairix_logger = logging.getLogger("kairix_engine")
        cognition_logger = logging.getLogger("cognition_engine")
        
        # Create queue handler
        handler = QueueHandler(self.log_streamer.log_queue)
        handler.setFormatter(
            logging.Formatter('[%(asctime)s] %(name)s - %(levelname)s - %(message)s')
        )
        
        # Add handler to Kairix loggers
        for logger in [kairix_logger, cognition_logger]:
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            
    def initialize_kairix(self, user_id: str = "gradio_user") -> str:
        """Initialize Kairix engine and chat."""
        try:
            self.log_streamer.add_log("Initializing Kairix Engine...", "INFO", "KAIRIX")
            
            # Initialize engine
            self.engine = KairixEngine()
            self.log_streamer.add_log("Engine initialized", "INFO", "KAIRIX")
            
            # Initialize chat using the engine's factory method
            self.chat = KairixEngine.get_chat_for_environment()
            self.log_streamer.add_log(
                f"Chat initialized for user: {user_id}", "INFO", "KAIRIX"
            )
            
            return "✅ Kairix initialized successfully"
            
        except Exception as e:
            error_msg = f"Failed to initialize Kairix: {e!s}"
            self.log_streamer.add_log(error_msg, "ERROR", "KAIRIX")
            return f"❌ {error_msg}"
            
    def process_message_async(
        self, message: str, history: list[list[str]]
    ) -> tuple[str, list[list[str]]]:
        """Process message through Kairix engine with async support."""
        if not self.chat:
            self.log_streamer.add_log("Chat not initialized", "ERROR", "KAIRIX")
            history.append([message, "Please initialize Kairix first"])
            return "", history
            
        try:
            self.log_streamer.add_log(
                f"Processing message: {message}", "INFO", "KAIRIX"
            )
            
            # Run async chat method in thread
            def run_chat():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    # Collect all chunks from the async iterator
                    async def collect_response():
                        chunks = []
                        if self.chat is not None:
                            async for chunk in self.chat.chat(message):
                                chunks.append(chunk)
                        return ''.join(chunks)
                    
                    return loop.run_until_complete(collect_response())
                finally:
                    loop.close()
                    
            # Execute in thread to avoid blocking
            response = run_chat()
            
            self.log_streamer.add_log(
                f"Generated response: {response}", "INFO", "KAIRIX"
            )
            
            # Update history
            history.append([message, response])
            
            return "", history
            
        except Exception as e:
            error_msg = f"Error processing message: {e!s}"
            self.log_streamer.add_log(error_msg, "ERROR", "KAIRIX")
            history.append([message, f"Error: {error_msg}"])
            return "", history
            
    def create_interface(self) -> gr.Blocks:
        """Create the Gradio interface."""
        with gr.Blocks(
            title="Kairix Engine - Gradio Interface",
            theme=gr.themes.Soft(
                primary_hue="indigo",
                secondary_hue="gray",
            ),
            css="""
            #log-output {
                font-family: monospace;
                font-size: 12px;
                background-color: #1e1e1e;
                color: #d4d4d4;
            }
            .gr-button-primary {
                background-color: #4f46e5 !important;
            }
            """
        ) as demo:
            gr.Markdown(
                """
                # 🤖 Kairix Engine Interface
                
                Real-time chat interface with log streaming for the Kairix 
                conversational AI engine.
                """
            )
            
            # Status row
            with gr.Row():
                status_display = gr.Markdown("⚠️ Kairix not initialized")
                init_btn = gr.Button("Initialize Kairix", variant="primary")
                
            with gr.Row():
                with gr.Column(scale=2):
                    # Chat interface
                    chatbot = gr.Chatbot(
                        height=500,
                        label="Conversation",
                        show_copy_button=True,
                        avatar_images=(None, "🤖"),
                        bubble_full_width=False,
                    )
                    
                    with gr.Row():
                        msg = gr.Textbox(
                            label="Message",
                            placeholder="Type your message here...",
                            lines=2,
                            autofocus=True,
                            elem_id="message-input"
                        )
                        
                    with gr.Row():
                        send_btn = gr.Button("Send", variant="primary", scale=1)
                        clear_btn = gr.Button("Clear", scale=1)
                        
                with gr.Column(scale=1):
                    # Logs section
                    gr.Markdown("### 📋 System Logs")
                    
                    log_display = gr.Textbox(
                        label="",
                        lines=25,
                        max_lines=30,
                        interactive=False,
                        elem_id="log-output",
                        show_label=False,
                        autoscroll=True
                    )
                    
                    with gr.Row():
                        clear_logs_btn = gr.Button("Clear Logs", size="sm")
                        export_logs_btn = gr.Button("Export Logs", size="sm")
                        
                    # Log level filter
                    log_level = gr.Radio(
                        choices=["ALL", "INFO", "WARNING", "ERROR"],
                        value="ALL",
                        label="Log Level Filter",
                        elem_id="log-level-filter"
                    )
                    
            # Configuration section
            with gr.Accordion("⚙️ Configuration", open=False):
                user_id_input = gr.Textbox(
                    label="User ID",
                    value="gradio_user",
                    placeholder="Enter user ID..."
                )
                
                with gr.Row():
                    gr.Markdown(
                        """
                        **Environment Variables:**
                        - `OPENAI_API_KEY`: Required for OpenAI models
                        - `ANTHROPIC_API_KEY`: Required for Claude models
                        - `MODEL_NAME`: Model to use (default: gpt-4)
                        """
                    )
                    
            # Helper functions
            def init_kairix(user_id: str) -> tuple[str, str]:
                """Initialize Kairix and update status."""
                result = self.initialize_kairix(user_id)
                if "successfully" in result:
                    return result, "✅ Kairix initialized and ready"
                return result, "⚠️ Kairix initialization failed"
                
            def update_logs(log_level: str) -> str:
                """Update log display with filtering."""
                all_logs = self.log_streamer.get_all_logs()
                
                if log_level == "ALL":
                    return all_logs
                    
                # Filter logs by level
                filtered_lines = []
                for line in all_logs.split('\n'):
                    if log_level in line or f"[{log_level}]" in line:
                        filtered_lines.append(line)
                        
                return '\n'.join(filtered_lines)
                
            def clear_logs() -> str:
                """Clear logs and return empty display."""
                self.log_streamer.clear_logs()
                self.log_streamer.add_log("Logs cleared", "INFO", "SYSTEM")
                return self.log_streamer.get_all_logs()
                
            def export_logs() -> str:
                """Export logs to file."""
                import tempfile
                from datetime import datetime
                datetime.now().strftime("%Y%m%d_%H%M%S")
                
                content = self.log_streamer.get_all_logs()
                # Create temporary file and return its path
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write(content)
                    return f.name
                
            # Event handlers
            init_btn.click(
                init_kairix,
                inputs=[user_id_input],
                outputs=[init_btn, status_display]
            )
            
            msg.submit(
                self.process_message_async,
                inputs=[msg, chatbot],
                outputs=[msg, chatbot]
            )
            
            send_btn.click(
                self.process_message_async,
                inputs=[msg, chatbot],
                outputs=[msg, chatbot]
            )
            
            clear_btn.click(
                lambda: ([], ""),
                None,
                [chatbot, msg]
            )
            
            clear_logs_btn.click(clear_logs, None, log_display)
            export_logs_btn.click(export_logs, None, None)
            
            # Auto-refresh logs every 500ms with filtering
            demo.load(
                update_logs,
                inputs=[log_level],
                outputs=log_display,
                every=0.5
            )
            
            # Update logs when filter changes
            log_level.change(
                update_logs,
                inputs=[log_level],
                outputs=log_display
            )
            
        return demo  # type: ignore[no-any-return]


def main():
    """Launch the Kairix Gradio interface."""
    interface = KairixGradioInterface()
    demo = interface.create_interface()
    
    # Add startup log
    interface.log_streamer.add_log(
        "Kairix Gradio Interface started",
        "INFO",
        "SYSTEM"
    )
    
    # Launch with queue for better performance
    demo.queue(max_size=50)
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        debug=True
    )


if __name__ == "__main__":
    main()