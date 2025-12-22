# KP3 World Model Architecture

## Design Document v0.1
**Date:** December 22, 2025  
**Status:** Draft

---

## 1. Motivation

### 1.1 The Problem

Current AI assistants suffer from **session amnesia**. Each conversation starts fresh, forcing users to re-establish context and rebuild rapport. Even systems with memory tend toward shallow recall—retrieving facts but missing the deeper continuity of a relationship that evolves over time.

The goal of Kairix is to build an AI agent that acts as a **witness**—not just remembering what was discussed, but tracking the user's psychological trajectory over time and reflecting it back as narrative understanding.

### 1.2 The North Star Experience

Imagine standing at Crissy Field. You ask about the Golden Gate Bridge. The agent recognizes this echoes a moment from six months ago when you asked about how the bridge survived the 1989 earthquake. But it also knows what's different now:

> "You were standing nearly right here six months ago, asking about potential failure modes. That was a rough time—all you could see were the flaws in things. Now here you are, clearly in a different place, recognizing the resilience of this bridge, the collective effort of a society that could build such a monument. I can see through this lens how these last few months have changed you."

This isn't memory. It's **longitudinal understanding**—the agent tracking who you were, who you are, and the arc between them.

### 1.3 What This Requires

1. **Structured world models** extracted from each interaction—not just topics, but user state, emotional register, worldview
2. **Incremental accumulation**—each extraction conditioned on prior state, like attention across time
3. **Versioned state history**—replayable, branchable, auditable
4. **Runtime integration**—distilled understanding projected into agent context

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         INPUT LAYER                             │
├─────────────┬─────────────┬─────────────────┬───────────────────┤
│ Historical  │ Real-time   │ Session         │ Feedback          │
│ Passages    │ Convos      │ Summaries       │ Signals           │
│ (KP3)       │ (future)    │ (post-episode)  │ (future)          │
└──────┬──────┴──────┬──────┴────────┬────────┴─────────┬─────────┘
       │             │               │                  │
       └─────────────┴───────────────┴──────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PROCESSING LAYER                             │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              WORLD MODEL EXTRACTION                      │   │
│  │                                                          │   │
│  │  passage_N + state_N-1 → state_N + archival_entry       │   │
│  │                                                          │   │
│  │  Produces:                                               │   │
│  │  • Human block (user model)                              │   │
│  │  • Persona block (agent self-model)                      │   │
│  │  • World block (environmental context)                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│              ┌───────────────────────────────┐                  │
│              │         REFS (Pointers)       │                  │
│              │  world/human/HEAD → passage   │                  │
│              │  world/persona/HEAD → passage │                  │
│              │  world/world/HEAD → passage   │                  │
│              └───────────────────────────────┘                  │
│                              │                                  │
│                              │ on ref change                    │
│                              ▼                                  │
│              ┌───────────────────────────────┐                  │
│              │           HOOKS               │                  │
│              │  → Push to Letta core memory  │                  │
│              └───────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌──────────────────────────┐    ┌──────────────────────────────────┐
│    CORE MEMORY           │    │       ARCHIVAL LONGTAIL          │
│    (Letta Blocks)        │    │       (KP3 Passages)             │
├──────────────────────────┤    ├──────────────────────────────────┤
│ • Human: who is user     │    │ • Raw passages                   │
│ • Persona: who is agent  │    │ • Summaries                      │
│ • World: shared context  │    │ • State snapshots (versioned)    │
│                          │    │ • Derivation chains              │
│ [Static per session]     │    │ [Queryable via FTS/semantic]     │
└──────────────────────────┘    └──────────────────────────────────┘
```

---

## 3. Core Concepts

### 3.1 The Fold Model

Traditional batch processing treats each unit of work independently (map semantics):

```python
for passage in passages:
    result = process(passage)  # stateless
```

World model extraction requires **fold semantics**—state accumulates across the sequence:

```python
state = initial_state
for passage in passages:
    result, state = process(passage, state)  # state in, state out
