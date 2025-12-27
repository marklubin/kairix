# KP3 World Model - Manual E2E Test Procedure

> Updated Session 38. Includes shadow tables, tracking fields, agent_id segmentation.

## Goal
Walk through the full world model extraction sequence manually to verify:
1. Passage creation and storage
2. World model extraction via DeepSeek (first-person prompts)
3. Refs update correctly (world/human/HEAD, etc.)
4. Tracking fields updated (last_occurrence, occurrence_count)
5. Shadow tables synced (projects, entities, themes with canonical keys)
6. Letta agent memory blocks sync via hooks

---

## Prerequisites

### Environment Setup
```bash
cd /Users/mark/kairix/kp3

# .env file should have (with KP3_ prefix):
# KP3_DATABASE_URL=postgresql+asyncpg://kp3:kp3@salinas:5432/kp3
# KP3_DEEPSEEK_API_KEY=sk-...
# KP3_LETTA_BASE_URL=http://salinas:9000
```

### Verify Connectivity
```bash
# Database
uv run kp3 sql "SELECT 1 as test"

# Letta (note: needs trailing slash)
curl -s http://salinas:9000/v1/agents/ | jq 'length'

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
- `world_model_projects`, `world_model_entities`, `world_model_themes` (NEW - shadow tables)

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
uv run python -m kp3.scripts.seed_prompts

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

## Phase 2: Create Test Letta Agent

### Step 2.1: Create New Test Agent
```bash
curl -X POST http://salinas:9000/v1/agents/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "kp3-world-model-test",
    "memory_blocks": [
      {"label": "human", "value": "Initial human block - will be updated by KP3"},
      {"label": "persona", "value": "Initial persona block - will be updated by KP3"},
      {"label": "world", "value": "Initial world block - will be updated by KP3"}
    ],
    "llm_config": {
      "model": "gpt-4o-mini",
      "model_endpoint_type": "openai"
    },
    "embedding_config": {
      "embedding_model": "text-embedding-ada-002",
      "embedding_endpoint_type": "openai"
    }
  }' | jq '.'

# Save the agent ID!
export TEST_AGENT_ID="agent-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

### Step 2.2: Verify Memory Blocks
```bash
curl -s http://salinas:9000/v1/agents/$TEST_AGENT_ID | jq '.memory.blocks[] | {label, value}'
```

### Step 2.3: Save Initial State
```bash
curl -s http://salinas:9000/v1/agents/$TEST_AGENT_ID | jq '.memory.blocks' > /tmp/blocks_before.json
```

---

## Phase 3: Create Test Passage

```bash
uv run kp3 passage create \
  "Had a great conversation today about the Kairix voice AI project. Mark mentioned he's been working on integrating Letta for persistent memory. He seems really excited about the potential for natural voice interactions. The main challenge right now is getting the audio pipeline working smoothly. We discussed using Pipecat for the real-time audio handling." \
  --type memory_shard

# Note the passage ID from output
export PASSAGE_ID="<passage-uuid-here>"
```

---

## Phase 4: Configure Letta Sync Hooks

```bash
# Hook for human block
uv run kp3 refs add-hook world/human/HEAD letta_agent_block_update \
  "{\"agent_id\":\"$TEST_AGENT_ID\",\"block_label\":\"human\"}"

# Hook for persona block
uv run kp3 refs add-hook world/persona/HEAD letta_agent_block_update \
  "{\"agent_id\":\"$TEST_AGENT_ID\",\"block_label\":\"persona\"}"

# Hook for world block
uv run kp3 refs add-hook world/world/HEAD letta_agent_block_update \
  "{\"agent_id\":\"$TEST_AGENT_ID\",\"block_label\":\"world\"}"

# Verify hooks
uv run kp3 refs hooks
```

---

## Phase 5: Run World Model Extraction

