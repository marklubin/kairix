"""
Gradio application with real-time log streaming from Python processes.
This module demonstrates how to stream logs from background processes to a Gradio
web interface.
"""

import logging
import queue
import subprocess
import threading
import time
from datetime import datetime

import gradio as gr


class LogStreamer:
    """Manages log streaming from multiple sources to Gradio interface."""
    
    def __init__(self, max_logs: int = 1000):
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.logs: list[str] = []
        self.max_logs = max_logs
        self.is_running = True
        
        # Set up logging to capture Python logs
        self.setup_logging()
        
    def setup_logging(self) -> None:
        """Configure Python logging to send logs to our queue."""
        handler = QueueHandler(self.log_queue)
        handler.setFormatter(
            logging.Formatter('[%(asctime)s] %(name)s - %(levelname)s - %(message)s')
        )
        
        # Add handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
        
    def add_log(self, message: str, level: str = "INFO", source: str = "SYSTEM") -> None:
        """Add a log entry to the queue."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] [{source}] [{level}] {message}"
        self.log_queue.put(log_entry)
        
    def get_new_logs(self) -> list[str]:
        """Get all new logs from the queue."""
        new_logs = []
        while not self.log_queue.empty():
            try:
                log = self.log_queue.get_nowait()
                new_logs.append(log)
                self.logs.append(log)
                
                # Keep only the most recent logs
                if len(self.logs) > self.max_logs:
                    self.logs = self.logs[-self.max_logs:]
                    
            except queue.Empty:
                break
                
        return new_logs
    
    def get_all_logs(self) -> str:
        """Get all logs as a single string."""
        return "\n".join(self.logs)
    
    def clear_logs(self) -> None:
        """Clear all stored logs."""
        self.logs = []
        # Clear the queue
        while not self.log_queue.empty():
            try:
                self.log_queue.get_nowait()
            except queue.Empty:
                break


class QueueHandler(logging.Handler):
    """Custom logging handler that sends logs to a queue."""
    
    def __init__(self, log_queue: queue.Queue):
        super().__init__()
        self.log_queue = log_queue
        
    def emit(self, record: logging.LogRecord) -> None:
        log_entry = self.format(record)
        self.log_queue.put(log_entry)


class ProcessLogStreamer:
    """Streams logs from a subprocess to the log queue."""
    
    def __init__(self, log_streamer: LogStreamer):
        self.log_streamer = log_streamer
        self.process: subprocess.Popen[str] | None = None
        self.thread: threading.Thread | None = None
        
    def start_process(self, command: list[str], cwd: str | None = None) -> None:
        """Start a subprocess and stream its output."""
        if self.process and self.process.poll() is None:
            self.log_streamer.add_log("Process already running", "WARNING", "PROCESS")
            return
            
        try:
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                cwd=cwd
            )
            
            # Start threads to read stdout and stderr
            self.thread = threading.Thread(
                target=self._stream_output,
                args=(self.process,),
                daemon=True
            )
            self.thread.start()
            
            self.log_streamer.add_log(
                f"Started process: {' '.join(command)}", 
                "INFO", 
                "PROCESS"
            )
            
        except Exception as e:
            self.log_streamer.add_log(
                f"Failed to start process: {e!s}", 
                "ERROR", 
                "PROCESS"
            )
            
    def _stream_output(self, process: subprocess.Popen[str]) -> None:
        """Stream output from the process to the log queue."""
        # Stream stdout
        if process.stdout:
            for line in iter(process.stdout.readline, ''):
                if line:
                    self.log_streamer.add_log(line.strip(), "INFO", "STDOUT")
                
        # Stream stderr
        if process.stderr:
            for line in iter(process.stderr.readline, ''):
                if line:
                    self.log_streamer.add_log(line.strip(), "ERROR", "STDERR")
                
        # Process finished
        return_code = process.wait()
        self.log_streamer.add_log(
            f"Process exited with code: {return_code}", 
            "INFO" if return_code == 0 else "ERROR", 
            "PROCESS"
        )
        
    def stop_process(self) -> None:
        """Stop the running process."""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.log_streamer.add_log("Process terminated", "INFO", "PROCESS")


def create_gradio_app(
    log_streamer: LogStreamer, process_streamer: ProcessLogStreamer
) -> gr.Blocks:
    """Create the Gradio interface with log streaming."""
    
    with gr.Blocks(title="Log Streaming Demo", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# Real-time Log Streaming Demo")
        gr.Markdown(
            "This demo shows how to stream logs from Python processes to a Gradio "
            "interface."
        )
        
        with gr.Row():
            with gr.Column(scale=2):
                # Chat interface
                chatbot = gr.Chatbot(height=400, label="Chat Interface")
                msg = gr.Textbox(
                    label="Message",
                    placeholder="Type a message to trigger log events...",
                    lines=1
                )
                
                with gr.Row():
                    send_btn = gr.Button("Send", variant="primary")
                    clear_chat_btn = gr.Button("Clear Chat")
                    
            with gr.Column(scale=1):
                # Log display
                log_display = gr.Textbox(
                    label="System Logs",
                    lines=20,
                    max_lines=25,
                    interactive=False,
                    elem_id="log-output",
                    placeholder="Logs will appear here...",
                    autoscroll=True
                )
                
                with gr.Row():
                    clear_logs_btn = gr.Button("Clear Logs", size="sm")
                    export_logs_btn = gr.Button("Export Logs", size="sm")
                    
        with gr.Row():
            # Process control
            gr.Markdown("### Process Control")
            
        with gr.Row():
            command_input = gr.Textbox(
                label="Command",
                value=(
                    "python -c \"import time; "
                    "[print(f'Log {i}') or time.sleep(1) for i in range(10)]\""
                ),
                placeholder="Enter command to run..."
            )
            
        with gr.Row():
            start_process_btn = gr.Button("Start Process", variant="primary")
            stop_process_btn = gr.Button("Stop Process", variant="stop")
            
        # Example commands
        gr.Examples(
            examples=[
                [
                    "python -c \"import time; "
                    "[print(f'Log {i}') or time.sleep(1) for i in range(10)]\""
                ],
                [
                    "python -c \"import logging; "
                    "logging.basicConfig(level=logging.INFO); "
                    "[logging.info(f'Processing item {i}') for i in range(5)]\""
                ],
                ["echo 'Hello from subprocess'"],
                ["ls -la"],
            ],
            inputs=command_input,
            label="Example Commands"
        )
        
        def process_message(
            message: str, history: list[list[str]]
        ) -> tuple[str, list[list[str]]]:
            """Process a chat message and generate logs."""
            log_streamer.add_log(f"Received message: {message}", "INFO", "CHAT")
            
            # Simulate some processing with logs
            log_streamer.add_log("Processing message...", "INFO", "CHAT")
            time.sleep(0.5)
            
            # Generate response
            response = f"Processed: {message}"
            log_streamer.add_log(f"Generated response: {response}", "INFO", "CHAT")
            
            # Update chat history
            history.append([message, response])
            
            return "", history
        
        def update_logs() -> str:
            """Get the latest logs."""
            return log_streamer.get_all_logs()
        
        def clear_logs() -> str:
            """Clear all logs."""
            log_streamer.clear_logs()
            log_streamer.add_log("Logs cleared", "INFO", "SYSTEM")
            return log_streamer.get_all_logs()
        
        def export_logs() -> str:
            """Export logs to a file."""
            datetime.now().strftime("%Y%m%d_%H%M%S")
            
            content = log_streamer.get_all_logs()
            
            # Create file in memory
            # Note: gr.File expects a string path, not bytes
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(content)
                return f.name
        
        def start_process(command: str) -> None:
            """Start a subprocess."""
            if not command:
                log_streamer.add_log("No command provided", "ERROR", "SYSTEM")
                return
                
            command_parts = command.split()
            process_streamer.start_process(command_parts)
            
        def stop_process() -> None:
            """Stop the running process."""
            process_streamer.stop_process()
            
        # Event handlers
        msg.submit(process_message, [msg, chatbot], [msg, chatbot])
        send_btn.click(process_message, [msg, chatbot], [msg, chatbot])
        clear_chat_btn.click(lambda: ([], ""), None, [chatbot, msg])
        
        clear_logs_btn.click(clear_logs, None, log_display)
        export_logs_btn.click(export_logs, None, None)
        
        start_process_btn.click(start_process, command_input, None)
        stop_process_btn.click(stop_process, None, None)
        
        # Auto-refresh logs every 500ms
        demo.load(update_logs, None, log_display, every=0.5)
        
    return demo  # type: ignore[no-any-return]


def main() -> None:
    """Run the Gradio app with log streaming."""
    # Initialize components
    log_streamer = LogStreamer(max_logs=1000)
    process_streamer = ProcessLogStreamer(log_streamer)
    
    # Add initial log
    log_streamer.add_log("Gradio app started", "INFO", "SYSTEM")
    
    # Create and launch the app
    demo = create_gradio_app(log_streamer, process_streamer)
    
    # Example of adding logs from the main thread
    def background_logger() -> None:
        """Example background task that generates logs."""
        counter = 0
        while True:
            time.sleep(10)
            counter += 1
            log_streamer.add_log(
                f"Background task heartbeat #{counter}", 
                "DEBUG", 
                "BACKGROUND"
            )
            
    # Start background logger
    bg_thread = threading.Thread(target=background_logger, daemon=True)
    bg_thread.start()
    
    # Launch the app
    demo.queue(max_size=100)
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        debug=True
    )


if __name__ == "__main__":
    main()