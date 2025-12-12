# Session 10 - Date: 2025-11-26

## Goals
- [x] Complete Pydantic message protocol (Phase 2)
- [x] Build test client CLI
- [x] Create abstract LLMProvider interface
- [x] Implement AnthropicProvider with real streaming
- [x] Wire WebSocket handler to stream real AI responses
- [x] Test end-to-end bidirectional streaming

## What We Covered
- **Pydantic Basics**: BaseModel, model_validate_json(), model_dump_json()
- **Literal Types**: Python's value-constrained types for discriminated unions
- **Abstract Base Classes**: ABC pattern for swappable providers
- **Async Generators**: The `yield` keyword's magical type transformation
- **Type Checker Frustrations**: ty, pyright, and the many papercuts of Python typing
- **Anthropic SDK**: AsyncAnthropic, messages.stream(), text_stream iteration
- **UUID for Request IDs**: Unique response tracking without global locks

## Key Concepts Learned

1. **Pydantic Serialization**
   - `model_validate_json(raw)` - Parse JSON string to model
   - `model_dump_json()` - Serialize model to JSON string
   - `model_dump()` - Serialize to dict (for send_json())
   - Don't double-serialize: `send_json(model.model_dump())` OR `send_text(model.model_dump_json())`

2. **Literal Types in Python**
   - `Literal["value"]` = type constrained to exact value
   - `[]` holds VALUES, not types (unlike generics)
   - Foundation for discriminated unions
   - Python typing inconsistency: `List[str]` vs `Literal["a"]` use `[]` differently

3. **Abstract Base Classes**
   ```python
   from abc import ABC, abstractmethod

   class LLMProvider(ABC):
       @abstractmethod
       async def stream_response(self, msg: str) -> AsyncIterator[str]:
           yield  # REQUIRED to make it an async generator!
   ```

4. **The `yield` Type Transformation (The Big Gotcha!)**
   - `async def foo() -> AsyncIterator[str]: ...` = coroutine returning iterator
   - `async def foo() -> AsyncIterator[str]: yield x` = async generator (IS an iterator)
   - Same signature, different types based on function body
   - Type checker can't express "must contain yield" in annotation
   - Abstract methods need `yield` in body to match override types

5. **Python Typing Frustrations**
   - `dict[str, str]` doesn't match `TypedDict` (no structural literal inference)
   - SDK docs show "wrong" types that work at runtime but fail type checkers
   - `Unknown | Type` = type checker gave up figuring it out
   - `ty` is alpha, pyright gives better error messages
   - Liskov Substitution errors can be misleading

6. **Anthropic Streaming API**
   ```python
   async with client.messages.stream(...) as stream:
       async for text in stream.text_stream:
           yield text
   ```
   - Must use `async with` (not `with`) for AsyncAnthropic
   - `text_stream` yields string chunks directly
   - Uses ANTHROPIC_API_KEY env var automatically

7. **Sync vs Async Python**
   - `Anthropic()` = sync client, use `with`, `for`
   - `AsyncAnthropic()` = async client, use `async with`, `async for`
   - Don't mix! If using async client, everything needs `async`

8. **Coroutine Local Variables**
   - Each coroutine has its own stack frame
   - Local variables are automatically "coroutine-local"
   - No races on locals - only module-level globals are shared
   - For unique IDs: `uuid.uuid4()` (no locks needed)

9. **dotenv for Environment Variables**
   - `dotenv.load_dotenv()` reads `.env` into `os.environ`
   - Or use `uv run --env-file .env` (no code changes)
   - Keep `.env` out of git!

10. **Module Exports in Python**
    - `__init__.py` controls package-level imports
    - Re-export: `from .module import Class`
    - `__all__` only affects `from package import *`
    - Watch for circular imports in `__init__.py`

## What We Built

**model.py** - Pydantic message types:
- `InputChunk` - client input with text, timestamp
- `ResponseStart` - marks response beginning with UUID
- `ResponseChunk` - streaming text piece with chunk_id, response_id
- `ResponseDone` - marks response complete
- All with `type: Literal[...]` for future discriminated unions

**test_client.py** - CLI WebSocket test client:
- Connects to ws://localhost:8000/ws
- Reads stdin, sends as InputChunk JSON
- Prints received messages with ← → arrows
- Uses asyncio + run_in_executor for non-blocking stdin

**provider/base.py** - Abstract LLM interface:
- `LLMProvider(ABC)` with `stream_response()` abstract method
- `yield` in body to make it an async generator type

**provider/anthropic.py** - Real Anthropic integration:
- `AnthropicProvider(LLMProvider)`
- Uses AsyncAnthropic with messages.stream()
- Yields text chunks from stream.text_stream

**provider/__init__.py** - Clean exports:
- Re-exports LLMProvider and AnthropicProvider
- Import moved after class definition to avoid circular import

**main.py** - Updated WebSocket handler:
- Instantiates AnthropicProvider
- Generates UUID for each response
- Sends ResponseStart, streams ResponseChunks, sends ResponseDone
- Real streaming from Anthropic API!

