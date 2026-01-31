# KP3 - Knowledge Processing Pipeline

A text processing pipeline with semantic search, world model extraction, and full provenance tracking. Built with PostgreSQL + pgvector for hybrid search (full-text + semantic).

## Features

- **Passage Management**: Store and organize text passages with metadata and provenance
- **Hybrid Search**: Combine full-text search (PostgreSQL tsvector) with semantic search (pgvector embeddings) using Reciprocal Rank Fusion
- **Memory Scopes**: Define dynamic search closures using refs and literal passage IDs with full versioning and revert support
- **Tags**: Flexible categorization of passages with FTS and semantic search on tag names
- **World Model Extraction**: Extract evolving human/persona/world state from conversation history using LLMs
- **Branching & Refs**: Git-like refs system for mutable pointers with version history
- **Processing Pipelines**: Configurable processors for embedding generation, LLM-based extraction, etc.
- **Multi-Agent Support**: Agent-scoped passages, tags, and scopes for multi-agent deployments
- **REST API + MCP**: FastAPI service with Model Context Protocol support

## Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API key (for embeddings)
- Optional: DeepSeek API key (for world model extraction)

### 1. Clone and Configure

```bash
git clone https://github.com/yourusername/kp3.git
cd kp3

# Create environment file
cat > .env << EOF
KP3_OPENAI_API_KEY=sk-your-openai-key
DEEPSEEK_API_KEY=sk-your-deepseek-key  # Optional
EOF
```

### 2. Start Services

```bash
# Start PostgreSQL and KP3 service
docker compose -f docker-compose.yml up -d

# Run database migrations
docker compose -f docker-compose.yml exec kp3-service uv run alembic upgrade head

# Seed default prompts (for world model extraction)
docker compose -f docker-compose.yml exec kp3-service uv run kp3 world-model seed-prompts
```

### 3. Verify Installation

```bash
# Check service health
curl http://localhost:8080/health

# Create a test passage
docker compose -f docker-compose.yml exec kp3-service uv run kp3 passage create "Hello, KP3!" -t manual_input

# List passages
docker compose -f docker-compose.yml exec kp3-service uv run kp3 passage ls
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `KP3_DATABASE_URL` | Yes | `postgresql+asyncpg://kp3:kp3@localhost:5432/kp3` | PostgreSQL connection URL |
| `KP3_OPENAI_API_KEY` | Yes | - | OpenAI API key for embeddings |
| `KP3_OPENAI_EMBEDDING_MODEL` | No | `text-embedding-3-large` | OpenAI embedding model |
| `KP3_OPENAI_EMBEDDING_DIM` | No | `1024` | Embedding dimensions |
| `DEEPSEEK_API_KEY` | No | - | DeepSeek API key for world model |
| `DEEPSEEK_BASE_URL` | No | `https://api.deepseek.com` | DeepSeek API base URL |
| `DEEPSEEK_MODEL` | No | `deepseek-chat` | DeepSeek model name |
| `KP3_ANTHROPIC_API_KEY` | No | - | Anthropic API key for LLM processing |
| `KP3_RRF_WEIGHT_FTS` | No | `1.0` | Hybrid search FTS weight |
| `KP3_RRF_WEIGHT_SEMANTIC` | No | `1.0` | Hybrid search semantic weight |
| `KP3_RRF_WEIGHT_RECENCY` | No | `0.5` | Hybrid search recency weight |

## CLI Reference

### Passages

```bash
# Create a passage
kp3 passage create "Your content here" -t passage_type

# List passages
kp3 passage ls [--type TYPE] [--limit N]

# Search passages (requires running kp3-service)
kp3 passage search "query" --agent AGENT_ID [-m fts|semantic|hybrid] [-n LIMIT]
```

### Processing Runs

```bash
# Create and execute a processing run
kp3 run create "SELECT id FROM passages WHERE ..." -p processor_type [-c '{"config": "json"}']

# List runs
kp3 run ls [--status STATUS] [--limit N]

# Execute fold operation (sequential processing with state)
kp3 run fold "SELECT id FROM passages ORDER BY created_at" -p world_model -c '{"config": "json"}'
```

### Refs (Mutable Pointers)

