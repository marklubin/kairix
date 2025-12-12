# Session 11 - Date: 2025-11-28

## Goals
- [x] Set up local Letta server with Podman
- [x] Docker/Docker Compose refresher
- [x] Replace ty with pyright for type checking
- [x] Create LettaProvider for Python backend
- [x] Test Letta streaming end-to-end
- [x] Understand async streaming patterns

## What We Covered
- **Docker/Podman**: Images, containers, compose files, Podman as Docker alternative
- **Pyright Setup**: Replacing ty with pyright, configuring strict mode
- **Letta Python SDK**: AsyncLetta, streaming API, message types
- **Async Patterns**: Two-layer awaits (connection + iteration), AsyncStream
- **Python Typing Pain**: Union types, SDK type mismatches, bolted-on typing
- **rich Library**: Pretty-printing for debugging Pydantic models

## Key Concepts Learned

1. **Podman vs Docker**
   - Podman: Daemonless, rootless, CLI-compatible with Docker
   - On macOS: Requires VM (like Docker Desktop)
   - `alias docker='podman'` for compatibility
   - DOCKER_HOST needed for tools expecting Docker socket

2. **Docker Compose Basics**
   - `ports: "host:container"` - left is your machine, right is container
   - `volumes:` for persistent data
   - `env_file:` for secrets (keep .env out of git)
   - `container_name:` for predictable container IDs

3. **Pyright vs ty**
   - ty: Astral's new type checker (alpha, sparse errors)
   - pyright: Microsoft's mature type checker (better errors)
   - Both configured in pyproject.toml `[tool.pyright]`
   - Can have global ~/pyrightconfig.json for IDE

4. **`yield ""` vs `yield` in Abstract Methods**
   - `yield` alone produces `None`, type is `AsyncGenerator[None, ...]`
   - `yield ""` produces empty string, type is `AsyncGenerator[str, ...]`
   - Must match the declared `AsyncIterator[str]` return type

5. **Two-Layer Async Streaming**
   ```python
   # Layer 1: await to get the stream object
   stream = await client.agents.messages.stream(...)

   # Layer 2: async for awaits each chunk
   async for chunk in stream:
       ...
   ```
   - First await: "Connect and start request"
   - Each iteration: "Wait for next chunk from network"

6. **Python Won't Enforce `await`**
   - Forgetting `await` gives you a coroutine object, not the result
   - Only a RuntimeWarning, not an error
   - Type checkers help but aren't foolproof
   - Common async bug!

7. **Letta Streaming Message Types**
   - `ReasoningMessage` - AI's internal thinking (`.reasoning` field)
   - `AssistantMessage` - Actual response (`.content` field)
   - `LettaStopReason` - End of turn signal
   - `LettaUsageStatistics` - Token counts
   - Filter to extract just the text you want

8. **Union Types in SDKs**
   ```python
   content: Union[List[LettaAssistantMessageContentUnion], str]
   ```
   - Usually just a `str` for text responses
   - List form for multi-modal (images, etc.)
   - Use `isinstance()` or just `str(content)` for simple cases

9. **`__new__` vs `__init__`**
   - `__new__`: Creates the object (returns it)
   - `__init__`: Initializes the object (returns None)
   - Split exists for immutable types (int, str, tuple)
   - 99% of classes only need `__init__`

