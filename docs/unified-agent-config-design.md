# Unified Agent Configuration Model

## Goal
Replace scattered agent configuration (agent_definitions, agent_voice_settings, hardcoded AgentSpec, env vars) with a single `agents` table as the source of truth. Provisioning becomes syncing this config to downstream systems (Letta, KP3 refs/hooks).

## Design Decisions
- **Per-agent LLM config**: Each agent specifies `inference_model` and `inference_provider_url`
- **Hybrid block ownership**: Agent config defines block schema (labels, limits), KP3 refs manage content
- **Flatten to instances**: No inheritance from agent_definitions, each agent has full config inline

---

## New Schema: `agents` Table

```sql
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(128) UNIQUE NOT NULL,
    description TEXT,
    system_prompt TEXT NOT NULL,

    -- Primary LLM Config (for Letta conversational agent)
    inference_model VARCHAR(256) NOT NULL,        -- e.g., "openai/Qwen2.5-7B-Instruct-AWQ"
    inference_provider_url VARCHAR(512),          -- e.g., "http://vllm:8000/v1" (custom OpenAI-compatible)
    embedding_model VARCHAR(256) NOT NULL DEFAULT 'openai/text-embedding-3-small',
    context_window INTEGER NOT NULL DEFAULT 25000,
    max_tokens INTEGER NOT NULL DEFAULT 4096,
    enable_reasoner BOOLEAN NOT NULL DEFAULT true,
    max_reasoning_tokens INTEGER DEFAULT 1024,

    -- Background LLM Config (for BlockManagerAgent: summarizer, insights, step_memory)
    background_llm_model VARCHAR(256) NOT NULL DEFAULT 'deepseek-chat',
    background_llm_url VARCHAR(512) NOT NULL DEFAULT 'https://api.deepseek.com',

    -- Block Schema (JSONB - defines structure, not content)
    -- ALL blocks use KP3 refs for content management
    block_schema JSONB NOT NULL DEFAULT '[]',

    -- Tools
    tools TEXT[] NOT NULL DEFAULT '{}',
    include_base_tools BOOLEAN NOT NULL DEFAULT true,

    -- Voice (merged from agent_voice_settings)
    -- Note: voice_id references voices table which has:
    --   - provider: "cartesia" | "kokoro" | etc.
    --   - provider_voice_id: the provider-specific voice identifier
    voice_id UUID REFERENCES voices(id) ON DELETE SET NULL,

    -- KP3 Integration (all blocks use refs)
    kp3_ref_prefix VARCHAR(128),      -- e.g., "corindel" -> refs "corindel/human/HEAD"
    kp3_hooks_enabled BOOLEAN NOT NULL DEFAULT true,

    -- Letta Sync State
    letta_agent_id VARCHAR(64),
    letta_archive_id VARCHAR(64),
    letta_synced_at TIMESTAMPTZ,
    letta_sync_hash VARCHAR(64),      -- For change detection

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);
```

**Note on inference_model format:** Letta uses `provider/model` format. For vLLM (OpenAI-compatible), use `openai/<model>` with custom `inference_provider_url`. Letta auto-detects provider from the prefix.

### Block Schema Format
ALL blocks use KP3 refs for content management (full history, hooks, branches):
```json
[
  {"label": "persona", "description": "Core identity", "limit": 5000, "kp3_ref_suffix": "persona/HEAD"},
  {"label": "human", "description": "User information", "limit": 5000, "kp3_ref_suffix": "human/HEAD"},
  {"label": "world", "description": "World context", "limit": 20000, "kp3_ref_suffix": "world/HEAD"},
  {"label": "focus", "description": "Current task focus", "limit": 5000, "kp3_ref_suffix": "focus/HEAD"},
  {"label": "last_session_summary", "description": "Session summary", "limit": 5000, "kp3_ref_suffix": "session_summary/HEAD"},
  {"label": "background_insights", "description": "Background context", "limit": 5000, "kp3_ref_suffix": "insights/HEAD"}
]
```

This means:
- BlockManagerAgent (summarizer) updates `{prefix}/session_summary/HEAD` ref → hook syncs to Letta
- BlockManagerAgent (insights) updates `{prefix}/insights/HEAD` ref → hook syncs to Letta
- Full audit trail via `passage_ref_history`
- Can use branches for A/B testing block content

---

## Implementation Phases

### Phase 1: Database & Models
1. Create migration: `alembic/versions/xxx_create_unified_agents_table.py`
2. Create SQLAlchemy model: `src/kairix_agent/agents/models.py`
3. Create Pydantic schemas: `src/kairix_agent/agents/schemas.py`
4. Create CRUD service: `src/kairix_agent/agents/service.py`

