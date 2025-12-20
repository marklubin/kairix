# CLAUDE.md - Kairix Project Guide

## Coding Standards

### Python Projects

**Package Management: `uv` (mandatory)**
- All Python projects use `uv` for dependency management
- Commands: `uv sync`, `uv run`, `uv add <pkg>`
- Build backend: `uv_build` or `hatchling` with `uv-dynamic-versioning`

**Type Annotations: Strict (mandatory)**
- All code must be fully typed
- Pyright in `strict` mode is the standard
- Ruff `ANN` rules enforce annotation completeness
- Avoid `# type: ignore` - fix the types or use proper stubs

**Linting: Ruff**
- Line length: 100-120 characters
- Auto-fix with: `uv run ruff check --fix`
- Format with: `uv run ruff format`
- Strict rule selection - see individual `pyproject.toml` for project-specific ignores

**Testing: pytest**
- Default: automated e2e functional tests for new code
- Unit tests for complex logic
- Integration tests marked with `@pytest.mark.integration`
- Async tests: `@pytest.mark.asyncio`
- Fixtures for state setup (prefer fixtures over manual setup in tests)

**Project Verification**
- Run `uv run pytest` before finalizing changes
- Some projects have `just all` or `make test` for full verification

### Code Style

**Imports**
- Unconditional imports at top of files
- Sort with `isort` via Ruff (`I` rules)
- Type-checking imports in `TYPE_CHECKING` block when needed

**Error Handling**
- Typed result patterns over exceptions where practical
- Pydantic models for data validation at boundaries
- Explicit error types for domain errors

**Async**
- Prefer async/await for IO-bound operations
- Use `asyncio` patterns; avoid threading unless necessary
- See "Topics to Revisit" for asyncio/threading edge cases

---

## Learning Mode

**Activation**: Say "learning mode" or "tutorial approach" to enable guided learning.

When active, this collaborative approach applies:

### Philosophy
- **Learn by doing** - Build real features rather than just reading
- **Guided exploration** - Balance between teaching and discovering
- **Incremental complexity** - Start simple, build up
- **Collaboration over automation** - You implement key decisions; I handle boilerplate

### How It Works
1. **Context provided** - Explain what we're building and why
2. **You make decisions** - Choose approaches for meaningful features (2-10 lines of key logic)
3. **I handle scaffolding** - Structure, boilerplate, and routine code
4. **Insights shared** - Patterns, architecture, and how things connect

### When You'll Contribute Code
- Multiple valid approaches exist (error handling, data structures)
- Business logic involves design decisions
- Key algorithms or interface definitions need writing
- The decision teaches an important concept

---

## Journal Entries

At session end (or when you say "journal this"), create an entry in **`./journal/session-XX.md`**:

```markdown
---

## Session [N] - [Date: YYYY-MM-DD]

### Goals
- [ ] Goal 1
- [ ] Goal 2

### What We Covered
- Topic 1: Brief description
- Topic 2: Brief description

### Key Concepts Learned
1. **Concept Name**: Explanation
2. **Concept Name**: Explanation

### What We Built
- Feature/file created
- Code written (file paths and key changes)

### Insights & Aha Moments
- Important realization or pattern discovered

### Challenges & Solutions
- **Challenge**: Description
- **Solution**: How we resolved it

### Next Steps
- [ ] Next task to tackle

### Questions/Blockers
- Unresolved questions for next time
```

**Session Index**: `./journal/` directory contains all entries (session-01.md through session-23.md)

---

## Topics to Revisit

Concepts that need deeper exploration:

1. **Threading + Asyncio interaction** (Session 12)
   - `asyncio.get_event_loop()` fails in background threads
   - `call_soon_threadsafe()` bridges threads to event loop
   - Pattern: capture loop reference in main thread, use from background

2. **Audio feedback loop prevention** (Session 12)
   - Mic picks up speaker output, causing echo
   - Solution: mute mic during TTS playback

3. **VAD tuning** (Session 12, 20)
   - Current: `stop_secs=1.5`, various `min_volume`/`confidence` params
   - Different environments need different tuning
   - Smart Turn Detection (`LocalSmartTurnAnalyzerV3`) may help

4. **Barge-in / interruption handling** (Session 14)
   - User interrupting AI mid-speech vs echo detection
   - Pipecat's `allow_interruptions=True` behavior unclear

---

## v2-runtime Operations

### kx CLI

The `kx` script in `v2-runtime/` is the unified CLI for managing Kairix services:

```bash
cd v2-runtime

# Service management
./kx up              # Start all services
./kx down            # Stop all services
./kx restart         # Restart all services
./kx status          # Show service status
./kx logs [service]  # View logs

# Development
./kx dev             # Start dependencies only (postgres, redis, letta)
./kx dev:down        # Stop dev dependencies

# Database
./kx migrate         # Run alembic migrations
./kx psql            # Connect to PostgreSQL shell
./kx db:reset        # Reset database (destroys data)

# Voice management
./kx voice list      # List configured TTS voices
./kx voice add       # Add a new voice (interactive)
./kx voice assign    # Assign voice to an agent

# KP3 (passage/knowledge management)
./kx kp3 passage search "query"
./kx kp3 passage ls
./kx kp3 sql "SELECT ..."

# Health checks
./kx wait postgres redis    # Wait for specific services
./kx wait all               # Wait for all services
```

### Deploying to Remote Hosts

Use `deploy.sh` to deploy changes to remote hosts (e.g., salinas):

```bash
cd v2-runtime
./deploy.sh salinas
# or
./kx deploy salinas
```

The deploy script:
1. SSHs to the target host
2. Pulls latest from `origin/main`
3. Stops existing services (`kx down`)
4. Rebuilds images (`kx build`)
5. Starts infrastructure (`kx dev`)
6. Waits for postgres to be healthy
7. Runs migrations (`kx migrate`)
8. Starts app services (`kx up`)

**Prerequisites**: SSH access configured for the target host, and the repo cloned at `~/kairix/v2-runtime` on the remote.

### Running Commands on Remote

For ad-hoc commands on salinas, SSH and use the REST API or kx CLI:

```bash
# REST API
ssh salinas 'curl -s http://localhost:8000/voices | jq'

# kx CLI
ssh salinas 'cd ~/kairix/v2-runtime && ./kx voice list'
```

---

## External Documentation

- **Letta SDK**: Use official docs at https://docs.letta.com/api (not Context7 - outdated)
- **Other libraries**: Use Context7 MCP server for current documentation