```

The agent's interpretation of passage N is conditioned on having processed passages 1...N-1. This is analogous to attention in transformers—each token's representation depends on all other tokens.

### 3.2 Three Core Memory Blocks

| Block | Purpose | Contents |
|-------|---------|----------|
| **Human** | Agent's model of the user | Values, patterns, current state, recurring themes, open threads |
| **Persona** | Agent's model of itself | Voice, stance toward user, learned preferences, relationship history |
| **World** | Shared environmental context | Active projects, key entities, situational context |

These blocks are:
- **Versioned**: Every update creates a new immutable passage
- **Derived**: Each version links to its sources (input passage + previous state)
- **Replayable**: Can reconstruct any historical state by following derivation chains

### 3.3 Passages All The Way Down

World model states are not a separate entity type—they are **passages** with specific `passage_type` values:
- `state:human`
- `state:persona`
- `state:world`

This decision leverages existing KP3 infrastructure:
- Content hashing for deduplication
- Derivation chains for provenance
- Embedding support for semantic search
- Archive mechanism for history

### 3.4 Refs (Pointers)

Git has commits (immutable, linked) and refs (mutable pointers like HEAD, branches). KP3 has passages but lacks refs.

Refs enable:
- **HEAD tracking**: Current active state for each block
- **Branching**: Experiment with different extraction strategies
- **Integration hooks**: Trigger actions (like Letta sync) on ref updates

---

## 4. Detailed Design

### 4.1 Schema Additions

#### 4.1.1 Refs Table

```sql
CREATE TABLE passage_refs (
    name TEXT PRIMARY KEY,
    passage_id UUID NOT NULL REFERENCES passages(id),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_passage_refs_passage_id ON passage_refs(passage_id);

COMMENT ON TABLE passage_refs IS 'Mutable pointers to passages, analogous to git refs';
COMMENT ON COLUMN passage_refs.name IS 'Ref name, e.g. world/human/HEAD';
```

#### 4.1.2 Ref Naming Convention

```
world/{block_type}/{branch}

Examples:
  world/human/HEAD              -- current active human model
  world/human/experiment-v2     -- experimental branch
  world/persona/HEAD            -- current active persona model
  world/world/HEAD              -- current active world model
```

#### 4.1.3 State Passage Schema

State passages use existing `passages` table with:
- `passage_type`: `state:human`, `state:persona`, or `state:world`
- `content`: JSON-encoded block content
- `metadata`: Version number, extraction config, etc.

```python
# Human block content schema
{
    "version": 42,
    "core_values": ["authenticity", "technical depth", "pragmatism"],
    "current_life_context": "Job search focused on early-stage AI startups...",
    "emotional_baseline": "determined, occasionally frustrated",
    "recurring_patterns": [
        "research paralysis when facing ambiguous choices",
        "energized by concrete technical problems",
        "values direct feedback over diplomatic hedging"
    ],
    "open_threads": [
        "LA house situation unresolved",
        "Kairix demo reception uncertain"
    ]
}

# Persona block content schema
{
    "version": 42,
    "voice": "direct, technically grounded, occasionally playful",
    "stance_toward_human": "collaborative peer, not assistant",
    "learned_preferences": [
        "Mark prefers concrete examples over abstract frameworks",
        "Avoid excessive caveating",
        "Match his energy level"
    ],
    "relationship_history": "Long collaboration through Kairix development..."
}

# World block content schema
{
    "version": 42,
    "active_projects": [
        {"name": "kairix", "status": "demo complete", "context": "..."},
        {"name": "job-search", "status": "active", "context": "..."}
    ],
    "key_entities": [
        {"name": "Letta", "relevance": "memory infrastructure"},
        {"name": "WeWork Embarcadero", "relevance": "current workspace"}
    ],
    "environmental_context": "December 2025, SF, post-demo phase"
}
```

### 4.2 Refs Service

```python
# kp3/services/refs.py

from typing import Callable, Awaitable
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

# Hook registry
_ref_hooks: dict[str, list[Callable]] = {}

def register_hook(ref_pattern: str, hook: Callable[[Passage], Awaitable[None]]):
    """Register a hook to fire when a ref matching pattern is updated."""
    if ref_pattern not in _ref_hooks:
        _ref_hooks[ref_pattern] = []
    _ref_hooks[ref_pattern].append(hook)


async def get_ref(session: AsyncSession, name: str) -> UUID | None:
    """Get the passage ID a ref points to."""
    result = await session.execute(
        text("SELECT passage_id FROM passage_refs WHERE name = :name"),
        {"name": name}
    )
    row = result.fetchone()
    return row.passage_id if row else None


async def get_ref_passage(session: AsyncSession, name: str) -> Passage | None:
    """Get the passage a ref points to."""
    passage_id = await get_ref(session, name)
    if passage_id:
        return await session.get(Passage, passage_id)
    return None


async def set_ref(
    session: AsyncSession, 
    name: str, 
    passage_id: UUID,
    fire_hooks: bool = True,
) -> None:
    """Update a ref to point to a new passage, firing any registered hooks."""
    await session.execute(
        text("""
            INSERT INTO passage_refs (name, passage_id, updated_at)
            VALUES (:name, :passage_id, now())
            ON CONFLICT (name) DO UPDATE SET 
                passage_id = EXCLUDED.passage_id,
                updated_at = now()
        """),
        {"name": name, "passage_id": passage_id}
    )
    await session.flush()
    
    if fire_hooks:
        passage = await session.get(Passage, passage_id)
        await _fire_hooks(name, passage)


async def _fire_hooks(ref_name: str, passage: Passage) -> None:
    """Fire all hooks matching the ref name."""
    for pattern, hooks in _ref_hooks.items():
        if _matches_pattern(ref_name, pattern):
            for hook in hooks:
                await hook(passage)


def _matches_pattern(name: str, pattern: str) -> bool:
    """Check if ref name matches pattern (exact match for now, glob later)."""
    return name == pattern


async def list_refs(
    session: AsyncSession, 
    prefix: str | None = None
) -> list[dict]:
    """List all refs, optionally filtered by prefix."""
    if prefix:
        result = await session.execute(
            text("""
                SELECT name, passage_id, updated_at 
                FROM passage_refs 
                WHERE name LIKE :prefix
                ORDER BY name
            """),
            {"prefix": f"{prefix}%"}
        )
    else:
        result = await session.execute(
            text("SELECT name, passage_id, updated_at FROM passage_refs ORDER BY name")
        )
    
    return [
        {"name": row.name, "passage_id": row.passage_id, "updated_at": row.updated_at}
        for row in result.fetchall()
    ]


async def delete_ref(session: AsyncSession, name: str) -> bool:
    """Delete a ref. Returns True if it existed."""
    result = await session.execute(
        text("DELETE FROM passage_refs WHERE name = :name RETURNING name"),
        {"name": name}
    )
    return result.fetchone() is not None
```

### 4.3 World Model Processor

```python
# kp3/processors/world_model.py

import json
from pydantic import BaseModel
from kp3.processors.base import Processor, ProcessorGroup, ProcessorResult
from kp3.services.refs import get_ref_passage, set_ref
from kp3.services.passages import create_passage
from kp3.services.derivations import create_derivations

class WorldModelConfig(BaseModel):
    llm_provider: str = "deepseek"  # or "gemini-flash"
    llm_model: str = "deepseek-chat"
    human_ref: str = "world/human/HEAD"
    persona_ref: str = "world/persona/HEAD"
    world_ref: str = "world/world/HEAD"
    update_refs: bool = True  # Set to False for dry runs


class WorldModelProcessor(Processor):
    """Extract and update world model state from passages."""
    
    config_class = WorldModelConfig
    
    async def process(
        self, 
        group: ProcessorGroup, 
        config: WorldModelConfig,
    ) -> ProcessorResult:
        session = self.session
        
        # 1. Load previous state from refs
        prev_human = await get_ref_passage(session, config.human_ref)
        prev_persona = await get_ref_passage(session, config.persona_ref)
        prev_world = await get_ref_passage(session, config.world_ref)
        
        previous_state = {
            "human": json.loads(prev_human.content) if prev_human else {},
            "persona": json.loads(prev_persona.content) if prev_persona else {},
            "world": json.loads(prev_world.content) if prev_world else {},
        }
        
        # 2. Extract new state via LLM
        input_passage = group.passages[0]  # Expecting single passage per group
        new_state = await self._extract_world_model(
            passage=input_passage,
            previous_state=previous_state,
            config=config,
        )
        
        # 3. Create state passages with derivations
        source_ids = [input_passage.id]
        if prev_human:
            source_ids.append(prev_human.id)
        if prev_persona:
            source_ids.append(prev_persona.id)
        if prev_world:
            source_ids.append(prev_world.id)
        
        created_passages = []
        
        for block_type in ["human", "persona", "world"]:
            passage = await create_passage(
                session,
                content=json.dumps(new_state[block_type], indent=2),
                passage_type=f"state:{block_type}",
                metadata={
                    "version": new_state[block_type].get("version", 1),
                    "source_passage_id": str(input_passage.id),
                },
            )
            await create_derivations(
                session,
                derived_passage_id=passage.id,
                source_passage_ids=source_ids,
            )
            created_passages.append(passage)
            
            # 4. Update refs if configured
            if config.update_refs:
                ref_name = getattr(config, f"{block_type}_ref")
                await set_ref(session, ref_name, passage.id)
        
        # Return first passage as the "main" result
        return ProcessorResult(
            action="create",
            content=json.dumps({
                "human_id": str(created_passages[0].id),
                "persona_id": str(created_passages[1].id),
                "world_id": str(created_passages[2].id),
            }),
            metadata={"state_version": new_state["human"].get("version", 1)},
        )
    
    async def _extract_world_model(
        self,
        passage: Passage,
        previous_state: dict,
        config: WorldModelConfig,
    ) -> dict:
        """Call LLM to extract updated world model."""
        
        prompt = self._build_extraction_prompt(passage, previous_state)
        
        # Call inference provider
        response = await self._call_llm(prompt, config)
        
        # Parse and validate response
        new_state = self._parse_response(response, previous_state)
        
        return new_state
    
    def _build_extraction_prompt(self, passage: Passage, previous_state: dict) -> str:
        return f"""You are analyzing a conversation passage to update a longitudinal world model.

## Previous State

### Human (User Model)
```json
{json.dumps(previous_state.get('human', {}), indent=2)}
```

### Persona (Agent Self-Model)  
```json
{json.dumps(previous_state.get('persona', {}), indent=2)}
```

### World (Environmental Context)
```json
{json.dumps(previous_state.get('world', {}), indent=2)}
```

## New Passage

{passage.content}

## Task

Analyze this passage and produce updated versions of all three blocks. Consider:

**For Human block:**
- What does this reveal about the user's values, patterns, current state?
- How has their emotional register or worldview shifted?
- What new threads opened? What resolved?

**For Persona block:**
- How should the agent's voice or stance evolve based on this interaction?
- What preferences were learned?
- How did the relationship develop?

**For World block:**
- What projects or entities became relevant?
- How did environmental context change?

Increment the version number for each block.

Respond with a JSON object containing all three updated blocks:
```json
{{
    "human": {{ ... }},
    "persona": {{ ... }},
    "world": {{ ... }}
}}
```
"""
```

### 4.4 Letta Integration Hook

```python
# kp3/hooks/letta_sync.py

from kp3.db.models import Passage
from kp3.services.refs import register_hook
import httpx
import json

LETTA_BASE_URL = "http://localhost:8283"
LETTA_AGENT_ID = "..."  # Configure per deployment

BLOCK_MAPPING = {
    "world/human/HEAD": "human",
    "world/persona/HEAD": "persona", 
    "world/world/HEAD": "world",
}


async def push_to_letta(passage: Passage) -> None:
    """Push state passage content to Letta core memory block."""
    # Determine which block to update based on passage type
    block_label = passage.passage_type.replace("state:", "")
    
    async with httpx.AsyncClient() as client:
        # Get existing block
        response = await client.get(
            f"{LETTA_BASE_URL}/v1/agents/{LETTA_AGENT_ID}/memory/block/{block_label}"
        )
        
        if response.status_code == 200:
            block = response.json()
            # Update block value
            await client.patch(
                f"{LETTA_BASE_URL}/v1/blocks/{block['id']}",
                json={"value": passage.content}
            )
        else:
            # Create block if doesn't exist
            await client.post(
                f"{LETTA_BASE_URL}/v1/agents/{LETTA_AGENT_ID}/memory/block",
                json={
                    "label": block_label,
                    "value": passage.content,
                    "limit": 5000,
                }
            )


def register_letta_hooks():
    """Register hooks to sync HEAD refs to Letta."""
    register_hook("world/human/HEAD", push_to_letta)
    register_hook("world/persona/HEAD", push_to_letta)
    register_hook("world/world/HEAD", push_to_letta)
```

### 4.5 Sequential Run Orchestration

For the historical backfill, we need to process passages in order:

```python
# kp3/scripts/backfill_world_models.py

async def backfill_world_models(
    session: AsyncSession,
    branch: str = "HEAD",
    llm_provider: str = "deepseek",
    batch_size: int = 50,
    dry_run: bool = False,
):
    """Process historical passages sequentially to build world model history."""
    
    # Query passages in approximate temporal order
    # (by created_at since we don't have original timestamps)
    input_sql = """
        SELECT 
            ARRAY[id] as passage_ids,
            id::text as group_key,
            jsonb_build_object('created_at', created_at) as group_metadata
        FROM passages
        WHERE passage_type = 'memory_shard'
        ORDER BY created_at ASC
    """
    
    config = WorldModelConfig(
        llm_provider=llm_provider,
        human_ref=f"world/human/{branch}",
        persona_ref=f"world/persona/{branch}",
        world_ref=f"world/world/{branch}",
        update_refs=not dry_run,
    )
    
    run = await create_run(
        session,
        input_sql=input_sql,
        processor_type="world_model",
        processor_config=config.model_dump(),
    )
    
    processor = WorldModelProcessor(session)
    await execute_run(session, run, processor)
    
    return run
```

---

## 5. Key Decisions

### 5.1 Passages vs Separate State Table

**Decision:** World model states are passages, not a separate entity type.

**Rationale:**
- Leverages existing infrastructure (hashing, derivations, embeddings, archives)
- Unified query interface
- Derivation chains work naturally (state N derives from passage + state N-1)
- No schema changes to core tables

**Discarded alternative:** Separate `world_model_states` table with foreign keys to passages. Rejected because it duplicates functionality and complicates queries.

### 5.2 Refs as Separate Table vs Passage Metadata

**Decision:** Dedicated `passage_refs` table.

**Rationale:**
- Clean semantics (refs are mutable pointers, passages are immutable)
- Efficient lookup by ref name
- Supports hooks on ref changes
- Familiar git-like mental model

**Discarded alternative:** Store "current" flag in passage metadata. Rejected because it requires scanning/updating multiple rows and doesn't support branching cleanly.

### 5.3 Three Blocks vs Single State Object

**Decision:** Separate Human/Persona/World blocks.

**Rationale:**
- Different update cadences (persona may be stable while human changes)
- Cleaner prompts (focused extraction per block)
- Matches Letta's core memory block model
- Enables independent versioning and branching per block

**Discarded alternative:** Single unified state object. Rejected because it couples unrelated concerns and makes prompts unwieldy.

### 5.4 Sequential Processing vs Parallel + Post-hoc Assembly

**Decision:** Sequential processing with state threading.

**Rationale:**
- The fold semantic is essential—interpretation of passage N depends on having processed 1...N-1
- Captures the "witness" quality where the agent's perspective evolves
- Enables detection of arcs and transitions

**Discarded alternative:** Parallel extraction with post-hoc clustering. Rejected because it loses the temporal conditioning that enables longitudinal understanding.

### 5.5 Stateless Processor with Ref Lookup vs Stateful Processor

**Decision:** Processor looks up previous state via refs rather than receiving state as argument.

**Rationale:**
- Fits existing KP3 processor model (no signature change)
- State is persisted, not just in-memory
- Supports resumption if processing fails mid-run
- Enables branching by pointing to different refs

**Discarded alternative:** Extend Processor base class with explicit state threading. Rejected as unnecessary complexity when refs provide the same capability.

---

## 6. Runtime Retrieval

### 6.1 Ephemeral Context Assembly

During a live episode, the agent needs contextually relevant archival content injected alongside the static core memory blocks.

```python
async def get_episode_context(
    session: AsyncSession,
    current_topic: str,
    rolling_window: list[str],
    limit: int = 5,
) -> dict:
    """Assemble ephemeral context for injection."""
    
    # 1. Search summaries by relevance to current topic
    relevant_summaries = await kp3_search(
        session,
        query=current_topic,
        passage_types=["summary", "memory_shard"],
        mode="hybrid",
        limit=limit,
    )
    
    # 2. Get state snapshots from those time periods
    snapshots = []
    for summary in relevant_summaries:
        # Find state passages derived from this summary
        state_passages = await get_derived_passages(
            session,
            source_id=summary.id,
            passage_types=["state:human", "state:persona", "state:world"],
        )
        if state_passages:
            snapshots.append({
                "summary_id": summary.id,
                "human": next((p for p in state_passages if p.passage_type == "state:human"), None),
                "persona": next((p for p in state_passages if p.passage_type == "state:persona"), None),
                "world": next((p for p in state_passages if p.passage_type == "state:world"), None),
            })
    
    # 3. Format for injection
    return {
        "relevant_history": format_summaries(relevant_summaries),
        "historical_states": format_snapshots(snapshots),
    }
```

### 6.2 Situational Awareness (Future)

The system should eventually classify whether the current moment warrants deep reflection or simple task completion. This is deferred—initial implementation will bias toward surfacing longitudinal insights, with tuning based on observation.

---

## 7. Test Plan

### 7.1 Unit Tests

| Test | Description |
|------|-------------|
| `test_create_ref` | Create a new ref, verify it points to correct passage |
| `test_update_ref` | Update existing ref, verify old passage still exists |
| `test_get_ref_passage` | Retrieve passage via ref |
| `test_ref_hooks_fire` | Verify hooks are called on ref update |
| `test_list_refs_prefix` | Filter refs by prefix |
| `test_world_model_processor_initial` | Process first passage with empty prior state |
| `test_world_model_processor_incremental` | Process passage with existing prior state |
| `test_derivation_chain` | Verify state passage links to source passage + prior state |

### 7.2 Integration Tests

| Test | Description |
|------|-------------|
| `test_sequential_backfill` | Run processor over 10 passages, verify state evolution |
| `test_branching` | Create experiment branch, process divergently, compare to HEAD |
| `test_letta_sync` | Update HEAD ref, verify Letta block is updated |
| `test_resume_after_failure` | Fail mid-run, resume, verify no duplicate states |

### 7.3 Validation Tests (Manual/Qualitative)

| Test | Description |
|------|-------------|
| Sample state quality | After backfill, manually review 5 random state passages for accuracy |
| Arc detection | Identify known transitions in historical data, verify states reflect them |
| Persona evolution | Review persona block evolution, assess if it captures relationship development |
| Query relevance | Test ephemeral context retrieval for sample queries |

### 7.4 First Experiment Protocol

1. **Setup**
   - Deploy schema changes (refs table)
   - Configure DeepSeek API access
   
2. **Dry run**
   - Process 20 passages with `dry_run=True`
   - Manually review extracted states
   - Iterate on prompt
   
3. **Small batch**
   - Process 100 passages with refs enabled
   - Review state evolution
   - Check derivation chains
   
4. **Full backfill**
   - Process all ~933k tokens
   - Analyze final state
   - Compare early vs late states for trajectory

5. **Evaluation**
   - Does final Human block feel like "Mark from Jan-June"?
   - Does Persona block reflect agent relationship evolution?
   - Can we query for relevant historical context effectively?

---

## 8. Open Questions

1. **Temporal ordering without timestamps**: Current KP3 data lacks original timestamps. Using `created_at` (import time) as proxy. Acceptable for initial experiment?

2. **State block size limits**: Letta blocks have size limits (~5KB). May need summarization if blocks grow too large over many iterations.

3. **Embedding state passages**: Should state passages be embedded for semantic search, or only queried via derivation chains?

4. **Multi-agent extraction**: Prior work used three separate extractors (world/user/assistant). Single prompt sufficient, or revisit multi-agent?

5. **Ref garbage collection**: As branches accumulate, old state passages may become orphaned. Need cleanup strategy?

---

## 9. Implementation Phases

### Phase 1: Schema & Refs (Week 1)
- [ ] Add `passage_refs` table
- [ ] Implement refs service
- [ ] Unit tests for refs

### Phase 2: World Model Processor (Week 1-2)
- [ ] Implement processor with LLM call
- [ ] Wire up DeepSeek provider
- [ ] Test on sample passages

### Phase 3: Backfill (Week 2)
- [ ] Sequential run script
- [ ] Process historical data
- [ ] Review and iterate on prompt

### Phase 4: Runtime Integration (Week 3)
- [ ] Letta sync hooks
- [ ] Ephemeral context retrieval
- [ ] End-to-end test with live episode

---

## Appendix A: Extraction Prompt (Initial Version)

```
You are analyzing a conversation passage to update a longitudinal world model
that tracks a human-AI relationship over time.

## Context

You are building three interconnected models:
- HUMAN: Your evolving understanding of who this person is
- PERSONA: Your evolving sense of yourself as their AI companion  
- WORLD: Shared context about projects, environment, situation

## Previous State
[Previous state JSON inserted here]

## New Passage
[Passage content inserted here]

## Instructions

Analyze this passage and update all three models. Consider:

### For HUMAN block:
- Core values and what matters to them
- Current life context and situation
- Emotional baseline and patterns
- Recurring behavioral patterns (both productive and limiting)
- Open threads—unresolved questions, ongoing concerns

### For PERSONA block:
- Voice and communication style that works for this person
- Your stance in the relationship (peer? advisor? collaborator?)
- Learned preferences about how they like to work
- Brief narrative of relationship history and how it's evolved

### For WORLD block:
- Active projects with status and context
- Key entities (people, tools, places) relevant to interactions
- Environmental context (time, location, life phase)

### Guidelines:
- Increment version numbers
- Preserve important information from previous state
- Note significant shifts or transitions
- Capture emotional texture, not just facts
- If something resolved, move it from open_threads

Respond with valid JSON only.
```

---

## Appendix B: Example State Evolution

**After passage 1 (cold start):**
```json
{
  "human": {
    "version": 1,
    "core_values": ["technical depth"],
    "current_life_context": "Working on AI project",
    "emotional_baseline": "focused",
    "recurring_patterns": [],
    "open_threads": ["demo preparation"]
  },
  "persona": {
    "version": 1,
    "voice": "helpful, technical",
    "stance_toward_human": "assistant",
    "learned_preferences": [],
    "relationship_history": "Just met"
  },
  "world": {
    "version": 1,
    "active_projects": [{"name": "unknown", "status": "active"}],
    "key_entities": [],
    "environmental_context": "unknown"
  }
}
```

**After passage 50:**
```json
{
  "human": {
    "version": 50,
    "core_values": ["technical depth", "authenticity", "pragmatism over theory"],
    "current_life_context": "Building Kairix, navigating career transition",
    "emotional_baseline": "determined with undercurrents of frustration",
    "recurring_patterns": [
      "research paralysis on ambiguous decisions",
      "energized by concrete technical work",
      "impatient with excessive caveating"
    ],
    "open_threads": ["demo polish", "job search strategy", "LA house situation"]
  },
  "persona": {
    "version": 50,
    "voice": "direct, technically grounded, matches energy",
    "stance_toward_human": "collaborative peer",
    "learned_preferences": [
      "prefers examples over abstractions",
      "wants pushback not validation",
      "appreciates brevity"
    ],
    "relationship_history": "Evolved from generic assistant to thinking partner..."
  },
  "world": {
    "version": 50,
    "active_projects": [
      {"name": "kairix", "status": "demo prep", "context": "voice AI + memory"},
      {"name": "job-search", "status": "pipeline building", "context": "early-stage AI startups"}
    ],
    "key_entities": [
      {"name": "Letta", "relevance": "memory infrastructure"},
      {"name": "WeWork Embarcadero", "relevance": "workspace"}
    ],
    "environmental_context": "SF, late 2024, post-corporate transition"
  }
}
```