### Phase 2: BlockManagerAgent → KP3 Refs
**Critical change**: BlockManagerAgent writes to KP3 refs, hooks sync to Letta
1. Update `BlockManagerAgent.run()` to:
   - Write output to KP3 passage
   - Update ref (e.g., `{prefix}/session_summary/HEAD`)
   - Hook automatically syncs to Letta block
2. Update `BlockManagerConfig` to accept:
   - `background_llm_model` and `background_llm_url` from agent config
   - `kp3_ref_name` instead of direct `target_block`
3. Jobs (insights, summarizer, step_memory) load LLM config from `agents` table

### Phase 3: Provisioning Refactor
1. Refactor `provisioning/cli.py` to read from `agents` table
2. Add hash-based sync detection (only sync if config changed)
3. Update Letta agent creation to use unified config
4. Auto-create KP3 refs + hooks for ALL blocks from `block_schema`

### Phase 4: Migration
1. Create migration CLI: `./kx agent migrate`
2. For each existing Letta agent:
   - Create `agents` row with config extracted from Letta + agent_definitions
   - Set `letta_agent_id` to existing ID
   - Migrate voice setting from `agent_voice_settings`
   - Create KP3 refs for all blocks (including session_summary, insights)
3. Deprecate old tables (rename to `_deprecated`)

### Phase 5: CLI & API
1. Add commands: `./kx agent list`, `./kx agent create`, `./kx agent sync <name>`
2. Add REST endpoints: `/agents` CRUD
3. Remove voice assignment from separate table (now inline)

---

## Files to Modify

**New files:**
- `src/kairix_agent/agents/__init__.py`
- `src/kairix_agent/agents/models.py` - SQLAlchemy Agent model
- `src/kairix_agent/agents/schemas.py` - Pydantic schemas
- `src/kairix_agent/agents/service.py` - CRUD + provisioning logic
- `src/kairix_agent/agents/cli.py` - CLI commands
- `alembic/versions/xxx_create_unified_agents_table.py`

**Modify (BlockManagerAgent → KP3 refs):**
- `src/kairix_agent/llm/block_manager.py` - Write to KP3 refs instead of direct Letta block update
- `src/kairix_agent/llm/configs.py` - Accept LLM config from agent, use kp3_ref_name
- `src/kairix_agent/worker/jobs/insights.py` - Load LLM config from agents table
- `src/kairix_agent/worker/jobs/summarize.py` - Load LLM config from agents table
- `src/kairix_agent/worker/jobs/step_memory.py` - Load LLM config from agents table

**Modify (provisioning/voice):**
- `src/kairix_agent/provisioning/cli.py` - Use new agents service
- `src/kairix_agent/voices/service.py` - Remove agent_voice_settings, use agents.voice_id
- `src/kairix_agent/server/main.py` - Voice lookup from agents table, **fix TTS provider selection**
- `src/kairix_agent/worker/agents.py` - get_all_agents() reads from agents table

**Bug fix in main.py (TTS provider selection):**
Currently `main.py` uses `TTS_PROVIDER` env var to select TTS service. This should use `db_voice.provider` instead:
```python
# Current (wrong):
tts_provider = os.getenv("TTS_PROVIDER", "cartesia").lower()

# Fixed:
tts_provider = db_voice.provider  # "cartesia" or "kokoro" from voices table
```
This ensures voice records are self-contained (provider + provider_voice_id).

**Deprecate:**
- `src/kairix_agent/provisioning/models.py` - AgentDefinition model
- `src/kairix_agent/provisioning/blocks.py` - Hardcoded block definitions
- `src/kairix_agent/provisioning/agents.py` - AgentSpec dataclass
- `src/kairix_agent/voices/models.py` - AgentVoiceSettings model
- `src/kairix_agent/config.py` - LLM_BASE_URL, LLM_MODEL env vars (moved to per-agent)

---

## vLLM Integration

vLLM config stays infrastructure-level (docker-compose or podman run). Agents specify:
- `inference_provider_url`: Which vLLM endpoint to use
- `inference_model`: Which model (for Letta to request)

Multiple agents can share the same vLLM by using the same `inference_provider_url`.

To add vLLM to docker-compose:
```yaml
vllm-inference:
  image: vllm/vllm-openai:v0.8.5
  deploy:
    resources:
      reservations:
        devices:
          - capabilities: [gpu]
  environment:
    - VLLM_USE_V1=0
  command: >
    --model ${VLLM_MODEL:-Qwen/Qwen2.5-7B-Instruct-AWQ}
    --max-model-len 16384
    --enable-auto-tool-choice
    --tool-call-parser hermes
    --enable-prefix-caching
  ports:
    - "8001:8000"
```

