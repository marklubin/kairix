---

## Session 42 - 2024-12-30

### Goals
- [x] Add CLI subcommand for extraction prompt management
- [x] Make kp3 act as subcommand of kx
- [x] Update insights prompt to be predictive
- [x] Fix search to exclude non-narrative passage types
- [x] Add auto-embedding for session summaries

### What We Covered
- KP3 CLI: Added `prompts` subcommand for managing extraction prompts
- Insights v4: Rewrote prompt to be predictive rather than reactive
- Search filtering: Changed from opt-out to opt-in allowlist
- Auto-embedding: New session_summary passages get embeddings on creation

### What We Built

**1. KP3 `prompts` CLI subcommand** (`kp3/src/kp3/cli.py:407-562`)
- `kp3 prompts list [-n name]` - List extraction prompts
- `kp3 prompts show <name> [-v version]` - Show prompt details
- `kp3 prompts create <name> -s <file> -t <file> [-f fields.json] [--activate]` - Create new version
- `kp3 prompts activate <name> <version>` - Activate a specific version

**2. Updated kx help** (`v2-runtime/kx`)
- Documented prompts commands in `cmd_kp3` help

**3. Predictive Insights Prompt v4** (`block_manager_insights`)
- Changed from reactive ("search for what's mentioned") to predictive ("anticipate what will be needed")
- Key addition: "PREDICTIVE SEARCH STRATEGY" section
- Search for related topics, adjacent concepts, likely follow-up subjects
- Same first-person voice preserved

**4. Opt-in Search Allowlist** (`kp3/src/kp3/services/search.py`)
```python
SEARCHABLE_PASSAGE_TYPES = {"memory_shard", "session_summary"}
```
- Only these types appear in FTS, semantic, and hybrid search
- Excludes: `state:*`, `world_model_*`, and any future types by default

**5. Auto-embedding on Creation** (`kp3/src/kp3/query_service/router.py`)
```python
AUTO_EMBED_PASSAGE_TYPES = {"session_summary", "memory_shard"}
```
- Passages of these types get embeddings generated inline when created via REST API
- Backfilled existing 4 session_summary passages

### Key Concepts
1. **Opt-in vs Opt-out** - Search uses allowlist (safer for new passage types)
2. **Auto-embedding** - Removes need for batch embedding jobs for common types
3. **Predictive context** - Insights agent anticipates conversation trajectory

### Commits
- `83a9810` feat: Add prompts CLI subcommand for extraction prompt management
- `65c3006` feat: Exclude state:* from search, auto-embed session_summary
- `e6e859b` chore: Add prompt files for insights v4
- `d9e3342` refactor: Use opt-in allowlist for searchable passage types

### Next Steps
- [ ] Monitor insights v4 quality in real conversations
- [ ] Consider adding more passage types to search if needed
- [ ] Possibly add `prompts test` command for testing prompts interactively
