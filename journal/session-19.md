---

## Session 19 - Date: 2025-12-05

### Goals
- [x] Create a minimal CLI voice client for testing the Pipecat WebSocket server

### What We Covered
- Building a Python CLI client with audio I/O for the voice pipeline
- Protobuf message encoding/decoding for Pipecat frames
- Asyncio patterns for concurrent audio capture, playback, and WebSocket communication

### What We Built
- `voice-client/` - Minimal Python package (~177 LOC)
  - `pyproject.toml` - uv-managed dependencies (websockets, sounddevice, numpy, protobuf)
  - `frames.proto` - Copied from agent-server for protobuf generation
  - `client.py` - Single-file client with:
    - Mic capture at 16kHz → sends AudioRawFrame to server
    - Receives TextFrame (prints transcriptions) and AudioRawFrame (plays TTS)
    - Auto-generates `frames_pb2.py` on first run
    - Clean Ctrl+C shutdown

### Key Concepts Learned
1. **Thread-to-asyncio bridging**: `sounddevice` callbacks run in a separate thread; use `loop.call_soon_threadsafe()` to queue audio to the async event loop
2. **Sample rate mismatch**: STT wants 16kHz input, TTS outputs 22kHz—client handles both natively

### Insights & Aha Moments
- Revisited the threading + asyncio interaction pattern from Session 12
- Bash signal handling: `&` + `wait` breaks Ctrl+C because the pipeline is backgrounded

### Next Steps
- [ ] Test with actual voice conversation
- [ ] Consider adding echo cancellation or mic muting during playback
