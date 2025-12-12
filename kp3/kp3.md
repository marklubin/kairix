# Text Processing Pipeline Schema Design

## Goal
Design a general-purpose database schema for tracking text passages through multi-step processing pipelines with full provenance/derivation chains.

## Core Requirements

1. **Passages** - Store text content at any granularity (conversation, day summary, week summary, month summary, etc.)
2. **Derivation chains** - Track how passages derive from other passages (many-to-one consolidation)
3. **Processing runs** - Configure and execute processing jobs that query subsets and produce new passages
4. **Tagging** - Flexible tagging system for passages
5. **Full provenance** - Always trace back to source material

## Key Design Decisions

### Question 1: Passage Identity
- Should passages be immutable (new version = new row) or mutable with versioning?
- Recommendation: **Immutable** - simpler provenance, append-only

### Question 2: Derivation Relationship
- Many-to-many: Multiple source passages → one derived passage
- One derived passage can have multiple sources (consolidation)
- Need join table: `passage_sources`

### Question 3: Processing Configuration
- How flexible should run configs be?
- Store as JSON for maximum flexibility vs structured columns?

---

## Proposed Schema

### Core Tables

```sql
-- The fundamental unit: a text passage
CREATE TABLE passages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Content
    content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,  -- SHA256 for dedup detection

    -- Classification
    passage_type VARCHAR(64) NOT NULL,  -- 'conversation', 'daily_summary', 'weekly_summary', 'insight', etc.
    granularity VARCHAR(32),            -- 'atomic', 'daily', 'weekly', 'monthly', 'custom'

    -- Temporal context (optional, for time-based passages)
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,

    -- Metadata
    metadata JSONB DEFAULT '{}',        -- Flexible additional data

    -- Provenance
    source_system VARCHAR(64),          -- 'chatgpt_export', 'letta', 'manual', 'pipeline'
    external_id VARCHAR(256),           -- Original ID from source system

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archived_at TIMESTAMPTZ,            -- Soft delete

    UNIQUE(content_hash)  -- Prevent exact duplicates
);

CREATE INDEX idx_passages_type ON passages(passage_type);
CREATE INDEX idx_passages_granularity ON passages(granularity);
CREATE INDEX idx_passages_period ON passages(period_start, period_end);
CREATE INDEX idx_passages_created ON passages(created_at);

-- Track derivation: which passages were used to create which
CREATE TABLE passage_derivations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- The derived (output) passage
    derived_passage_id UUID NOT NULL REFERENCES passages(id),

    -- The source (input) passage
    source_passage_id UUID NOT NULL REFERENCES passages(id),

    -- Which processing run created this derivation
    processing_run_id UUID NOT NULL REFERENCES processing_runs(id),

    -- Ordering (if source order matters)
    source_order INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(derived_passage_id, source_passage_id)
);

CREATE INDEX idx_derivations_derived ON passage_derivations(derived_passage_id);
CREATE INDEX idx_derivations_source ON passage_derivations(source_passage_id);
CREATE INDEX idx_derivations_run ON passage_derivations(processing_run_id);
```

### Tagging System

```sql
CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(128) NOT NULL UNIQUE,
    description TEXT,
    color VARCHAR(7),  -- Hex color for UI
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE passage_tags (
    passage_id UUID NOT NULL REFERENCES passages(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY(passage_id, tag_id)
);

CREATE INDEX idx_passage_tags_tag ON passage_tags(tag_id);
```

### Processing Pipeline Tables

