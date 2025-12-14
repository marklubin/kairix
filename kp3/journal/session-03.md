## Session 3 - 2025-12-14

### Goals
- [x] Create SQLite importer for kairix backup
- [x] Write tests for importer
- [x] Run importer on real data
- [x] Generate embeddings for all passages
- [x] Fix semantic/hybrid search
- [x] Improve search output with rich formatting

### What We Covered
- SQLite importer implementation and testing
- Bulk embedding generation (~3880 passages)
- Debugging asyncpg/pgvector query issues
- Rich library integration for CLI output

### Key Concepts Learned
1. **asyncpg vector casting quirk**: `ORDER BY column <=> cast(:param as vector)` returns 0 rows, but computing the score in a CTE first and then `ORDER BY score DESC` works correctly
2. **Background process for long runs**: CLI wraps everything in a transaction, so timeouts cause rollback. Use `nohup ... &` for long-running embedding jobs
3. **Rich panels**: Using `title` for header info and `subtitle` for IDs creates a clean card-like display

### What We Built

**SQLite Importer** (`src/kp3/importers/kairix_sqlite.py`):
- Imports memory_shards from Kairix SQLite backup
- Joins with agents table to get agent name
- Stores metadata: original_id, original_created_at, agent_name
- Uses uid as source_external_id for deduplication
- CLI command: `kp3 importer kairix <db_path>`

**Importer Tests** (`tests/test_kairix_importer.py`):
- 8 tests covering load, import, deduplication, empty content handling

**E2E Pipeline Tests** (`tests/test_e2e_pipeline.py`):
- 4 tests covering import → embed → aggregate flows

**Search Fix** (`src/kp3/cli.py`):
- Fixed semantic search SQL using CTE pattern
- Added rich formatting with Panel cards showing full content and UUID

### Insights & Aha Moments
- The `ORDER BY` with cast parameter issue was subtle - the query would succeed but return 0 rows
- Computing scores in a CTE and ordering by that computed value fixes the issue entirely

### Challenges & Solutions
- **Challenge**: Embedding run timing out and rolling back
- **Solution**: Run with `nohup uv run kp3 run create ... &` in background

- **Challenge**: Semantic search returning 0 results despite embeddings existing
- **Solution**: Discovered asyncpg issue with `ORDER BY col <=> cast(:param as vector)`. Fixed by using CTE to compute score first, then order by score

### Results
- 3880 memory shards imported from kairix backup
- 3885 total passages with embeddings
- FTS, semantic, and hybrid search all working
- 48 tests passing

### Next Steps
- [ ] Add search filters (--type, --after/--before, --source)

### Questions/Blockers
- None currently
