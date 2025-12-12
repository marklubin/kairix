# Session 13 - Date: 2025-11-30

## Goals
- [x] Debug VAD/turn detection fragmentation issue
- [x] Understand Pipecat's context aggregator pattern
- [x] Build custom UserTurnAggregator state machine
- [x] Add pytest test suite for aggregator
- [x] Wire up aggregator to pipeline and test end-to-end

## What We Covered
- **Whisker Debugger**: Installed pipecat-ai-whisker for pipeline visualization
- **Frame Processor Architecture**: How Pipecat LLM services handle transcription
- **Context Aggregator Pattern**: Buffers transcripts, waits for VAD, handles race conditions
- **Pipecat Concurrency Model**: Single-threaded event loop, one pipeline per connection
- **Explicit State Machine Design**: Replaced boolean flags with enum states

## Key Concepts Learned

1. **Official LLM Services Don't Handle TranscriptionFrame Directly**
   - OpenAI/Anthropic processors listen for `LLMContextFrame`, not `TranscriptionFrame`
   - Context aggregators sit between STT and LLM to buffer and finalize turns
   - Our `LettaLLMService` was processing each transcript chunk immediately

2. **Turn vs Transcript**
   - **Turn**: Full utterance from start to stop speaking
   - **Transcript**: Chunks within a turn (Deepgram sends finals at sentence boundaries)
   - Multiple `TranscriptionFrame` can occur per turn
   - `InterimTranscriptionFrame` = unstable partial, `TranscriptionFrame` = committed chunk

3. **Frame Ordering Guarantees**
   - Within a single processor: ordered
   - Across different processors (VAD vs STT): NO guarantee
   - VAD can fire `UserStoppedSpeakingFrame` before final `TranscriptionFrame` arrives
   - This is why timeout-based aggregation exists

4. **State Machine vs Boolean Flags**
   ```python
   # Boolean approach (Pipecat's built-in) - hard to reason about
   _user_speaking: bool
   _seen_interim_results: bool

   # Explicit state approach (ours) - clear transitions
   class UserTurnState(Enum):
       IDLE
       SPEAKING_AWAITING_TRANSCRIPT
       SPEAKING_RECEIVED_TRANSCRIPT
       DONE_AWAITING_TRANSCRIPT
   ```

5. **VAD in Transport, Not Pipeline**
   - VAD analyzer is config on transport, not a separate processor
   - Needs to operate on raw audio samples before framing
   - Tight integration for echo cancellation, barge-in handling

## What We Built

**UserTurnAggregator** (`user_turn_aggregator.py`):
- Explicit 4-state state machine
- Consumes interim/final transcripts, emits `UserTurnMessageFrame`
- Handles race condition via inline timeout check (no background task)
- State handlers in separate module for clarity

**State Handler Pattern** (`state_handlers.py`):
```python
class StateHandler(ABC):
    async def handle(self, frame, direction) -> None:
        # Routes to on_user_started, on_transcription, etc.

class IdleHandler(StateHandler):
    async def on_user_started(self, frame, direction) -> None:
        self.aggregator.transition_to(UserTurnState.SPEAKING_AWAITING_TRANSCRIPT)
```

**Test Suite** (`tests/pipecat/test_user_turn_aggregator.py`):
- 20 tests covering all state transitions
- Per-state unit tests
- Integration tests for full conversation flows
- Race condition test (stop before final transcript)

## Pipeline Architecture

```
Before:
transport.input() → stt → LettaLLMService → tts → transport.output()
                          ↑ processed each TranscriptionFrame immediately

After:
transport.input() → stt → UserTurnAggregator → LettaLLMService → tts → transport.output()
                          ↑ buffers transcripts    ↑ only sees UserTurnMessageFrame
                          ↑ emits complete turn
```

## Insights & Aha Moments

- **"The timeout is defensive"**: Most of the time VAD fires after final transcript, but network latency can reverse order
- **"Explicit states > boolean combinations"**: 4 states × 4 frame types = 16 handlers, but each is trivial
- **"Consume vs pass through"**: Aggregator consumes transcription frames (no push), only emits aggregated result
- **"Frame flow through Whisker"**: PROCESS = received, PUSH = forwarded - consumed frames only show PROCESS

## Files Created/Modified

**New Files:**
- `src/agent_server/pipecat/user_turn_aggregator.py` - Aggregator + state enum + frame type
- `src/agent_server/pipecat/state_handlers.py` - StateHandler base + 4 concrete handlers
- `tests/pipecat/test_user_turn_aggregator.py` - 20 pytest tests