```sql
-- Define reusable processing configurations
CREATE TABLE processing_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name VARCHAR(128) NOT NULL UNIQUE,
    description TEXT,

    -- What this processor does
    processor_type VARCHAR(64) NOT NULL,  -- 'llm_prompt', 'consolidator', 'tagger', 'extractor'

    -- Configuration (model, prompt template, parameters)
    config JSONB NOT NULL,
    /*
    Example config for llm_prompt:
    {
        "model": "claude-sonnet-4-20250514",
        "prompt_template": "Summarize the following passages into a {{granularity}} summary:\n\n{{passages}}",
        "temperature": 0.7,
        "max_tokens": 2000,
        "output_passage_type": "weekly_summary",
        "output_granularity": "weekly"
    }
    */

    -- Versioning
    version INTEGER NOT NULL DEFAULT 1,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

-- A specific execution of processing
CREATE TABLE processing_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- What config was used
    processing_config_id UUID NOT NULL REFERENCES processing_configs(id),

    -- Query that selected input passages (flexible filter DSL)
    input_query JSONB NOT NULL,
    /*
    Supports multiple query patterns:

    Time-based:
    {
        "passage_type": ["daily_summary"],
        "period_start_gte": "2025-09-01",
        "period_end_lte": "2025-09-07"
    }

    Tag-based:
    {
        "tags": ["career", "decisions"],           -- passages with ANY of these tags
        "tags_all": ["important", "actionable"]   -- passages with ALL of these tags
    }

    Topic/content-based (semantic):
    {
        "semantic_query": "discussions about job searching",
        "similarity_threshold": 0.7
    }

    Combined:
    {
        "passage_type": ["conversation"],
        "tags": ["relationships"],
        "period_start_gte": "2025-01-01",
        "exclude_tags": ["archived"]
    }

    By derivation:
    {
        "derived_from": "<passage-id>",    -- all descendants
        "not_derived_from": "<passage-id>" -- exclude a branch
    }
    */

    -- Execution status
    status VARCHAR(32) NOT NULL DEFAULT 'pending',  -- 'pending', 'running', 'completed', 'failed'

    -- Stats
    input_count INTEGER,
    output_count INTEGER,

    -- Error tracking
    error_message TEXT,

    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_runs_config ON processing_runs(processing_config_id);
CREATE INDEX idx_runs_status ON processing_runs(status);
CREATE INDEX idx_runs_created ON processing_runs(created_at);

-- Track which passages were inputs to a run (before derivation is created)
CREATE TABLE processing_run_inputs (
    processing_run_id UUID NOT NULL REFERENCES processing_runs(id) ON DELETE CASCADE,
    passage_id UUID NOT NULL REFERENCES passages(id),
    input_order INTEGER DEFAULT 0,
    PRIMARY KEY(processing_run_id, passage_id)
);
```

### Export Tracking

```sql
-- Track exports to external systems (Letta, etc.)
CREATE TABLE export_destinations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name VARCHAR(128) NOT NULL UNIQUE,        -- 'letta-corindel', 'letta-dev', etc.
    destination_type VARCHAR(64) NOT NULL,    -- 'letta', 'pinecone', 'file', etc.

    -- Connection/config info
    config JSONB NOT NULL,
    /*
    Letta example:
    {
        "base_url": "http://localhost:8283",
        "agent_id": "agent-xxxxx",
        "api_key_env": "LETTA_API_KEY"
    }
    */

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

-- Track which passages have been exported where
CREATE TABLE passage_exports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    passage_id UUID NOT NULL REFERENCES passages(id),
    destination_id UUID NOT NULL REFERENCES export_destinations(id),

    -- Forward reference to external system
    external_id VARCHAR(256),                  -- Letta archival memory ID, etc.
    external_metadata JSONB DEFAULT '{}',      -- Any extra info from external system

    -- Status
    status VARCHAR(32) NOT NULL DEFAULT 'pending',  -- 'pending', 'exported', 'failed', 'deleted'
    error_message TEXT,

    -- Timestamps
    exported_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(passage_id, destination_id)  -- One export per passage per destination
);

CREATE INDEX idx_exports_passage ON passage_exports(passage_id);
CREATE INDEX idx_exports_destination ON passage_exports(destination_id);
CREATE INDEX idx_exports_external ON passage_exports(destination_id, external_id);
CREATE INDEX idx_exports_status ON passage_exports(status);
```

### Optional: Embeddings for Semantic Search

```sql
CREATE TABLE passage_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    passage_id UUID NOT NULL REFERENCES passages(id) ON DELETE CASCADE,

    embedding_model VARCHAR(64) NOT NULL,  -- 'text-embedding-3-small', etc.
    embedding VECTOR(1536),                -- pgvector

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(passage_id, embedding_model)
);

CREATE INDEX idx_embeddings_passage ON passage_embeddings(passage_id);
-- Vector index for similarity search
CREATE INDEX idx_embeddings_vector ON passage_embeddings USING ivfflat (embedding vector_cosine_ops);
```

---

## Example Usage: Monthly Consolidation Pipeline