```bash
uv run kp3 world-model commit $PASSAGE_ID --branch HEAD --model deepseek-chat --agent-id $TEST_AGENT_ID
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
9. Fire Letta sync hooks for each block

### Verify Refs Updated
```bash
uv run kp3 refs list
```

### Verify State Passage Content
```bash
# Get the world block passage and inspect
uv run kp3 sql "SELECT content FROM passages WHERE type='state:world' ORDER BY created_at DESC LIMIT 1"
```

**Expected:** JSON with `active_projects`, `key_entities`, `recurring_themes` (structured ThemeEntry objects), `key_insights`

---

## Phase 6: Verify Shadow Tables

### Check Projects Shadow Table
```bash
uv run kp3 sql "SELECT agent_id, canonical_key, name, status, occurrence_count, last_occurrence FROM world_model_projects WHERE agent_id='$TEST_AGENT_ID'"
```

**Expected:** Should see "kairix" project with:
- `canonical_key`: "kairix" (lowercase, normalized)
- `occurrence_count`: 1
- `last_occurrence`: recent timestamp

### Check Entities Shadow Table
```bash
uv run kp3 sql "SELECT agent_id, canonical_key, name, relevance, occurrence_count FROM world_model_entities WHERE agent_id='$TEST_AGENT_ID'"
```

**Expected:** Entities like "Letta", "Pipecat", "Mark" with canonical keys

### Check Themes Shadow Table
```bash
uv run kp3 sql "SELECT agent_id, canonical_key, name, description, occurrence_count FROM world_model_themes WHERE agent_id='$TEST_AGENT_ID'"
```

---

## Phase 7: Verify Letta Sync

```bash
# Get updated blocks
curl -s http://salinas:9000/v1/agents/$TEST_AGENT_ID | jq '.memory.blocks[] | {label, value}'

# Compare before/after
curl -s http://salinas:9000/v1/agents/$TEST_AGENT_ID | jq '.memory.blocks' > /tmp/blocks_after.json
diff /tmp/blocks_before.json /tmp/blocks_after.json
```

---

## Phase 8: Incremental Update (Second Tick)

### Create Another Passage
```bash
uv run kp3 passage create \
  "Continued work on Kairix today. Got the VAD (voice activity detection) working better with some tuning. Mark mentioned he's also exploring job opportunities at AI startups. The voice pipeline now handles interruptions more gracefully. Next step is to work on the world model extraction - that's what KP3 is for." \
  --type memory_shard

export PASSAGE_ID_2="<new-passage-uuid>"
```

### Process Second Passage
```bash
uv run kp3 world-model commit $PASSAGE_ID_2 --branch HEAD --agent-id $TEST_AGENT_ID
```

### Verify Version Incremented
```bash
uv run kp3 refs history world/human/HEAD
```

### Verify Tracking Fields Updated
```bash
# Kairix project should now have occurrence_count = 2
uv run kp3 sql "SELECT name, occurrence_count, last_occurrence FROM world_model_projects WHERE agent_id='$TEST_AGENT_ID' AND canonical_key='kairix'"
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
- [ ] Hooks configured for all 3 refs
- [ ] First world model extraction completes
- [ ] Refs point to valid state passages
- [ ] State passages contain valid JSON matching schemas
- [ ] **Tracking fields present** (last_occurrence, occurrence_count in world block)
- [ ] **Shadow tables populated** with agent_id and canonical_key
- [ ] Letta agent blocks updated with new content
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
  -H "Authorization: Bearer $KP3_DEEPSEEK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"test"}]}'
```

### Letta Hook Failures
```bash
# Check hook config
uv run kp3 sql "SELECT * FROM passage_ref_hooks"

# Verify agent has the block labels
curl -s http://salinas:9000/v1/agents/$TEST_AGENT_ID | jq '.memory.blocks[].label'
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
uv run kp3 sql "SELECT LENGTH(content) as chars FROM passages WHERE type='state:world' ORDER BY created_at DESC LIMIT 1"
```
Pruning only triggers when WorldBlock exceeds 5000 characters.