```bash
# List refs
kp3 refs list [--prefix PREFIX]

# Get ref details
kp3 refs get REF_NAME

# Set ref to point to passage
kp3 refs set REF_NAME PASSAGE_ID [--no-hooks]

# View ref history
kp3 refs history REF_NAME [--limit N]
```

### World Model

```bash
# Seed default extraction prompts
kp3 world-model seed-prompts

# Process a single passage
kp3 world-model step PASSAGE_ID --ref-prefix agent_name --agent-id AGENT_ID

# Process multiple passages with fold semantics
kp3 world-model fold "SELECT id FROM passages ORDER BY created_at" \
    --ref-prefix agent_name \
    --agent-id AGENT_ID

# Backfill world model from historical passages
kp3 world-model backfill [--branch BRANCH] [--limit N] [--dry-run]
```

### Branches

```bash
# Create a new branch
kp3 world-model branch create prefix/branch_name [--main] [-d "description"]

# Fork from existing branch
kp3 world-model branch fork prefix/source prefix/new_branch

# List branches
kp3 world-model branch list [--prefix PREFIX]

# Show branch details
kp3 world-model branch show prefix/branch_name

# Promote branch (copy refs to target)
kp3 world-model branch promote prefix/source [--to TARGET]

# Delete branch
kp3 world-model branch delete prefix/branch_name [--delete-refs] [--force]
```

### Prompts

```bash
# List prompts
kp3 prompts list [--name NAME]

# Show prompt details
kp3 prompts show NAME [--version VERSION]

# Create new prompt version
kp3 prompts create NAME -s system.txt -t template.txt [-f fields.json] [--activate]

# Activate prompt version
kp3 prompts activate NAME VERSION
```

### Utilities

```bash
# Execute raw SQL
kp3 sql "SELECT * FROM passages LIMIT 5"

# Import from Kairix SQLite backup
kp3 importer kairix /path/to/backup.db
```

## REST API

The kp3-service exposes a REST API on port 8080.

### Endpoints

#### Health Check
```
GET /health
```

#### Search Passages
```
GET /passages/search?query=...&mode=hybrid&search_type=content&limit=5
Header: X-Agent-ID: <agent-id>

Query Parameters:
- query: Search query text (required)
- mode: fts | semantic | hybrid (default: hybrid)
- search_type: content | tags (default: content)
- limit: Max results (default: 5, max: 50)
- period_start_after: Filter by period_start >= value
- period_end_before: Filter by period_end <= value
- created_after: Filter by created_at >= value
- created_before: Filter by created_at <= value

Response:
{
  "query": "search query",
  "mode": "hybrid",
  "search_type": "content",
  "results": [
    {
      "id": "uuid",
      "content": "passage content",
      "passage_type": "memory_shard",
      "score": 0.85
    }
  ],
  "count": 1
}
```

#### Create Passage
```
POST /passages
Header: X-Agent-ID: <agent-id>
Content-Type: application/json

{
  "content": "passage content",
  "passage_type": "memory_shard",
  "metadata": {},
  "period_start": "2024-01-01T00:00:00Z",
  "period_end": "2024-01-01T23:59:59Z"
}

Response:
{
  "id": "uuid",
  "content": "passage content",
  "passage_type": "memory_shard"
}
```

#### Get Prompt
```
GET /prompts/{name}

Response:
{
  "id": "uuid",
  "name": "human",
  "version": 1,
  "system_prompt": "...",
  "user_prompt_template": "...",
  "field_descriptions": {}
}
```

### Tag Endpoints

#### Create Tag
```
POST /tags
Header: X-Agent-ID: <agent-id>
Content-Type: application/json

{
  "name": "Python",
  "description": "Python programming content"
}

Response: { "id": "uuid", "name": "Python", ... }
```

#### List Tags
```
GET /tags?limit=100&offset=0&order_by=name
Header: X-Agent-ID: <agent-id>

Response: { "tags": [...], "count": N }
```

#### Get/Delete Tag
```
GET /tags/{tag_id}
DELETE /tags/{tag_id}
Header: X-Agent-ID: <agent-id>
```

#### Attach/Detach Tags to Passage
```
POST /passages/{passage_id}/tags
DELETE /passages/{passage_id}/tags
Header: X-Agent-ID: <agent-id>
Content-Type: application/json

{ "tag_ids": ["uuid1", "uuid2"] }
```