### 1. Import raw conversations (atomic passages)
```
passages: [
    {type: 'conversation', granularity: 'atomic', period: '2025-09-01 14:00'},
    {type: 'conversation', granularity: 'atomic', period: '2025-09-01 16:00'},
    ...
]
```

### 2. Daily summary run
```
processing_config: {
    name: 'daily_consolidator',
    processor_type: 'llm_prompt',
    config: {prompt: '...', output_type: 'daily_summary', output_granularity: 'daily'}
}

processing_run: {
    input_query: {passage_type: 'conversation', period: '2025-09-01'}
}

Result:
- New passage: {type: 'daily_summary', granularity: 'daily', period: '2025-09-01'}
- passage_derivations links it to all source conversations
```

### 3. Weekly summary run
```
processing_run: {
    input_query: {passage_type: 'daily_summary', period_start: '2025-09-01', period_end: '2025-09-07'}
}

Result:
- New passage: {type: 'weekly_summary', granularity: 'weekly'}
- Derivations link to 7 daily summaries
```

### 4. Query provenance
```sql
-- Get full derivation chain for a monthly summary
WITH RECURSIVE chain AS (
    SELECT derived_passage_id, source_passage_id, 1 as depth
    FROM passage_derivations
    WHERE derived_passage_id = :monthly_summary_id

    UNION ALL

    SELECT pd.derived_passage_id, pd.source_passage_id, c.depth + 1
    FROM passage_derivations pd
    JOIN chain c ON pd.derived_passage_id = c.source_passage_id
)
SELECT * FROM chain;
```

---

## Design Decisions (Confirmed)

1. **Embeddings**: Yes, include pgvector from the start
2. **Deployment**: Standalone service with its own DB
3. **Job runner**: Simple process manager for long-running tasks (not a full queue)
4. **Soft deletes**: Yes, add `archived_at` for soft delete
5. **Multi-tenancy**: Single user for now

---

## Tech Stack

- **uv** for project/dependency management (native builds)
- **PostgreSQL 15+** with pgvector extension
- **SQLAlchemy 2.0** async models
- **Alembic** for migrations
- **Pydantic** for config/model validation
- **FastAPI** for API (optional, can start CLI-only)
- **asyncio** task runner for long processes
- **pytest** + **pytest-asyncio** for testing
- **testcontainers** for DB integration tests

---

## Project Location

`/Users/mark/kairix-passage-processor-pipeline` (KP3)

## Project Structure

```
kairix-passage-processor-pipeline/
├── alembic/
│   └── versions/
├── src/
│   └── kp3/
│       ├── __init__.py
│       ├── config.py              # Settings, DB URL
│       ├── db/
│       │   ├── __init__.py
│       │   ├── engine.py          # Async engine setup
│       │   └── models.py          # SQLAlchemy models
│       ├── processors/
│       │   ├── __init__.py
│       │   ├── base.py            # Abstract processor
│       │   ├── llm_prompt.py      # LLM-based processing
│       │   └── importers/
│       │       ├── chatgpt.py     # ChatGPT export importer
│       │       └── sqlite.py      # Import from kairix sqlite
│       ├── exporters/
│       │   ├── __init__.py
│       │   ├── base.py            # Abstract exporter
│       │   └── letta.py           # Letta archival export
│       ├── runner/
│       │   ├── __init__.py
│       │   └── job_runner.py      # Simple async job manager
│       ├── api/                   # Optional FastAPI
│       │   └── ...
│       └── cli.py                 # Click CLI
├── tests/
│   ├── conftest.py                # Fixtures, testcontainers
│   ├── unit/
│   │   ├── test_models.py
│   │   ├── test_query_builder.py
│   │   └── test_hash.py
│   ├── integration/
│   │   ├── test_passages.py
│   │   ├── test_derivations.py
│   │   ├── test_tags.py
│   │   └── test_exports.py
│   ├── processors/
│   │   ├── test_sqlite_import.py
│   │   └── test_llm_prompt.py
│   └── e2e/
│       ├── test_pipeline.py
│       └── fixtures/
│           └── sample_data.db
├── alembic.ini
├── pyproject.toml
├── podman-compose.yml             # Dev PostgreSQL+pgvector
└── README.md
```

---

## Implementation Plan

