# CLAUDE.md - KP3 Project Guide

## Project Overview

KP3 (Knowledge Processing Pipeline) is a text processing system with semantic search, world model extraction, and provenance tracking. Built with PostgreSQL + pgvector.

## Development Commands

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Lint and format
uv run ruff check --fix
uv run ruff format

# Type check
uv run pyright

# Run migrations
uv run alembic upgrade head

# Start service
uv run kp3-service

# CLI help
uv run kp3 --help
```

## Docker Commands

```bash
# Start full stack
docker compose up -d

# Run migrations in container
docker compose exec kp3-service uv run alembic upgrade head

# Run CLI commands
docker compose exec kp3-service uv run kp3 <command>
```

## Code Style

- Python 3.12+, fully typed (pyright strict mode)
- Ruff for linting and formatting (line length: 100)
- Async/await for all database operations
- Pydantic for API schemas and validation

## Architecture

```
src/kp3/
├── cli.py              # Click CLI commands
├── config.py           # Pydantic settings
├── db/                 # SQLAlchemy models, engine
├── processors/         # Embedding, LLM, world model
├── services/           # Business logic (passages, refs, search)
├── query_service/      # FastAPI REST API + MCP
├── schemas/            # API request/response models
└── llm/                # OpenAI-compatible client
```

## Key Concepts

- **Passages**: Text content with embeddings, metadata, provenance
- **Refs**: Mutable pointers to passages (like git refs)
- **Branches**: Groups of refs (human/persona/world) as a unit
- **Processors**: Transform passages (embedding, world model extraction)
- **Shadow Tables**: Denormalized entity storage for fast queries

---

## Journal Entries (Required)

**At the end of each session**, create or update a journal entry in `./journal/session-XX.md`.

### Finding the Next Session Number

```bash
ls journal/ | tail -1  # See latest session number
```

### Journal Entry Template

```markdown
## Session [N] - [YYYY-MM-DD]

### Goals
- [ ] Goal 1
- [ ] Goal 2

### What We Did
- Summary of changes made
- Files created/modified

### Key Changes
- **Feature/Fix**: Brief description
- **Feature/Fix**: Brief description

### Technical Notes
- Important implementation details
- Gotchas or non-obvious decisions

### Tests
- Tests added or modified
- Current test status

### Next Steps
- [ ] Follow-up task 1
- [ ] Follow-up task 2
```

### Example Entry

```markdown
## Session 4 - 2025-01-30

### Goals
- [x] Extract kp3 as standalone repository
- [x] Remove letta dependencies

### What We Did
- Removed letta integration (hooks, CLI options, config)
- Inlined kairix-common types into kp3
- Updated Dockerfile for standalone builds
- Created comprehensive README

### Key Changes
- **Removed**: `src/kp3/hooks/letta_sync.py`
- **Added**: `src/kp3/schemas/api.py` (API types)
- **Added**: `src/kp3/llm/` (LLM client utilities)
- **Updated**: `docker-compose.yml` for standalone deployment

### Technical Notes
- Hook system still exists but letta hook type removed
- Agent ID still used for multi-agent scoping (not letta-specific)

### Tests
- Updated test_refs.py to use generic hook types
- All tests passing

### Next Steps
- [ ] Publish to GitHub
- [ ] Set up CI/CD
```

### Why Journal?

1. **Context continuity** - Resume sessions without re-reading code
2. **Decision history** - Understand why things were done
3. **Progress tracking** - See what's complete vs pending
4. **Knowledge transfer** - Others can understand the evolution