#### Get Passage Tags
```
GET /passages/{passage_id}/tags
Header: X-Agent-ID: <agent-id>
```

### Memory Scope Endpoints

Scopes define dynamic search closures using refs and literal passage IDs.

#### Create Scope
```
POST /scopes
Header: X-Agent-ID: <agent-id>
Content-Type: application/json

{
  "name": "working-memory",
  "description": "Active conversation context"
}

Response:
{
  "id": "uuid",
  "name": "working-memory",
  "agent_id": "agent-id",
  "head_ref": "agent-id/scope/working-memory/HEAD",
  "description": "Active conversation context",
  "created_at": "...",
  "updated_at": "..."
}
```

#### List Scopes
```
GET /scopes?limit=100&offset=0
Header: X-Agent-ID: <agent-id>

Response: { "scopes": [...], "count": N }
```

#### Get/Delete Scope
```
GET /scopes/{name}
DELETE /scopes/{name}
Header: X-Agent-ID: <agent-id>
```

#### Create Passage in Scope
```
POST /scopes/{name}/passages
Header: X-Agent-ID: <agent-id>
Content-Type: application/json

{
  "content": "Important context to remember",
  "passage_type": "memory"
}

Response:
{
  "passage_id": "uuid",
  "content": "...",
  "passage_type": "memory",
  "scope_version": 2
}
```

#### Add to Scope
```
POST /scopes/{name}/add
Header: X-Agent-ID: <agent-id>
Content-Type: application/json

{
  "passage_ids": ["uuid1", "uuid2"],
  "refs": ["agent/human/HEAD", "agent/persona/HEAD"]
}

Response: { "scope_version": 3, "modified_count": 4 }
```

#### Remove from Scope
```
POST /scopes/{name}/remove
Header: X-Agent-ID: <agent-id>
Content-Type: application/json

{
  "passage_ids": ["uuid1"],
  "refs": ["old/ref"]
}

Response: { "scope_version": 4, "modified_count": 2 }
```

#### Get Scope History
```
GET /scopes/{name}/history?limit=100
Header: X-Agent-ID: <agent-id>

Response:
{
  "history": [
    { "version": 4, "changed_at": "...", "passage_id": "def-uuid" },
    { "version": 3, "changed_at": "...", "passage_id": "prev-uuid" },
    ...
  ],
  "count": 4
}
```

#### Revert Scope
```
POST /scopes/{name}/revert
Header: X-Agent-ID: <agent-id>
Content-Type: application/json

{ "to_version": 2 }

Response: { "scope_version": 5, "reverted_from": 4 }
```

#### Search in Scope
```
GET /scopes/{name}/search?query=...&mode=hybrid&limit=10
Header: X-Agent-ID: <agent-id>

Response:
{
  "query": "...",
  "mode": "hybrid",
  "search_type": "content",
  "results": [...],
  "count": N,
  "scope": "working-memory",
  "scope_version": 5
}
```

## Database Schema

### Core Tables

| Table | Description |
|-------|-------------|
| `passages` | Text passages with embeddings and metadata |
| `passage_derivations` | Provenance tracking (which passages derived from which) |
| `passage_refs` | Mutable pointers to passages (like git refs) |
| `passage_ref_history` | Audit trail of ref changes |
| `passage_ref_hooks` | Configurable hooks triggered on ref updates |
| `processing_runs` | Processing run execution records |
| `extraction_prompts` | Versioned prompts for world model extraction |

### Tagging Tables

| Table | Description |
|-------|-------------|
| `tags` | Tags with embeddings for semantic search |
| `passage_tags` | Junction table linking passages to tags |

### Memory Scope Tables

| Table | Description |
|-------|-------------|
| `memory_scopes` | Scope metadata (name, head_ref, description) |

Note: Scope definitions are stored as passages with `passage_type="scope_definition"`.

### World Model Tables

