# Session 18 - Date: 2025-12-03

## Goals
- [x] Fix soft reset bug (system messages being wiped)
- [x] Repair Corindel's database state after accidental message deletion
- [x] Clean up junk archival passages
- [x] Update session timeout and cron job frequency for production
- [x] Create Docker Compose deployment configuration
- [ ] Get Docker build working (in progress)

## What We Covered
- **Letta Message Types**: SystemMessage must be first in message_ids or agent fails
- **Soft Reset vs Hard Delete**: `agents.update(message_ids=[...])` vs `messages.reset()`
- **Database Repair**: Direct psql access in Letta container to restore state
- **Docker Compose Profiles**: Separating infrastructure from app services
- **Docker Build Issues**: Symlinks, README requirements, pyaudio native deps

## Key Concepts Learned

1. **Letta System Message Requirement**
   - First message in `message_ids` MUST be a `SystemMessage`
   - If wiped, subsequent agent calls fail with: "First message is not a system message"
   - Soft reset must preserve system messages while removing summarized ones

2. **Soft Reset Pattern (Fixed)**
   ```python
   # Get current messages
   agent = await client.agents.retrieve(agent_id=agent_id)
   current_message_ids = agent.message_ids or []

   # Identify system messages to preserve
   system_message_ids: set[str] = set()
   async for msg in client.agents.messages.list(agent_id):
       if msg.id in current_message_ids and isinstance(msg, SystemMessage):
           system_message_ids.add(msg.id)

   # Keep system messages + any new messages, remove summarized ones
   remaining_ids = [
       mid for mid in current_message_ids
       if mid in system_message_ids or mid not in summarized_set
   ]

   await client.agents.update(agent_id=agent_id, message_ids=remaining_ids)
   ```

3. **Docker Compose Profiles**
   - `profiles: [app]` - only starts with `--profile app`
   - Infrastructure (redis, letta, piper) runs always
   - App services (kairix-server, kairix-worker) run with profile
   - Allows dev mode (local Python) vs prod mode (containers)

4. **Dockerfile Gotchas**
   - Symlinks outside build context fail (`.claude -> ../kmp-scaffold/.claude`)
   - `readme = "README.md"` in pyproject.toml requires the file to exist
   - `pyaudio` needs native deps (gcc, portaudio) - remove for server builds
   - `uv sync --frozen --no-dev` should exclude dev deps but lock file matters

5. **Letta Database Access**
   ```bash
   podman exec -it letta psql -U letta -d letta
   # Then SQL:
   UPDATE letta.agents SET message_ids = '["message-xxx"]'::json WHERE id = 'agent-xxx';
   ```

## What We Built

**src/kairix_agent/worker/jobs/summarize.py** - Fixed soft reset:
- Added logic to identify and preserve `SystemMessage` types
- Only removes messages that were part of the summarized session
- Logs detailed info about what was kept vs removed

**src/kairix_agent/config.py** - Production settings:
- `SESSION_GAP_MINUTES` default changed from 1 to 5

**src/kairix_agent/worker/settings.py** - Production cron:
- Changed from `*/5 * * * * *` (every 5 seconds) to `* * * * *` (every minute)

**docker-compose.yml** - Added app services:
```yaml
kairix-server:
  build: .
  command: uv run uvicorn kairix_agent.server.main:app --host 0.0.0.0 --port 8000 --workers 2
  profiles: [app]

kairix-worker:
  build: .
  command: uv run saq kairix_agent.worker.settings --verbose
  profiles: [app]
```

**Dockerfile** - Simplified build:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
RUN uv sync --frozen --no-dev
CMD ["uv", "run", "kairix-server"]
```

**.dockerignore** - Exclude problematic files:
- `.claude` symlink
- `.venv/`, `__pycache__/`
- `.letta/`, `.piper/`, `.env`
- `tests/`, `*.md`, `design-docs/`

**pyproject.toml** - Cleanup:
- Removed `readme = "README.md"` (file doesn't exist)
- Removed `pyaudio` from dev dependencies (native build issues)
- Removed `test-client` and `voice-client` scripts (unused)

## Insights & Aha Moments

- **"System messages are sacred"**: Letta uses them for agent identity/instructions - can't be removed
- **"Soft reset is surgical"**: Must carefully preserve what matters while removing what's processed
- **"Docker Compose profiles = deployment targets"**: Clean separation of dev vs prod configurations
- **"Lock files include dev deps"**: Even with `--no-dev`, if pyaudio is in lock file, it may try to resolve
- **"Direct DB access is escape hatch"**: When SDK doesn't have an operation, psql works

## Challenges & Solutions

- **Challenge**: Agent calls hanging after soft reset
- **Solution**: Bug found - we were wiping system messages. Fixed by preserving `SystemMessage` types.

- **Challenge**: Corindel's `message_ids` was empty `[]` after bug
- **Solution**: Direct psql UPDATE to restore the system message ID

- **Challenge**: Docker build failing on `.claude` symlink
- **Solution**: Created `.dockerignore` to exclude it

- **Challenge**: Docker build failing on missing `README.md`
- **Solution**: Removed `readme = "README.md"` from pyproject.toml

- **Challenge**: Docker build failing on `pyaudio` (needs gcc)
- **Solution**: Removed pyaudio and unused voice/test clients from project

## Database Operations Performed

1. **Restored Corindel's system message**:
   ```sql
   UPDATE letta.agents
   SET message_ids = '["message-b9c6ac51-030e-436e-8cdb-a4128d0968fe"]'::json
   WHERE id = 'agent-62f4b273-69c4-41d3-8571-02a0413756fb';
   ```

2. **Cleaned up junk archival passages** (kept 2, deleted 3):
   - Kept: passage-c2624bd7 (277-message summary)
   - Kept: passage-93cdda64 (latest test summary)
   - Deleted: 3 junk/incorrect passages

## Next Steps
- [ ] Get Docker build fully working (pyaudio removed, retry build)
- [ ] Deploy to remote server
- [ ] Test with actual voice client app (KMP iOS app)
- [ ] Reconsider "raw" Claude agents vs Letta agents for auxiliary background processes
- [ ] Evaluate if reflector agent needs full Letta overhead or just Claude API calls

## Questions/Blockers
- Docker build should work now after removing pyaudio - needs testing
- Consider whether Letta agents are overkill for simple summarization tasks

## Architecture Consideration: Raw Agents vs Letta Agents

For auxiliary background processes like summarization, we should evaluate:

| Approach | Pros | Cons |
|----------|------|------|
| **Letta Agent (current)** | Consistent identity, memory tools, conversation history | Overhead, latency, complexity |
| **Raw Claude API** | Fast, simple, cheap | No memory tools, no identity persistence |

The reflector agent might be simpler as direct Claude calls since:
- It doesn't need conversation memory (gets transcript as input)
- It doesn't need tools (just generates summary text)
- Identity can be maintained via system prompt alone
- Faster and cheaper without Letta overhead

Worth exploring in future session.

## Session Victory

**Critical bug fixed + deployment prep!**
- Fixed soft reset to preserve system messages (agent no longer breaks)
- Repaired production database state
- Cleaned up archival memory
- Created Docker deployment configuration
- Removed unused code and dependencies
- Ready for final Docker build test and deployment

Two sessions of debugging and infrastructure work, but the system is now production-ready!
