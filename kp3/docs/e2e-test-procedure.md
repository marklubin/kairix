# KP3 World Model - Manual E2E Test Procedure

## Goal

Walk through the full world model extraction sequence manually to verify:
1. Passage creation and storage
2. World model extraction via DeepSeek (first-person prompts)
3. Refs update correctly (world/human/HEAD, etc.)
4. Tracking fields updated (last_occurrence, occurrence_count)
5. Shadow tables synced (projects, entities, themes with canonical keys)

---

## Prerequisites

### Environment Setup
```bash
cd /path/to/kp3

# .env file should have:
# KP3_DATABASE_URL=postgresql+asyncpg://kp3:kp3@localhost:5432/kp3
# DEEPSEEK_API_KEY=sk-...
# KP3_OPENAI_API_KEY=sk-...
```

### Verify Connectivity
```bash
# Database
uv run kp3 sql "SELECT 1 as test"

# Migrations current
uv run alembic current
```

---

## Phase 1: Database & Prompt Setup

### Step 1.1: Run Migrations (if needed)
```bash
uv run alembic upgrade head
```

### Step 1.2: Verify Database Schema
```bash
uv run kp3 sql "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
```

**Expected tables include:**
- `passages`, `passage_refs`, `passage_ref_history`, `passage_ref_hooks`
- `extraction_prompts`
- `world_model_projects`, `world_model_entities`, `world_model_themes` (shadow tables)

### Step 1.3: Verify Shadow Tables Structure
```bash
# Check shadow table columns
uv run kp3 sql "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'world_model_projects' ORDER BY ordinal_position"
```

**Expected columns:**
- `id`, `agent_id`, `canonical_key`, `name`, `status`, `context`
- `last_occurrence`, `occurrence_count`, `created_at`, `updated_at`

### Step 1.4: Seed Extraction Prompts
```bash
uv run kp3 world-model seed-prompts

# Verify prompts exist and are active
uv run kp3 sql "SELECT name, version, is_active FROM extraction_prompts ORDER BY name"
```

**Expected output:**
- `world_model_human` (v1, active) - first-person perspective
- `world_model_persona` (v1, active) - first-person perspective
- `world_model_world` (v1, active) - first-person perspective

### Step 1.5: Inspect Prompt Content (Optional)
```bash
# Verify first-person wording
uv run kp3 sql "SELECT system_prompt FROM extraction_prompts WHERE name='world_model_human'"
```

Should contain phrases like "I am updating my understanding..." not "The agent updates..."

---

## Phase 2: Create World Model Branch

### Step 2.1: Create Agent Branch
```bash
# Create a main branch for your agent
uv run kp3 world-model branch create test-agent/HEAD --main -d "Test agent branch"

# Set an agent ID for this test
export TEST_AGENT_ID="test-agent-001"
```

### Step 2.2: Verify Branch Created
```bash
uv run kp3 world-model branch show test-agent/HEAD
```

---

## Phase 3: Create Test Passage

```bash
uv run kp3 passage create \
  "Had a great conversation today about the voice AI project. Mark mentioned he's been working on integrating persistent memory. He seems really excited about the potential for natural voice interactions. The main challenge right now is getting the audio pipeline working smoothly. We discussed using Pipecat for the real-time audio handling." \
  --type memory_shard

# Note the passage ID from output
export PASSAGE_ID="<passage-uuid-here>"
```

---

## Phase 4: Run World Model Extraction

```bash
uv run kp3 world-model step $PASSAGE_ID --ref-prefix test-agent --agent-id $TEST_AGENT_ID
```

> **Note:** The `--agent-id` flag enables shadow table sync with proper segmentation.

**Expected behavior:**
1. Load prompts from DB (first-person perspective)
2. Check refs (empty on first run - cold start)
3. Make 3 parallel DeepSeek API calls
4. Create 3 state passages (state:human, state:persona, state:world)
5. Update refs to point to new passages
6. **Update tracking fields** (last_occurrence, occurrence_count) on world block entities
7. **Prune world block** if > 5k characters (round-robin by recency)
8. **Sync to shadow tables** (projects, entities, themes with canonical keys)

### Verify Refs Updated
```bash
uv run kp3 refs list --prefix test-agent
```