### Phase 1: Foundation
1. Create project structure with pyproject.toml
2. Set up PostgreSQL + pgvector in podman-compose
3. Create Alembic config
4. Write initial migration with all tables
5. Create SQLAlchemy models

### Phase 2: Core Operations
1. Passage CRUD operations
2. Tag management
3. Derivation chain queries (recursive CTE)
4. Basic embedding generation

### Phase 3: Importers
1. SQLite importer (from kairix backup)
   - Import memory_shards as atomic passages
   - Preserve timestamps and metadata
2. ChatGPT JSON export importer (future)

### Phase 4: Processors
1. Abstract processor base class
2. LLM prompt processor (Anthropic)
   - Configurable prompt templates
   - Jinja2 for variable substitution
3. Processing run execution

### Phase 5: Job Runner
1. Simple async job manager
2. Status tracking and progress reporting
3. CLI commands for running/monitoring jobs

### Phase 6: Exporters
1. Abstract exporter base class
2. Letta exporter (archival memory insert via API)
   - Store returned archival ID in passage_exports.external_id
   - Handle batching for large exports
3. File exporter (JSON/markdown for backup)

### Phase 7: First Pipeline
1. Daily consolidation config
2. Weekly consolidation config
3. End-to-end test: sqlite import → daily → weekly → monthly → export to Letta

---

## Testing Strategy

### Test Infrastructure
Tests are baked into development - each phase includes tests that build on previous phases.

```
tests/
├── conftest.py               # Shared fixtures, testcontainers setup
├── unit/
│   ├── test_models.py        # Pydantic model validation
│   ├── test_query_builder.py # Query DSL parsing
│   └── test_hash.py          # Content hashing
├── integration/
│   ├── test_passages.py      # Passage CRUD with real DB
│   ├── test_derivations.py   # Derivation chain queries
│   ├── test_tags.py          # Tagging operations
│   ├── test_exports.py       # Export tracking
│   └── test_embeddings.py    # Vector operations
├── processors/
│   ├── test_sqlite_import.py # Import from kairix backup
│   ├── test_llm_prompt.py    # LLM processor (mocked)
│   └── test_letta_export.py  # Letta export (mocked)
└── e2e/
    ├── test_pipeline.py      # Full pipeline runs
    └── fixtures/
        └── sample_data.db    # Subset of real kairix data
```

### Fixtures (conftest.py)
```python
@pytest.fixture(scope="session")
def postgres_container():
    """Spin up PostgreSQL+pgvector via testcontainers."""
    with PostgresContainer("pgvector/pgvector:pg16") as pg:
        yield pg

@pytest.fixture
async def db_session(postgres_container):
    """Fresh DB session with migrations applied."""
    engine = create_async_engine(postgres_container.get_connection_url())
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()

@pytest.fixture
def sample_passages(db_session):
    """Pre-populated passages for testing."""
    ...
```

### Tests Per Phase

**Phase 1 (Foundation):**
- `test_models.py` - SQLAlchemy model instantiation, constraints
- `test_db_connection.py` - Engine setup, migrations run

**Phase 2 (Core Operations):**
- `test_passages.py` - CRUD, content hashing, dedup detection
- `test_tags.py` - Tag create/assign/remove, query by tag
- `test_derivations.py` - Create derivation, recursive CTE query

**Phase 3 (Importers):**
- `test_sqlite_import.py` - Import from fixture DB, verify passage count, metadata preservation

**Phase 4 (Processors):**
- `test_llm_prompt.py` - Mock Anthropic client, verify prompt rendering, output passage creation
- `test_processing_run.py` - Run lifecycle, status transitions, input/output tracking

**Phase 5 (Job Runner):**
- `test_job_runner.py` - Start/monitor/cancel jobs, progress callbacks

**Phase 6 (Exporters):**
- `test_letta_export.py` - Mock Letta API, verify archival insert, external_id stored
- `test_export_tracking.py` - No duplicate exports, status tracking

