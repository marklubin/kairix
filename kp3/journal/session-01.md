## Session 1 - 2025-12-13

### Goals
- [x] Set up KP3 project structure
- [x] Implement database schema (4 tables)
- [x] Create core services (passages, derivations, runs)
- [x] Create processors (base, embedding)
- [ ] Create LLM prompt processor
- [ ] Create SQLite importer
- [ ] Create CLI

### What We Covered
- Project setup with uv, pyproject.toml
- PostgreSQL + pgvector via podman compose
- SQLAlchemy 2.0 async models
- Alembic migrations with async support
- Test infrastructure with pytest-asyncio

### Key Concepts Learned
1. **pytest-asyncio loop scope**: Must use `asyncio_default_fixture_loop_scope = "function"` to avoid event loop mismatch with asyncpg connections
2. **asyncpg multi-statement limitation**: Migration SQL must be split into separate `op.execute()` calls
3. **Compose container naming**: podman-compose uses underscores (kp3_postgres_1) not hyphens

### What We Built

**Database Schema (4 tables):**
- `passages` - Core content with embeddings, tsvector FTS, metadata
- `passages_archive` - Version history before updates
- `passage_derivations` - Provenance links (which passages derived from which)
- `processing_runs` - Run execution tracking with SQL input queries

**Services:**
- `services/passages.py` - CRUD, content hashing, archiving
- `services/derivations.py` - Provenance queries with recursive CTE
- `services/runs.py` - Run execution with create/update/pass actions

**Processors:**
- `processors/base.py` - ProcessorResult dataclass, Processor ABC
- `processors/embedding.py` - Ollama qwen3-embedding:4b integration

**Tests (all passing):**
- `tests/test_passages.py` - 11 tests
- `tests/test_derivations.py` - 7 tests  
- `tests/test_runs.py` - 7 tests
- `tests/test_embedding.py` - 5 tests (mocked)

### Files Created
```
kp3/
├── pyproject.toml
├── compose.yml
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/e935a08a6245_initial_schema.py
├── src/kp3/
│   ├── __init__.py
│   ├── config.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   └── models.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── passages.py
│   │   ├── derivations.py
│   │   └── runs.py
│   └── processors/
│       ├── __init__.py
│       ├── base.py
│       └── embedding.py
└── tests/
    ├── conftest.py
    ├── test_passages.py
    ├── test_derivations.py
    ├── test_runs.py
    └── test_embedding.py
```

### Challenges & Solutions
- **testcontainers + podman**: Didn't work due to ryuk image and socket issues. Solution: Use compose-managed postgres with manual test DB creation
- **Event loop mismatch**: asyncpg connections bound to specific loop. Solution: function-scoped fixtures instead of session-scoped

### Next Steps
- [ ] Write tests for LLM prompt processor
- [ ] Create `processors/llm_prompt.py` (Anthropic Claude)
- [ ] Create `importers/sqlite.py` (kairix backup import)
- [ ] Create `cli.py` (Click commands)
- [ ] E2E test: import → embed → daily aggregation

### Commands to Resume
```bash
cd /Users/mark/kairix/kp3
podman-compose up -d  # Start postgres if not running
uv run pytest  # Run all tests (should pass)
```

### Test Database Setup
The test database must exist before running tests:
```bash
podman exec kp3_postgres_1 psql -U kp3 -d postgres -c "CREATE DATABASE kp3_test"
```