10. **IntelliJ + uv**
    - IntelliJ doesn't auto-detect `uv add` changes
    - Must manually refresh interpreter (click refresh icon)
    - Or: Settings → Project → Python Interpreter → refresh packages
    - No native uv support yet (doesn't watch uv.lock)

## What We Built

**docker-compose.yml** - Local Letta server:
```yaml
services:
  letta:
    container_name: letta
    image: letta/letta:latest
    ports:
      - "9000:8283"
    volumes:
      - .letta/.persist/pgdata:/var/lib/postgresql/data
    env_file:
      - .env
```

**pyproject.toml** - Updated for pyright:
- Replaced ty with pyright in dev deps
- Added `[tool.pyright]` section with strict mode
- Disabled noisy rules (reportUnknownMemberType, etc.)

**provider/letta.py** - Letta streaming provider:
- `LettaProvider(LLMProvider)` with agent_id parameter
- Uses `AsyncLetta` client
- Calls `client.agents.messages.stream()` with async iteration
- Filters for `AssistantMessage` and extracts `.content`

**~/.zshrc** - Podman Docker compatibility:
```bash
alias docker='podman'
export DOCKER_HOST="unix://$(podman machine inspect | jq -r '.[0].ConnectionInfo.PodmanSocket.Path')"
```

## Insights & Aha Moments

- **"Python typing is bolted-on"**: TypeScript designed with types; Python retrofitted. The seams show everywhere.
- **"Two awaits for streaming"**: First await gets the pipe, iteration awaits each chunk. Different from single-value async.
- **"SDK types lie"**: Official docs show code that works at runtime but fails type checkers. Most Python devs don't use strict typing.
- **"Podman is Docker without the daemon"**: Same CLI, different architecture. Philosophy > convenience for some.
- **"Union types = SDK complexity"**: Every LLM provider has slightly different schemas. Patterns transfer, details don't.

## Challenges & Solutions

- **Challenge**: Podman DOCKER_HOST not working
- **Solution**: Used `podman machine inspect | jq` to get socket path dynamically

- **Challenge**: ty giving sparse/unhelpful errors
- **Solution**: Switched to pyright for better error messages and maturity

- **Challenge**: `yield` in abstract method causing type mismatch
- **Solution**: Changed `yield` to `yield ""` to produce `str` not `None`

- **Challenge**: `json.dumps(response)` failing on Pydantic model
- **Solution**: Used `rich.pretty.pretty_repr()` for debugging, then extracted specific fields

- **Challenge**: IntelliJ not finding letta imports after `uv add`
- **Solution**: Manually refresh interpreter in Settings → Python Interpreter

- **Challenge**: Understanding `Union[List[...], str]` content type
- **Solution**: 99% of time it's just `str`; use isinstance or cast for safety

## Next Steps

**NEXT SESSION: Pipecat Integration**
- [ ] Research Pipecat architecture and concepts
- [ ] Write custom LLM provider to bridge Letta into Pipecat
- [ ] Understand Pipecat's frame-based pipeline model
- [ ] Set up audio input/output pipeline
- [ ] Connect speech-to-text and text-to-speech

**FUN IDEA: Dual TTS for Reasoning + Response**
- Fork stream after Letta: ReasoningMessage → TTS1, AssistantMessage → TTS2
- Different voices: calm main voice, fast/whispery/muttering thinking voice
- Could pan audio (reasoning left, response right) or lower volume for "background thoughts"
- Would be hilarious for demos - hear the AI's internal monologue in real-time!

## Questions/Blockers
- Need to understand Pipecat's provider interface
- Will require bridging our LettaProvider to Pipecat's expected interface
- May need to handle audio streaming (WebTransport consideration)

## Key Decisions Made

- **Podman over Docker**: Philosophical preference for daemonless architecture
- **Pyright over ty**: Maturity and error quality more important than bleeding edge
- **Filter to AssistantMessage only**: Skip reasoning/usage in final output
- **Pass agent_id to provider**: More flexible than env var for multi-agent scenarios
- **rich for debugging**: Better than print() for complex objects

## Technical Notes

**Project Structure (Updated):**
```
agent-server/
├── src/agent_server/
│   ├── __init__.py
│   ├── main.py           # FastAPI + WebSocket
│   ├── model.py          # Pydantic message types
│   ├── test_client.py    # CLI test tool
│   └── provider/
│       ├── __init__.py   # Exports all providers
│       ├── base.py       # Abstract LLMProvider
│       ├── anthropic.py  # Anthropic integration
│       └── letta.py      # Letta integration (NEW)
├── docker-compose.yml    # Local Letta server
├── pyproject.toml
└── .env                  # API keys + LETTA_AGENT_ID
```

**Commands:**
```bash
podman compose up -d      # Start Letta container
podman compose logs -f    # Watch logs
uv run agent-server       # Start our server
uv run test-client        # Test streaming
uv run pyright            # Type check
```

**Provider Swap:**
```python
# In main.py, just change which provider is used:
letta_provider = LettaProvider(agent_id=agent_id)
# vs
anthropic_provider = AnthropicProvider()
```

## Philosophical Insights

- **"Get the concepts, I'll generate the boilerplate"**: Right division of labor for learning. Understand patterns, delegate SDK wrangling.
- **"Python typing is a culture clash"**: 30 years of dynamic typing vs modern type safety. Neither side fully wins.
- **"Every SDK is slightly different"**: LLM APIs share concepts but differ in details. Learn the patterns, not the specifics.
- **"Frustration with types is normal"**: Even experienced devs fight Union types and SDK mismatches.

## Session Victory

**Letta streaming working locally!** Built complete integration:
- Local Letta server running in Podman
- LettaProvider implementing our abstract interface
- Token-level streaming through WebSocket
- Clean message extraction (AssistantMessage content only)
- Swappable with AnthropicProvider

Ready to integrate with Pipecat for the voice pipeline next session! 🎤