## Insights & Aha Moments

- **"The `yield` changes everything"**: Presence of `yield` in function body transforms type from coroutine→generator. Mind-bending.
- **"Python typing is bolted-on"**: TypeScript designed with types; Python retrofitted them. Shows in the inconsistencies.
- **"SDK docs are for runtime, not type checkers"**: Official examples don't type-check because most Python devs don't use strict typing
- **"`Unknown` means give up"**: Type checker couldn't figure it out, not that the type IS unknown
- **"Sync/async must match throughout"**: `with` vs `async with` - mixing causes cryptic errors
- **"Interleaving works!"**: Can send new requests while responses stream, UUIDs track which is which

## Challenges & Solutions

- **Challenge**: `send_json(model.model_dump_json())` double-serializing
- **Solution**: Use `send_json(model.model_dump())` OR `send_text(model.model_dump_json())`

- **Challenge**: Import path `src.agent_server.model` wrong
- **Solution**: Mark `src/` as Sources Root in IntelliJ, use `agent_server.model`

- **Challenge**: Type error on Anthropic `messages` parameter
- **Solution**: Python can't infer TypedDict from dict literal. Use `# type: ignore` or explicit type annotation.

- **Challenge**: `Unknown | AsyncMessageStreamManager` error
- **Solution**: Using sync `with` instead of `async with`. Add `async`.

- **Challenge**: Invalid override of `stream_response` - LSP violation
- **Solution**: Abstract method needs `yield` in body to be async generator type, not coroutine returning iterator.

- **Challenge**: Circular import in `__init__.py`
- **Solution**: Move import after class definition, or use separate `base.py` file.

- **Challenge**: Forgot to send ResponseChunk in loop
- **Solution**: Added `await websocket.send_text(response_chunk.model_dump_json())` inside async for.

- **Challenge**: Passing raw JSON `text` instead of `input_chunk.text` to provider
- **Solution**: Use the parsed Pydantic model's `.text` attribute.

## Next Steps

**START NEXT SESSION WITH DIRECTION DISCUSSION:**
Possible directions to explore:
- [ ] Add conversation history/context to Anthropic calls
- [ ] Implement server-triggered responses (pause detection)
- [ ] Build proper TUI client with Textual
- [ ] Add Letta integration as alternative provider
- [ ] Local storage for conversation persistence
- [ ] Connect KMP mobile app to this backend
- [ ] Add text-to-speech/speech-to-text pipeline
- [ ] WebTransport for audio streaming

## Questions/Blockers
- Direction unclear - need to discuss priorities next session
- No conversation context yet (each message is standalone)
- Mobile app (KMP) not connected to new backend

## Key Decisions Made

- **Abstract provider pattern**: Easy to swap Anthropic → Letta later
- **UUID for response IDs**: No global locks, guaranteed unique
- **Separate base.py**: Avoids circular import issues
- **`yield` in abstract method**: Weird but necessary for type system
- **Skip trigger_response for now**: Server always responds immediately

## Technical Notes

**Project Structure:**
```
agent-server/
├── src/agent_server/
│   ├── __init__.py
│   ├── main.py           # FastAPI + WebSocket
│   ├── model.py          # Pydantic message types
│   ├── test_client.py    # CLI test tool
│   └── provider/
│       ├── __init__.py   # Exports LLMProvider, AnthropicProvider
│       ├── base.py       # Abstract LLMProvider
│       └── anthropic.py  # Real Anthropic integration
├── pyproject.toml
└── .env                  # ANTHROPIC_API_KEY (gitignored)
```

**Commands:**
```bash
uv run agent-server       # Start server
uv run test-client        # Interactive test client
uv run ty check           # Type check
uv run ruff check         # Lint
```

**Message Flow:**
```
Client                          Server
  │                               │
  │──── InputChunk ──────────────>│
  │                               │ (call Anthropic)
  │<──── ResponseStart ───────────│
  │<──── ResponseChunk ───────────│ (streaming)
  │<──── ResponseChunk ───────────│
  │<──── ResponseChunk ───────────│
  │<──── ResponseDone ────────────│
  │                               │
  │──── InputChunk ──────────────>│ (can interleave!)
```

## Philosophical Insights

- **"Python typing is a culture clash"**: 30 years of "dicts are fine" vs modern type safety. The seams show.
- **"Abstract async generators are cursed"**: `yield` in an abstract method body is weird, but type systems need it
- **"Type errors lie sometimes"**: "LSP violation" was really "wrong function type", error message was misleading
- **"Pyright > ty for debugging"**: Alpha tools give worse errors; use mature tools when stuck

## Session Victory

**Real streaming AI working!** Built complete pipeline:
- Pydantic-typed message protocol
- Abstract provider pattern for swappability
- Real Anthropic streaming integration
- WebSocket bidirectional communication
- Test client showing interleaved requests/responses

From echo server to real AI streaming in one session! The architecture is solid and extensible. 🚀
