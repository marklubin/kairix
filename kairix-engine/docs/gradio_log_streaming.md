# Gradio Log Streaming Guide

This guide explains how to stream logs from Python processes to a Gradio web interface in real-time.

## Overview

The log streaming system consists of three main components:

1. **LogStreamer**: Manages a queue of log messages and provides thread-safe access
2. **QueueHandler**: Custom logging handler that sends Python logs to the queue
3. **ProcessLogStreamer**: Captures output from subprocesses and sends to the log queue

## Quick Start

### Basic Demo

```bash
# Run the basic log streaming demo
uv run python launch_gradio.py

# Or with custom port
uv run python launch_gradio.py --port 8080
```

### Kairix Integration

```bash
# Run the Kairix interface with log streaming
uv run python launch_gradio.py --kairix
```

## Key Features

### 1. Real-time Log Updates
- Logs update every 500ms automatically
- No manual refresh needed
- Efficient queue-based system

### 2. Multiple Log Sources
- Python logging module integration
- Subprocess stdout/stderr capture
- Custom log messages from any part of your code

### 3. Log Management
- Filter by log level (ALL, INFO, WARNING, ERROR)
- Clear logs
- Export logs to file with timestamp

### 4. Process Control
- Start/stop external processes
- View real-time output from subprocesses
- Handle both stdout and stderr

## Integration Examples

### Basic Integration

```python
from src.kairix_engine.gradio_log_streamer import LogStreamer

# Create log streamer
log_streamer = LogStreamer(max_logs=1000)

# Add logs from anywhere
log_streamer.add_log("Starting process", "INFO", "MYAPP")
log_streamer.add_log("Error occurred", "ERROR", "MYAPP")

# Get logs for display
all_logs = log_streamer.get_all_logs()
```

### Python Logging Integration

```python
import logging
from src.kairix_engine.gradio_log_streamer import LogStreamer, QueueHandler

# Create log streamer
log_streamer = LogStreamer()

# Set up Python logging
logger = logging.getLogger("myapp")
handler = QueueHandler(log_streamer.log_queue)
handler.setFormatter(logging.Formatter('[%(asctime)s] %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Now all Python logs go to the queue
logger.info("This will appear in Gradio")
logger.error("This error too")
```

### Subprocess Integration

```python
from src.kairix_engine.gradio_log_streamer import LogStreamer, ProcessLogStreamer

# Create streamers
log_streamer = LogStreamer()
process_streamer = ProcessLogStreamer(log_streamer)

# Start a process
process_streamer.start_process(["python", "my_script.py"])

# Logs from the process will automatically stream to the queue
```

### Custom Gradio App

```python
import gradio as gr
from src.kairix_engine.gradio_log_streamer import LogStreamer

log_streamer = LogStreamer()

with gr.Blocks() as demo:
    # Your UI components
    logs = gr.Textbox(label="Logs", lines=20, interactive=False)
    
    # Update function
    def get_logs():
        return log_streamer.get_all_logs()
    
    # Auto-refresh logs
    demo.load(get_logs, None, logs, every=0.5)

demo.launch()
```

## Advanced Usage

### Custom Log Formatting

```python
def add_custom_log(log_streamer, message, level="INFO"):
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    formatted = f"[{timestamp}] [CUSTOM] [{level}] {message}"
    log_streamer.log_queue.put(formatted)
```

### Thread-Safe Background Tasks

```python
import threading

def background_task(log_streamer):
    while True:
        # Do work
        log_streamer.add_log("Background task running", "DEBUG", "BACKGROUND")
        time.sleep(10)

# Start in thread
thread = threading.Thread(target=background_task, args=(log_streamer,), daemon=True)
thread.start()
```

### Async Integration

```python
import asyncio

async def async_task(log_streamer):
    log_streamer.add_log("Starting async task", "INFO", "ASYNC")
    await asyncio.sleep(1)
    log_streamer.add_log("Async task complete", "INFO", "ASYNC")

# Run in event loop
asyncio.run(async_task(log_streamer))
```

## Performance Considerations

1. **Log Limit**: Default max_logs=1000 to prevent memory issues
2. **Update Frequency**: 500ms refresh rate balances responsiveness and performance
3. **Queue Size**: Unbounded queue, but old logs are pruned
4. **Thread Safety**: All operations are thread-safe

## Troubleshooting

### Logs Not Appearing
- Check that the log streamer is initialized
- Verify the update interval is set (every=0.5)
- Ensure logs are being added to the correct queue

### Process Output Not Captured
- Verify the process uses stdout/stderr properly
- Some processes may buffer output - use `python -u` for unbuffered
- Check process permissions

### Performance Issues
- Reduce max_logs if memory is a concern
- Increase update interval if CPU usage is high
- Consider filtering logs before display