### Verify State Passage Content
```bash
# Get the world block passage and inspect
uv run kp3 sql "SELECT content FROM passages WHERE passage_type='state:world' ORDER BY created_at DESC LIMIT 1"
```

**Expected:** JSON with `active_projects`, `key_entities`, `recurring_themes` (structured ThemeEntry objects), `key_insights`

---

## Phase 5: Verify Shadow Tables

### Check Projects Shadow Table
```bash
uv run kp3 sql "SELECT agent_id, canonical_key, name, status, occurrence_count, last_occurrence FROM world_model_projects WHERE agent_id='$TEST_AGENT_ID'"
```

**Expected:** Should see project entries with:
- `canonical_key`: normalized lowercase key
- `occurrence_count`: 1
- `last_occurrence`: recent timestamp

### Check Entities Shadow Table
```bash
uv run kp3 sql "SELECT agent_id, canonical_key, name, occurrence_count FROM world_model_entities WHERE agent_id='$TEST_AGENT_ID'"
```

**Expected:** Entities like "Pipecat", "Mark" with canonical keys

### Check Themes Shadow Table
```bash
uv run kp3 sql "SELECT agent_id, canonical_key, name, description, occurrence_count FROM world_model_themes WHERE agent_id='$TEST_AGENT_ID'"
```

---

## Phase 6: Incremental Update (Second Tick)

### Create Another Passage
```bash
uv run kp3 passage create \
  "Continued work on the project today. Got the VAD (voice activity detection) working better with some tuning. Mark mentioned he's also exploring job opportunities at AI startups. The voice pipeline now handles interruptions more gracefully. Next step is to work on the world model extraction." \
  --type memory_shard

export PASSAGE_ID_2="<new-passage-uuid>"
```

### Process Second Passage
```bash
uv run kp3 world-model step $PASSAGE_ID_2 --ref-prefix test-agent --agent-id $TEST_AGENT_ID
```

### Verify Version Incremented
```bash
uv run kp3 refs history test-agent/human/HEAD
```

### Verify Tracking Fields Updated
```bash
# Project should now have occurrence_count = 2
uv run kp3 sql "SELECT name, occurrence_count, last_occurrence FROM world_model_projects WHERE agent_id='$TEST_AGENT_ID'"
```

### Verify New Entities Added
```bash
# Should see new entities like "VAD" or "job search"
uv run kp3 sql "SELECT canonical_key, name, occurrence_count FROM world_model_entities WHERE agent_id='$TEST_AGENT_ID' ORDER BY last_occurrence DESC"
```

---

## Success Criteria

- [ ] Prompts seeded and active in DB (first-person perspective)
- [ ] Shadow tables exist (world_model_projects, _entities, _themes)
- [ ] Test passage created successfully
- [ ] Branch created for test agent
- [ ] First world model extraction completes
- [ ] Refs point to valid state passages
- [ ] State passages contain valid JSON matching schemas
- [ ] **Tracking fields present** (last_occurrence, occurrence_count in world block)
- [ ] **Shadow tables populated** with agent_id and canonical_key
- [ ] Second passage processed (incremental)
- [ ] Version numbers increment correctly
- [ ] **occurrence_count incremented** for recurring entities
- [ ] Derivation chain tracks lineage

---

## Troubleshooting

### DeepSeek API Errors
```bash
# Test API directly
curl https://api.deepseek.com/chat/completions \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"test"}]}'
```

### Shadow Table Issues
```bash
# Check if shadow tables have data
uv run kp3 sql "SELECT COUNT(*) FROM world_model_projects"
uv run kp3 sql "SELECT COUNT(*) FROM world_model_entities"
uv run kp3 sql "SELECT COUNT(*) FROM world_model_themes"

# Check for duplicate canonical keys (should not exist per agent)
uv run kp3 sql "SELECT agent_id, canonical_key, COUNT(*) FROM world_model_projects GROUP BY agent_id, canonical_key HAVING COUNT(*) > 1"
```

### Pruning Not Happening
```bash
# Check world block size
uv run kp3 sql "SELECT LENGTH(content) as chars FROM passages WHERE passage_type='state:world' ORDER BY created_at DESC LIMIT 1"
```
Pruning only triggers when WorldBlock exceeds 5000 characters.
