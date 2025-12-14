## Session 2 - 2025-12-14

### Goals
- [x] Create CLI with Click
- [x] Test with sample data
- [x] Test LLM and embedding processors end-to-end
- [x] Test FTS, semantic, and hybrid search
- [ ] Create SQLite importer (deferred)
- [ ] E2E integration test (deferred)

### What We Covered
- Built full CLI for kp3 with run, passage, and search commands
- Fixed various issues: config imports, generated columns, embedding dimensions
- Tested both processors with real external services (Anthropic, Ollama)
- Implemented hybrid search with Reciprocal Rank Fusion (RRF)

### Key Concepts Learned
1. **Ollama dimensions parameter**: qwen3-embedding outputs 2560 dims by default, but Ollama API supports `dimensions` param to truncate to 1024 (needed for pgvector index limits)
2. **SQLAlchemy Computed columns**: Generated columns like `content_tsv` need `Computed()` wrapper to prevent insert attempts
3. **asyncpg casting**: Use `cast(:param as vector)` instead of `:param::vector` to avoid syntax errors with named parameters
4. **pgvector index limits**: Both ivfflat and hnsw indexes have 2000 dimension limit

### What We Built

**CLI Commands:**
```bash
kp3 run create <sql> -p <processor> -c <json>  # Execute processing run
kp3 run ls                                      # List runs
kp3 passage create <content>                    # Create manual_input passage
kp3 passage ls                                  # List passages
kp3 passage search <query> -m fts|semantic|hybrid  # Search passages
kp3 sql <query>                                 # Debug SQL
kp3 -v ...                                      # Verbose logging
```

**Files Modified:**
- `src/kp3/cli.py` - Full CLI with run, passage, search commands
- `src/kp3/services/runs.py` - Added verbose logging to execute_run
- `src/kp3/processors/embedding.py` - Added dimensions parameter support
- `src/kp3/db/models.py` - Fixed content_tsv Computed column
- `src/kp3/db/engine.py` - Fixed get_settings() import
- `src/kp3/config.py` - Config defaults
- `alembic/env.py` - Fixed get_settings() import
- `.env` - API keys and Ollama host
- `.gitignore` - Ignore .env files

### End-to-End Tests Performed

1. **LLM Processor**: Created summary from 4 manual_input passages
   - Provenance tracked (4 derivation links created)
   - Run logged with status, timing, counts

2. **Embedding Processor**: Generated 1024-dim embeddings for all 5 passages
   - Using Ollama qwen3-embedding:4b on salinas server
   - Dimensions truncated from native 2560 to 1024

3. **Search**:
   - FTS: `kp3 passage search "embedding" -m fts`
   - Semantic: `kp3 passage search "vector database" -m semantic`
   - Hybrid: `kp3 passage search "embedding processor test"`

### Database State
- 5 passages (4 manual_input + 1 summary)
- All passages have 1024-dim embeddings
- 4 derivation links (summary → sources)
- 2 completed runs (1 llm_prompt, 1 embedding)

### Test Results
- 36 tests passing

### Next Steps
- [ ] Create SQLite importer for kairix backup
- [ ] E2E test: import → embed → daily aggregation
- [ ] Consider adding more processor types

### Commands to Resume
```bash
cd /Users/mark/kairix/kp3
podman-compose up -d  # Start postgres if not running
source .env           # Or use direnv
uv run kp3 --help     # CLI ready
uv run pytest         # All tests pass
```