**Modified:**
- `src/agent_server/pipecat/__init__.py` - Export new classes
- `src/agent_server/pipecat/letta_llm.py` - Now only handles `UserTurnMessageFrame`
- `src/agent_server/main.py` - Added `UserTurnAggregator` to pipeline
- `pyproject.toml` - Added pytest, pytest-asyncio; fixed piper extra

## Whisker Debug Output (Success!)

```
#UserStartedSpeakingFrame#0   PROCESS + PUSH ✓
#InterimTranscriptionFrame#0  PROCESS only (consumed) ✓
#TranscriptionFrame#0         PROCESS only (consumed, aggregated) ✓
#UserStoppedSpeakingFrame#0   PROCESS, then:
  #UserTurnMessageFrame#0     PUSHED ✓  ← Complete turn!
  #UserStoppedSpeakingFrame#0 PUSHED ✓
```

## Future Enhancements (noted in code)

- Flag words with low confidence scores from STT for LLM context
- Include tone/sentiment markers from audio analysis

## Next Steps
- Wire up KMP mobile app to this backend
- Test voice conversation on Android
- Address audio feedback loop (mute mic during playback)

## Session Victory

Built a robust, testable state machine for turn aggregation that:
1. Correctly buffers multiple transcript chunks per turn
2. Handles the VAD/STT race condition gracefully
3. Has 20 passing tests covering all transitions
4. Works end-to-end (verified with Whisker + live test)

## Design Discussion: Pipecat Critique & Future Architecture

**Pipecat Framework Observations:**

Valid critiques:
- **Implicit dependencies between processors** - Can't understand a processor in isolation; pipeline is a list but relationships are a graph
- **Frame inheritance footgun** - `InterimTranscriptionFrame extends TranscriptionFrame` breaks `isinstance` patterns
- **VAD in transport, not composable** - Pragmatic but breaks the "everything is a processor" mental model
- **Boolean state for complex logic** - Their aggregator uses flag soup; explicit state machines are more maintainable

What's reasonable:
- Frame-based architecture itself (actor model, decoupled producers/consumers)
- Async-first, single-threaded (correct for I/O-bound streaming)
- Transport as boundary (separates wire format from processing)

**The Business Model Reality:**
- Happy path (their integrations) is smooth
- Custom path (like Letta) is rough - fighting implicit contracts
- "Framework" is really a sales funnel toward Daily.co and hosted offerings
- Good scaffold to learn the problem space, but may want simpler custom version later

**Future: Minimal Custom Pipeline**

Since we're orchestrating fixed components (Deepgram → Letta → Piper), not building generic abstraction:
- `VoiceSession` class owns the websocket
- `UserTurnAggregator` (already built)
- Direct SDK calls, no frame abstraction needed
- Explicit control flow instead of implicit frame routing

**Architecture: Decouple Voice from Background Processes**

Voice pipeline has hard real-time constraints (<500ms response). Background agent processes (summarization, reflection, proactive updates) should be separate:

```
┌─────────────────┐     ┌─────────────┐
│  Voice Pipeline │────▶│             │
│  (real-time)    │     │    Letta    │
└─────────────────┘     │   Server    │
                        │             │
┌─────────────────┐     │  (manages   │
│ Background Jobs │────▶│   state)    │
│ (async workers) │     │             │
└─────────────────┘     └─────────────┘
```

Letta is the coordination point. Voice pipeline stays dumb and fast.

**Docker Compose Strategy for Dev/Prod:**

```yaml
# docker-compose.yml
services:
  letta:        # their image
  piper-tts:    # their image
  agent-server: # our Dockerfile
  background-worker: # our Dockerfile, same codebase, different entrypoint
```

Dev flexibility via environment-based config:
```python
LETTA_URL = os.getenv("LETTA_URL", "http://localhost:9000")
PIPER_URL = os.getenv("PIPER_URL", "http://localhost:5001")
```

Local dev: run Python directly, infrastructure in Docker
CI/Prod: everything in Docker with container name URLs

## Future Session Ideas
- Audio feedback loop prevention / barge-in handling
- Add Android speech recognition (requires Foreground Service architecture)
- Local storage with SQLDelight
- **Contribute to Pipecat**: Once battle-tested, consider contributing `LettaLLMService` and `UserTurnAggregator` as community integrations (they accept PRs and have a community integration guide)
- Custom LLM context orchestration
- Build proper Textual TUI client
