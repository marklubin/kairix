## Session 30 - [Date: 2025-12-17 to 2025-12-18]

### Goals
- [x] Add memory block visibility to mobile app
- [x] Implement context_state event emission
- [x] Fix circular import in events module
- [x] Add app logo/branding
- [x] Deduplicate context streaming
- [x] Switch TTS from Deepgram to Cartesia
- [x] Fix Docker build cache invalidation for dependencies

### What We Covered
- Real-time memory block streaming to mobile clients
- Context state event architecture
- Circular import resolution patterns
- Cartesia TTS integration
- Docker layer caching with uv dependencies
- dotenv loading order issues

### Key Concepts Learned

1. **Context State Events**: New event type `context_state` streams the agent's current memory blocks (persona, human, background_insights) to connected clients. Emitted on:
   - WebSocket connection (initial state)
   - After session summarization updates blocks
   - After insights job updates blocks

2. **Circular Import Resolution**: `events/__init__.py` was importing from `events/context.py` which imported from `events/payloads.py` which imported back. Fixed by restructuring imports and using lazy imports where needed.

3. **Context Deduplication**: Multiple jobs could emit context_state simultaneously. Added tracking to prevent duplicate emissions within short time windows.

4. **Cartesia TTS**: Switched from Deepgram TTS to Cartesia for better voice quality. Requires `CARTESIA_API_KEY` and `CARTESIA_VOICE_ID` env vars.

5. **Docker Cache Invalidation with uv**: Using `--mount=type=bind` for `pyproject.toml` and `uv.lock` doesn't invalidate cache when files change. Must `COPY` these files before `RUN uv sync` so Docker detects changes.

6. **dotenv Loading Order**: `os.getenv()` at module definition time (in Enum classes) runs BEFORE `dotenv.load_dotenv()` in main.py imports. Must call `dotenv.load_dotenv()` in config.py itself.

### What We Built

**Memory Block Visibility (a1eb9c0):**
- `v2-runtime/src/kairix_agent/events/context.py` - `emit_context_state()` function
  - Fetches current blocks from Letta API
  - Formats into `ContextStatePayload`
  - Optionally persists to DB or just broadcasts
- `v2-runtime/src/kairix_agent/events/payloads.py` - `ContextStatePayload`, `MemoryBlock` models
- `v2-runtime/src/kairix_agent/server/main.py` - Emit on WebSocket connect
- `v2-runtime/src/kairix_agent/worker/jobs/summarize.py` - Emit after summary updates
- `v2-runtime/src/kairix_agent/worker/jobs/insights.py` - Emit after insights updates

**KMP App Updates:**
- `kairix-app/.../EventModels.kt` - Added `ContextStateEvent`, `MemoryBlock` data classes
- `kairix-app/.../App.kt` - Display memory blocks in UI
- Added app logo (`kairix.imageset`)

**Context Deduplication (695e982):**
- Track last emission time per agent
- Skip emission if within dedup window

**Cartesia TTS (22a1010):**
- Added `pipecat-ai[cartesia]` dependency
- `CartesiaTTSService` replaces `DeepgramTTSService`
- New env vars: `CARTESIA_API_KEY`, `CARTESIA_VOICE_ID`

**Docker Build Fix (d969172):**
```dockerfile
# Before (cache not invalidated on dependency changes):
RUN --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked

# After (cache invalidated when files change):
COPY uv.lock pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked
```

**Config Loading Fix (this session):**
```python
# config.py - load dotenv BEFORE enum definition
import dotenv
dotenv.load_dotenv()

class Config(Enum):
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    # ... now correctly reads from .env
```

### Architecture Update

```
WebSocket Connect          Background Jobs
       │                        │
       ▼                        ▼
  emit_context_state()    emit_context_state()
       │                        │
       ▼                        ▼
  ┌─────────────────────────────────────┐
  │         Deduplication Layer          │
  │   (skip if emitted < N seconds ago)  │
  └─────────────────────────────────────┘
                    │
                    ▼
           ┌───────────────┐
           │ Letta API     │
           │ GET /blocks   │
           └───────────────┘
                    │
                    ▼
           ┌───────────────┐
           │ Format Event  │
           │ context_state │
           └───────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
   Persist to DB         Broadcast to
   (optional)            WebSocket clients
```

### Files Modified

| File | Change |
|------|--------|
| `events/__init__.py` | Export emit_context_state |
| `events/context.py` | NEW - Context state emission |
| `events/payloads.py` | ContextStatePayload, MemoryBlock |
| `server/main.py` | Emit on connect, Cartesia TTS |
| `worker/jobs/summarize.py` | Emit after update |
| `worker/jobs/insights.py` | Emit after update |
| `config.py` | dotenv.load_dotenv() at top |
| `Dockerfile` | COPY instead of bind mount |
| `pyproject.toml` | pipecat-ai[cartesia] |
| `.env` | CARTESIA_*, salinas endpoints |

### Insights & Aha Moments

- **Bind mounts don't invalidate cache**: Docker's cache key for `RUN` instructions only considers the instruction text, not bind-mounted content. Use `COPY` for files that should trigger rebuilds.

- **Module-level code runs at import time**: Python evaluates class bodies (including Enum values) when the module is imported. Any setup (like dotenv) must happen before the import chain reaches the config.

- **Event deduplication is important**: Multiple code paths can trigger the same event type. Without dedup, clients receive redundant updates.

### Next Steps
- [ ] Add memory block editing in mobile app
- [ ] Consider caching Letta block fetches
- [ ] Add connection status indicator for events

### Questions/Blockers
- Cartesia voice selection - current voice ID hardcoded, consider making configurable