Model selection via `.env` file or override per deployment.

---

## Provisioning Flow (New)

```
./kx agent sync <name>
    │
    ├── 1. Load agent from `agents` table
    │
    ├── 2. Compute config hash, compare to letta_sync_hash
    │       └── If unchanged and letta_agent_id exists → skip
    │
    ├── 3. Sync to Letta
    │       ├── Create/update agent with system_prompt, model, params
    │       ├── Create blocks from block_schema (content from KP3 refs)
    │       └── Attach tools
    │
    ├── 4. Sync KP3 refs/hooks
    │       └── For each block with kp3_ref_suffix:
    │           └── Create passage_ref_hook → letta_agent_block_update
    │
    └── 5. Update agents table
            ├── letta_agent_id
            ├── letta_sync_hash
            └── letta_synced_at
```

---

## Migration Example

```python
# Migrate existing Corindel agent
INSERT INTO agents (
    name, description, system_prompt,
    inference_model, inference_provider_url,
    embedding_model, context_window, max_tokens,
    block_schema, tools, voice_id,
    kp3_ref_prefix, letta_agent_id
) VALUES (
    'Corindel',
    'Primary conversational agent',
    (SELECT system_prompt FROM agent_definitions WHERE agent_type = 'conversational'),
    'Qwen/Qwen2.5-7B-Instruct-AWQ',
    'http://vllm:8000/v1',
    'openai/text-embedding-3-small',
    25000, 4096,
    '[{"label":"persona","limit":5000,"kp3_ref_suffix":"persona/HEAD"}, ...]'::jsonb,
    ARRAY['core_memory_append', 'core_memory_replace', ...],
    (SELECT voice_id FROM agent_voice_settings WHERE agent_id = 'agent-56a10649-420a-4639-83f3-575e12964442'),
    'corindel',
    'agent-56a10649-420a-4639-83f3-575e12964442'
);
```

---

## Testing Strategy

### Unit Tests (per phase)

**Phase 1: Database & Models**
- `tests/agents/test_models.py` - SQLAlchemy model CRUD operations
- `tests/agents/test_schemas.py` - Pydantic validation (block_schema format, model format)
- `tests/agents/test_service.py` - Service layer logic (hash computation, agent lookup)

**Phase 2: BlockManagerAgent → KP3 Refs**
- `tests/llm/test_block_manager_kp3.py` - Test ref write instead of direct Letta update
- `tests/llm/test_configs.py` - LLM config loading from agent config
- Mock KP3 client, verify correct ref paths constructed

**Phase 3: Provisioning**
- `tests/agents/test_sync.py` - Hash-based change detection
- `tests/agents/test_provisioning.py` - Letta agent creation with unified config
- Mock Letta client, verify correct API calls

### E2E Tests

**New file: `tests/e2e/test_agent_lifecycle.py`**
```python
@pytest.mark.e2e
async def test_agent_create_sync_cycle():
    """Create agent in DB → sync to Letta → verify in Letta"""

@pytest.mark.e2e
async def test_block_update_via_kp3_ref():
    """Update KP3 ref → hook fires → Letta block updated"""

@pytest.mark.e2e
async def test_insights_job_uses_agent_llm_config():
    """Insights job loads background_llm_* from agents table"""

@pytest.mark.e2e
async def test_voice_lookup_from_agents_table():
    """Voice endpoint reads voice_id from agents table"""
```

**Existing E2E to update:**
- `tests/e2e/test_conversation.py` - Ensure voice lookup still works
- `tests/e2e/test_insights.py` - Verify insights uses new config path

### Test Infrastructure
- Add `conftest.py` fixtures for:
  - `test_agent` - Creates agent in DB with test config
  - `mock_letta_client` - Mocked Letta for unit tests
  - `test_kp3_client` - Real KP3 in test DB for integration

---

## Manual Verification Checklist

### Pre-Migration (on dev/staging)
- [ ] `./kx agent list` shows empty (new table)
- [ ] `./kx psql` → `\d agents` shows correct schema
- [ ] Old system still works (agent_definitions, agent_voice_settings)

### After Migration
- [ ] `./kx agent list` shows Corindel with correct config
- [ ] `./kx agent sync Corindel` reports "already synced" (no changes)
- [ ] Voice endpoint `/voice?agent_id=<id>` returns correct voice
- [ ] Insights job runs and uses background_llm_model from agents table
- [ ] Summarizer job updates KP3 ref → hook syncs to Letta block
- [ ] `/events/{agent_id}` WebSocket receives context_state update after block change