| Table | Description |
|-------|-------------|
| `world_model_branches` | Groups of refs (human/persona/world) as a unit |
| `world_model_projects` | Shadow storage for project entities |
| `world_model_entities` | Shadow storage for durable entities |
| `world_model_themes` | Shadow storage for recurring themes |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     KP3 Service                             │
├─────────────────────────────────────────────────────────────┤
│  REST API (FastAPI)          │  MCP Server                  │
│  /passages/search            │  passage_search tool         │
│  /passages                   │  get_prompt tool             │
│  /tags                       │                              │
│  /scopes                     │                              │
│  /prompts/{name}             │                              │
├─────────────────────────────────────────────────────────────┤
│                     Services Layer                          │
│  passages.py  refs.py  search.py  tags.py  scopes.py       │
├─────────────────────────────────────────────────────────────┤
│                     Processors                              │
│  EmbeddingProcessor  WorldModelProcessor  LLMPromptProcessor│
├─────────────────────────────────────────────────────────────┤
│                     Database (PostgreSQL + pgvector)        │
│  passages  refs  tags  scopes  derivations  world_model_*  │
└─────────────────────────────────────────────────────────────┘
```

## Search Modes

### Full-Text Search (FTS)
Uses PostgreSQL's built-in tsvector for keyword matching. Fast and effective for exact terms.

### Semantic Search
Uses OpenAI embeddings with pgvector for meaning-based similarity. Finds conceptually related content.

### Hybrid Search (Default)
Combines FTS and semantic search using Reciprocal Rank Fusion (RRF):
- Each search method ranks results independently
- RRF formula: `score = Σ 1/(k + rank)` where k=60
- Weights configurable via `KP3_RRF_WEIGHT_*` env vars
- Recency bonus applied based on passage timestamp

### Search Types

- **content**: Search passage content directly (default)
- **tags**: Search by tag names/descriptions, return passages with matching tags

## Memory Scopes

Memory scopes define dynamic search closures that:
- Are agent-scoped (isolated per agent)
- Use the refs infrastructure for versioning and history
- Store definitions as passages (enabling existing infrastructure reuse)
- Support both literal passage IDs and refs (resolved at search time)
- Are fully revertable via ref history

### How Scopes Work

1. **Create a scope**: Initializes with an empty definition
2. **Add content**: Add passage IDs or ref names to the scope
3. **Search**: Only searches passages within the scope closure
4. **Versioning**: Every change creates a new version
5. **Revert**: Roll back to any previous version (non-destructive)

### Scope Definition

Scope definitions are stored as JSON in passages:
```json
{
  "refs": ["agent/human/HEAD", "agent/persona/HEAD"],
  "passages": ["uuid1", "uuid2"],
  "version": 5,
  "created_from": "previous-def-uuid"
}
```

### Dynamic Resolution

Refs in a scope are resolved at search time, not when added. This means:
- Adding a ref that doesn't exist yet is allowed
- When a ref is updated, scoped searches automatically see the new target
- Deleted passages are automatically excluded from resolution

## World Model Extraction

The world model processor extracts three types of evolving state from conversations:

1. **Human Block**: Accumulated knowledge about the human user
2. **Persona Block**: The AI agent's evolving personality/character
3. **World Block**: Current projects, entities, and themes

### Fold Semantics

World model extraction uses "fold" semantics - each passage is processed sequentially, with the output of one step becoming the input context for the next. This allows the model to build up state over time.

```bash
# Process all memory shards in order
kp3 world-model fold \
    "SELECT id FROM passages WHERE passage_type = 'memory_shard' ORDER BY created_at" \
    --ref-prefix myagent \
    --agent-id agent-12345
```

## Development

### Local Setup

```bash
# Install dependencies
uv sync

# Start PostgreSQL with pgvector
docker run -d --name kp3-postgres \
    -e POSTGRES_USER=kp3 \
    -e POSTGRES_PASSWORD=kp3 \
    -e POSTGRES_DB=kp3 \
    -p 5432:5432 \
    pgvector/pgvector:pg16

# Run migrations
uv run alembic upgrade head

# Start the service
uv run kp3-service
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Skip Docker-dependent tests
uv run pytest -m "not docker"

# Run specific test files
uv run pytest tests/test_scopes.py -v
uv run pytest tests/test_tags.py -v
```

### Code Quality

```bash
# Format code
uv run ruff format

# Lint and fix
uv run ruff check --fix

# Type check
uv run pyright
```

## License

MIT License - see LICENSE file for details.