**Phase 7 (E2E Pipeline):**
- `test_pipeline.py` - Full flow: import → process → derive → export
  ```python
  async def test_full_pipeline(db_session, sample_sqlite_db, mock_letta):
      # Import
      await import_sqlite(sample_sqlite_db)
      passages = await list_passages(type="conversation")
      assert len(passages) == 50

      # Daily consolidation
      run = await execute_run("daily-summary", query={"period": "2025-09-01"})
      assert run.status == "completed"
      assert run.output_count == 1

      # Verify derivation chain
      daily = await get_passage(run.output_ids[0])
      sources = await get_derivation_sources(daily.id)
      assert len(sources) == 5  # 5 conversations that day

      # Export to Letta
      export = await export_passage(daily.id, "letta-test")
      assert export.external_id is not None
      assert mock_letta.archival_insert.called
  ```

### Running Tests

```bash
# All tests
uv run pytest

# Unit only (fast, no containers)
uv run pytest tests/unit

# Integration (requires testcontainers/Docker)
uv run pytest tests/integration

# E2E only
uv run pytest tests/e2e

# With coverage
uv run pytest --cov=kp3 --cov-report=html

# Watch mode during development
uv run pytest-watch tests/unit
```

### CI Integration
```yaml
# .github/workflows/test.yml
test:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: astral-sh/setup-uv@v4
    - run: uv sync
    - run: uv run pytest --cov
```

### Test Data
- `tests/e2e/fixtures/sample_data.db` - Curated subset (~50 passages) from kairix backup
- Covers: multiple days, various topics, different passage types
- Small enough for fast tests, realistic enough for meaningful E2E

---

## Files to Create

| File | Purpose |
|------|---------|
| `pyproject.toml` | Project config, dependencies |
| `podman-compose.yml` | PostgreSQL + pgvector |
| `alembic.ini` | Migration config |
| `alembic/versions/001_initial.py` | Full schema migration |
| `src/kp3/db/models.py` | SQLAlchemy models |
| `src/kp3/db/engine.py` | DB connection |
| `src/kp3/config.py` | Settings |
| `src/kp3/cli.py` | CLI entrypoint |
| `src/kp3/processors/base.py` | Abstract processor |
| `src/kp3/processors/importers/sqlite.py` | Kairix import |
| `src/kp3/exporters/base.py` | Abstract exporter |
| `src/kp3/exporters/letta.py` | Letta archival memory export |
| `src/kp3/runner/job_runner.py` | Job execution |
| `tests/conftest.py` | Test fixtures, testcontainers |
| `tests/unit/test_models.py` | Pydantic/SQLAlchemy tests |
| `tests/integration/test_passages.py` | DB integration tests |
| `tests/e2e/test_pipeline.py` | Full pipeline tests |

---

## CLI Commands (Target)

```bash
# Import from kairix sqlite backup
kp3 import sqlite /path/to/mark.db

# List passages
kp3 list --type conversation --limit 20
kp3 list --tag career --tag decisions

# Tag management
kp3 tag create "career" --description "Career-related discussions"
kp3 tag add <passage-id> career decisions
kp3 tag remove <passage-id> archived

# Create processing config
kp3 config create daily-summary --processor llm_prompt --config config.json
kp3 config create career-insights --processor llm_prompt --config career-config.json

# Run processing - time-based
kp3 run daily-summary --query '{"passage_type": "conversation", "period": "2025-09-01"}'

# Run processing - tag-based
kp3 run career-insights --query '{"tags": ["career", "decisions"]}'

# Run processing - semantic search
kp3 run topic-deep-dive --query '{"semantic_query": "job searching and interviews", "limit": 50}'

# Run processing - combined
kp3 run monthly-career --query '{"tags": ["career"], "period_start_gte": "2025-09-01", "period_end_lte": "2025-09-30"}'

# Check run status
kp3 runs list
kp3 runs show <run-id>

# Query derivation chain
kp3 provenance <passage-id>
kp3 provenance <passage-id> --depth 3  # limit depth

# Export destinations
kp3 destination create letta-corindel --type letta --config '{"base_url": "http://localhost:8283", "agent_id": "agent-xxx"}'
kp3 destination list

# Export passages to Letta
kp3 export <passage-id> letta-corindel
kp3 export --query '{"tags": ["curated"]}' letta-corindel
kp3 export --query '{"passage_type": ["monthly_summary"]}' letta-corindel --dry-run

# Check export status
kp3 exports list --destination letta-corindel
kp3 exports show <export-id>

# Cross-reference: find KP3 passage by Letta archival ID
kp3 lookup --external-id <letta-archival-id> --destination letta-corindel
```