### Voice Pipeline Test
1. Connect to `/voice?agent_id=<id>` via KMP app
2. Say something, verify STT → LLM → TTS works
3. Check logs for correct voice_id loaded from agents table

### Block Update Flow Test
1. Trigger insights job: `./kx worker trigger-insights <agent_id>`
2. Check KP3: `./kx kp3 passage ls` shows new passage
3. Check KP3 ref: `./kx kp3 sql "SELECT * FROM passage_refs WHERE name LIKE '%insights%'"`
4. Check Letta block: `./kx psql` → query Letta for block content matches KP3

---

## Migration Procedure (with Rollback)

### Pre-Migration Backup

```bash
# 1. Backup current state
./kx psql -c "
  CREATE TABLE agent_definitions_backup AS SELECT * FROM agent_definitions;
  CREATE TABLE agent_voice_settings_backup AS SELECT * FROM agent_voice_settings;
"

# 2. Export Letta agent state
./kx letta export-agent corindel > /tmp/corindel-backup.json

# 3. Record current KP3 ref heads
./kx kp3 sql "
  SELECT name, passage_id, version
  FROM passage_refs
  WHERE name LIKE 'corindel/%'
" > /tmp/kp3-refs-backup.txt
```

### Migration Steps

```bash
# 1. Run alembic migration (creates agents table)
./kx migrate

# 2. Run data migration (populates agents table from old sources)
./kx agent migrate --dry-run    # Preview what will be migrated
./kx agent migrate              # Execute migration

# 3. Verify migration
./kx agent list                 # Should show migrated agents
./kx agent show Corindel        # Verify config looks correct

# 4. Test sync (should be no-op if migration was correct)
./kx agent sync Corindel --dry-run

# 5. Test critical paths
./kx worker trigger-insights <agent_id>   # Test background job
curl http://localhost:8000/voices         # Test voice endpoint

# 6. If all tests pass, deprecate old tables
./kx psql -c "
  ALTER TABLE agent_definitions RENAME TO agent_definitions_deprecated;
  ALTER TABLE agent_voice_settings RENAME TO agent_voice_settings_deprecated;
"
```

### Rollback Procedure

**Level 1: Soft Rollback (keep new table, restore old)**
```bash
# Restore old tables from backup
./kx psql -c "
  DROP TABLE IF EXISTS agent_definitions;
  DROP TABLE IF EXISTS agent_voice_settings;
  ALTER TABLE agent_definitions_backup RENAME TO agent_definitions;
  ALTER TABLE agent_voice_settings_backup RENAME TO agent_voice_settings;
"

# Point code back to old tables (feature flag or revert commit)
git revert <migration-commit>
./kx up  # Restart with old code
```

**Level 2: Hard Rollback (drop new table)**
```bash
# Run down migration
alembic downgrade -1

# This drops agents table, restores from backup
```

**Level 3: Full Restore (Letta state)**
```bash
# If Letta agent was corrupted during sync
./kx letta delete-agent <agent_id>
./kx letta import-agent /tmp/corindel-backup.json
```

### Rollback Triggers
Rollback if any of these occur:
- Voice endpoint returns 500 or wrong voice
- Insights/summarizer jobs fail with config errors
- Letta agent responds incorrectly or blocks are wrong
- KP3 hooks fail to sync to Letta

### Post-Migration Cleanup (after 1 week stable)
```bash
# Remove backup tables
./kx psql -c "
  DROP TABLE agent_definitions_backup;
  DROP TABLE agent_voice_settings_backup;
  DROP TABLE agent_definitions_deprecated;
  DROP TABLE agent_voice_settings_deprecated;
"

# Remove deprecated code files
rm src/kairix_agent/provisioning/models.py
rm src/kairix_agent/provisioning/blocks.py
# etc.
```

---

## Implementation Order (Revised)

1. **Phase 1**: Database & Models + Unit Tests
2. **Phase 2**: BlockManagerAgent → KP3 Refs + Unit Tests
3. **Phase 3**: Provisioning Refactor + Unit Tests
4. **Run all unit tests**: `uv run pytest tests/agents tests/llm -v`
5. **Phase 4**: Migration CLI + Migration Script
6. **Dry-run migration on staging**
7. **Run E2E tests on staging**
8. **Manual verification checklist on staging**
9. **Production migration with backup**
10. **Monitor for 24-48 hours**
11. **Phase 5**: CLI & API (can be done after stable migration)
12. **Post-migration cleanup after 1 week**
