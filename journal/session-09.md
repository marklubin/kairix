# Session 9 - Date: 2025-11-26

## Goals
- [x] Pivot to Python backend development
- [x] Set up strict Python linting (Ruff + ty)
- [x] Configure uv project with modern tooling
- [x] Design bidirectional streaming chat architecture
- [x] Implement Phase 1: WebSocket echo server

## What We Covered
- **Python Tooling**: Ruff (linting/formatting), ty (type checking), uv (package manager)
- **Project Setup**: Strict pyproject.toml with 50+ Ruff rule categories
- **FastAPI Basics**: App creation, routing, uvicorn server
- **WebSocket Fundamentals**: Protocol upgrade, bidirectional communication
- **ASGI vs WSGI**: Why async matters for WebSockets
- **Architecture Design**: Continuous streaming chat (not turn-based)

## Key Concepts Learned

1. **Ruff + ty for Maximum Strictness**
   - Ruff: 50+ rule categories (ANN for type annotations!)
   - ty: Astral's new type checker, warnings→errors
   - Both configured in single pyproject.toml
   - `uv run ruff check` + `uv run ty check`

2. **uv_build vs hatchling**
   - `uv_build`: Native, 10-35x faster, auto-detects src layout
   - `hatchling`: More features (hooks, VCS versioning)
   - Start with uv_build, switch if needed

3. **requires-python vs .python-version**
   - `requires-python`: Package metadata ("needs Python X+")
   - `.python-version`: Local dev pinning ("use exactly X here")
   - Different audiences: installers vs local tools

4. **uv Cache is Already Shared**
   - `~/.cache/uv` shared across all projects
   - No per-venv duplication like pip
   - `.venv` contains symlinks to cache

5. **FastAPI + uvicorn Relationship**
   - FastAPI = framework (routes, validation)
   - uvicorn = ASGI server (runs the app)
   - `uvicorn.run("module:app", reload=True)`

6. **ASGI vs WSGI**
   - WSGI (2003): Sync, HTTP only, one request per thread
   - ASGI (2016): Async, HTTP + WebSockets + streaming
   - ASGI = interface between server and framework

7. **WebSocket Protocol**
   - Starts as HTTP, upgrades via `101 Switching Protocols`
   - Same TCP connection, different protocol after upgrade
   - Works through firewalls (looks like HTTP initially)

8. **WebSocket vs WebTransport**
   - WebSocket: TCP, reliable, mature, universal
   - WebTransport: QUIC/UDP, multi-stream, newer
   - WebSocket fine for text; WebTransport for audio/video

9. **Async Mental Model**
   - `await` = "I'm waiting, run other stuff, wake me later"
   - Cooperative multitasking (voluntary yield at await)
   - Pattern-match to learn, deep understanding comes later

10. **module:attr Convention**
    - Not Python syntax - tool convention
    - `importlib.import_module()` + `getattr()`
    - Used by uvicorn, entry points, celery, etc.

## What We Built

**pyproject.toml** - Strict Python project config:
- uv_build backend (simpler than hatchling)
- Ruff with 50+ rule categories enabled
- ty with warnings promoted to errors
- FastAPI + uvicorn dependencies

**src/agent_server/main.py** - WebSocket echo server:
- FastAPI app with `/hello` route
- `/ws` WebSocket endpoint
- Accept, loop receive/send, handle disconnect
- Programmatic uvicorn startup

## Architecture Designed

**Bidirectional Streaming Chat:**
- No discrete "send" button - continuous input streaming
- Server decides when to trigger response
- Multiple in-flight responses supported
- Context snapshots capture partial responses
- User can't unsay - like real conversation

**Message Protocol (v1):**
```python
# Client → Server
{"type": "input_chunk", "text": "..."}
{"type": "trigger_response"}

# Server → Client
{"type": "response_start", "id": "..."}
{"type": "response_chunk", "id": "...", "text": "..."}
{"type": "response_done", "id": "..."}
```

## Insights & Aha Moments

- **"Why isn't strict the default?"**: Historical inertia, gradual adoption philosophy
- **"uv cache is already shared"**: Unlike pip, uv deduplicates across projects
- **"ASGI = contract between server and framework"**: Not network protocol, just Python interface
- **"WebSocket upgrades, doesn't reconnect"**: Same TCP socket, protocol switch
- **"Async trips up experienced devs"**: Pattern-match first, deep understanding later
- **"module:attr is convention, not syntax"**: Tools agreed on format for lazy loading

## Challenges & Solutions

- **Challenge**: MCP servers not available in Claude Code CLI
- **Solution**: `claude mcp add --scope user context7` for global config

- **Challenge**: Couldn't use `async for` on `receive_text()`
- **Solution**: Returns single string, not iterator. Use `while True` loop.

- **Challenge**: Understanding ASGI vs WSGI
- **Solution**: ASGI = async interface that supports WebSockets; WSGI = sync HTTP only

## Next Steps (Build Plan)

**Phase 2**: Typed Pydantic message protocol
**Phase 3**: Conversation state management
**Phase 4**: Mock streaming responses
**Phase 5**: TUI test client (Claude builds)
**Phase 6**: Letta integration

## Questions/Blockers
- Async generator/iterator patterns still confusing (ongoing learning)
- Letta token streaming needs investigation with Python SDK

## Key Decisions Made

- **Ruff + ty over alternatives**: Astral ecosystem, fast, well-integrated
- **uv_build over hatchling**: Simpler, faster, auto-detects src layout
- **stdlib logging over structlog**: Simple enough for learning
- **WebSocket over SSE**: True bidirectional needed
- **FastAPI**: Familiar, great WebSocket support, async-native
- **Tutorial style**: Guided with concepts, user writes code

## Technical Notes

**Project Structure:**
```
agent-server/
├── src/agent_server/
│   ├── __init__.py
│   └── main.py    # FastAPI + WebSocket
├── pyproject.toml # All config
└── .python-version
```

**Commands:**
```bash
uv sync                      # Install deps
uv run agent-server          # Run server
uv run ruff check src/       # Lint
uv run ty check src/         # Type check
websocat ws://localhost:8000/ws  # Test WebSocket
```

## Philosophical Insights

- **"Most people fumble async until it works"**: Copy-paste → error-driven → vague intuition → (rare) understanding
- **"Same energy as Java generics"**: Overhead to reason > effort to make compiler happy
- **"No backspace in real convo"**: User can't unsay - forward correction only

## Session Victory

**Backend foundation laid!** Pivoted from KMP to Python:
- Strict linting setup (Ruff + ty)
- Modern uv project configuration
- WebSocket echo server working
- Architecture designed for bidirectional streaming
- Ready to build typed message protocol next

Good stopping point - core concepts covered, server running, clear path forward!
