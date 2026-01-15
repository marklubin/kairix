# Unified Cognitive Memory Architecture

> Design document for KP3's cognitive memory system

## Core Insight

**Two-tier architecture:**

1. **Foundation Tier** (domain-agnostic primitives):
   - Passages, Refs, Branches, Hooks, Derivations
   - General-purpose building blocks

2. **Cognitive Tier** (domain-specific, built on foundation):
   - CognitiveFrame, Perceptions, Cognition processes
   - **CognitiveFrames are themselves passages with refs** - versioned, branchable, queryable

**Key principle:** Everything is passages and refs. The cognitive layer is metadata that describes how to interpret and evolve them.

## Foundation Tier (Domain-Agnostic)

### Passages

Immutable content units. The atomic storage primitive.

```python
class Passage:
    id: UUID
    content: str
    content_hash: str      # dedup
    embedding: Vector      # semantic search
    passage_type: str      # classification (foundation level)
    agent_id: str | None   # optional ownership
    metadata: dict
    created_at: datetime
```

### Refs

Mutable name → passage pointers. The addressing primitive.

```python
class PassageRef:
    name: str              # e.g., "corindel/perception/persona"
    passage_id: UUID       # what it points to
    updated_at: datetime
    metadata: dict
```

Refs are hierarchical by convention: `{namespace}/{category}/{name}`

### Branches

Groupings of refs with configuration. Already exists as `WorldModelBranch`.

### Hooks

Side effects on ref updates. Already exists as `PassageRefHook`.

### Derivations

Provenance chains. Already exists as `PassageDerivation`.

## Cognitive Tier (Domain-Specific)

Built entirely on foundation primitives. **CognitiveFrames are passages. Perceptions are refs.**

### CognitiveFrame

A CognitiveFrame defines an agent's cognitive configuration:
- Which perceptions are active
- What cognition processes update them
- How search is scoped

**CognitiveFrame IS a passage** pointed to by a ref:
```
Ref: "corindel/frame/production" → Passage containing:
{
  "name": "Corindel-Production",
  "agent_id": "corindel",

  "perceptions": [
    {"name": "persona", "ref": "corindel/perception/persona", "process": "step_persona"},
    {"name": "human", "ref": "corindel/perception/human", "process": "step_human"},
    {"name": "world", "ref": "corindel/perception/world", "process": "step_world"}
  ],

  "cognition_config": {
    "llm_provider": "openai",
    "model": "gpt-4o",
    "processes": {
      "step_persona": {"prompt": "step_persona", "trigger": "session_end"},
      "step_human": {"prompt": "step_human", "trigger": "session_end"}
    }
  },

  "hooks_enabled": true
}
```

Because it's a passage:
- It has a content_hash (versioned)
- It can be derived from a previous frame (branching)
- It can be searched/queried
- Multiple frames can exist: "corindel/frame/production", "corindel/frame/experiment"

### Perceptions

**Perceptions are refs** in the cognitive tier. They represent the agent's "view" of something.

All perceptions function identically - they're refs pointing to passages that can be incremented via `increment_perception`. The frame simply lists which perceptions exist for an agent.

Some perceptions start in the initial frame config (persona, human, world), others can be added later (entities, concepts). This is configuration, not a type distinction - the mechanics are identical.

### Semantic Deduplication (Optional)

When creating new perceptions that might duplicate existing ones (like entities), the API can optionally check for semantic similarity:

```python
async def get_or_create_perception(
    session,
    agent_id: str,
    ref_prefix: str,      # e.g., "corindel/entity"
    content: str,
    *,
    dedup: bool = False,  # Enable semantic dedup
    similarity_threshold: float = 0.85,
) -> str:
    """Return ref name for perception, optionally deduping."""

    if dedup:
        # Search existing perceptions with this prefix
        existing = await search_similar(session, ref_prefix, content, threshold)
        if existing:
            return existing.ref_name  # Reuse existing

    # Create new perception
    ref_name = f"{ref_prefix}/{generate_slug(content)}"
    # ... create passage and ref
    return ref_name
```

This is a feature of the `create_perception` API, not a fundamental type distinction.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     FOUNDATION TIER (Domain-Agnostic)                    │
│                                                                         │
│   PASSAGES                  REFS                    HOOKS               │
│   ┌──────────┐             ┌──────────┐            ┌──────────┐        │
│   │ content  │◄────────────│ name →   │───────────►│ on update│        │
│   │ hash     │             │ passage  │            │ fire     │        │
│   │ embedding│             │ id       │            │ action   │        │
│   └──────────┘             └──────────┘            └──────────┘        │
│                                                                         │
│   DERIVATIONS               BRANCHES (existing)                         │
│   ┌──────────┐             ┌──────────┐                                │
│   │ source → │             │ group of │                                │
│   │ derived  │             │ refs     │                                │
│   └──────────┘             └──────────┘                                │
└─────────────────────────────────────────────────────────────────────────┘
                              ▲
                              │ built on
                              │
┌─────────────────────────────────────────────────────────────────────────┐
│                     COGNITIVE TIER (Domain-Specific)                     │
│                                                                         │
│   COGNITIVE FRAME (is a Passage with a Ref)                             │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │  Ref: "corindel/frame/production"                               │  │
│   │  ↓                                                              │  │
│   │  Passage: {                                                     │  │
│   │    perceptions: [ ... ],    // flat list of perception refs     │  │
│   │    cognition_config: { processes: {...} },                      │  │
│   │    hooks_enabled: true                                          │  │
│   │  }                                                              │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                              │                                          │
│                              │ defines                                  │
│                              ▼                                          │
│   PERCEPTIONS (are Refs - all work identically)                         │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │    corindel/perception/persona → Passage (self-model)           │  │
│   │    corindel/perception/human   → Passage (user-model)           │  │
│   │    corindel/perception/world   → Passage (world-context)        │  │
│   │    corindel/entity/mark-lubin  → Passage (entity model)         │  │
│   │    corindel/concept/kairix     → Passage (concept model)        │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│   COGNITION: input + previous → new (fold operation)                    │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │  increment_perception() - same for ALL perceptions              │  │
│   │  (creates passage, updates ref, fires hooks)                    │  │
│   │                                                                 │  │
│   │  Optional: dedup flag when creating new perceptions             │  │
│   └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## API Design

### Foundation APIs (domain-agnostic)

```
# Passages
POST /passages                    # Create
GET  /passages/{id}               # Get by ID
GET  /passages/search             # Search all (admin/operational)

# Refs
GET  /refs/{name}                 # Get ref + passage
GET  /refs?prefix=...             # List by prefix
PUT  /refs/{name}                 # Update (fires hooks)
GET  /refs/{name}/history         # Historical values

# Derivations
GET  /passages/{id}/sources       # What was this derived from?
GET  /passages/{id}/derived       # What derived from this?
```

### Cognitive APIs (domain-specific)

```
# Cognitive Frames
GET  /frames                      # List frames for agent
GET  /frames/{name}               # Get frame (parsed perception list)
POST /frames                      # Create new frame
POST /frames/{name}/fork          # Fork from existing
POST /frames/{name}/activate      # Set as active

# Perceptions
GET  /perceptions                 # List perceptions in active frame
GET  /perceptions/{name}          # Get perception content
POST /perceptions                 # Create (with dedup check)

# Cognition
POST /cognition/compute           # Run cognition process
  {
    "frame": "corindel/frame/production",
    "perception": "corindel/perception/persona",
    "input": "...",
    "process": "step_persona"
  }

# Search (scoped to active frame)
GET  /search?query=X&frame=corindel/frame/production
```

## Example: Frame Evolution

```
Initial Frame (v1):
  Ref: "corindel/frame/production" → Passage-F1
  Content: {
    perceptions: [
      {name: "persona", ref: "corindel/perception/persona"},
      {name: "human", ref: "corindel/perception/human"},
      {name: "world", ref: "corindel/perception/world"}
    ]
  }

After conversation, agent learns about entity:
  Cognition detects new entity "Mark Lubin"
  Dedup check: no similar entity exists (optional)
  Create: corindel/entity/mark-lubin → Passage-E1

  Update frame (v2):
  Ref: "corindel/frame/production" → Passage-F2
  Content: {
    perceptions: [
      {name: "persona", ref: "corindel/perception/persona"},
      {name: "human", ref: "corindel/perception/human"},
      {name: "world", ref: "corindel/perception/world"},
      {name: "entity:mark-lubin", ref: "corindel/entity/mark-lubin"}
    ]
  }

  Derivation: Passage-F2 derived from Passage-F1

Later, another reference to "Mark":
  Dedup check: similar entity exists (mark-lubin, similarity=0.95)
  Update existing: corindel/entity/mark-lubin → Passage-E2
  Frame stays at v2 (no new perception, just updated existing)
```

## The Computation Primitive

### `increment_perception`

The single primitive that ALL cognition reduces to:

```python
async def increment_perception(
    input_content: str,
    perception_ref: str,
    prompt_name: str,
    *,
    agent_id: str,
    context_refs: list[str] | None = None,  # Additional refs to read
    search_query: str | None = None,         # Optional KP3 search for context
) -> Passage:
    """
    The fold operation: (input, previous) → new

    1. Load previous state from perception_ref (if exists)
    2. Optionally load context from additional refs
    3. Optionally search KP3 for relevant context
    4. Load prompt from KP3
    5. Call LLM: input + previous + context + prompt → new_content
    6. Create new passage
    7. Create derivation link to previous
    8. Update perception_ref to point to new passage
    9. Hooks fire automatically (e.g., Letta sync)

    Returns the new passage.
    """
```

### API Endpoint

```
POST /cognition/increment
{
  "input_content": "...",
  "perception_ref": "corindel/perception/persona",
  "prompt_name": "step_persona",
  "context_refs": ["corindel/perception/human", "corindel/perception/world"],
  "search_query": "relevant topics"  // optional
}
Header: X-Agent-ID

Returns: {
  "passage_id": "...",
  "ref_name": "...",
  "content": "...",
  "previous_passage_id": "..." // if existed
}
```

## Mapping Existing Jobs to the Primitive

### Current State (v2-runtime)

| Job | Input | Previous | Output | Letta Block |
|-----|-------|----------|--------|-------------|
| `summarize_session` | transcript | none | session_summary | last_session_summary |
| `trigger_insights` | last 10 msgs | insights block | insights | background_insights |
| `step_memory_blocks` (persona) | summary | persona block | step:persona | persona |
| `step_memory_blocks` (human) | summary | human block | step:human | human |
| `step_memory_blocks` (world) | summary | world block | step:world | world |

### Current State (KP3)

| Processor | Input | Previous (via refs) | Output | Refs Updated |
|-----------|-------|---------------------|--------|--------------|
| `WorldModelProcessor` | passage | human/persona/world refs | state:* passages | world/*/HEAD |

### Migration Mapping

Each existing job becomes a call to `increment_perception`:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ EXISTING: summarize_session                                             │
│                                                                         │
│   BlockManagerAgent(SUMMARIZER_CONFIG)                                  │
│     input: transcript                                                   │
│     target_block: last_session_summary                                  │
│     kp3_storage: session_summary                                        │
│                                                                         │
│ BECOMES: increment_perception(                                          │
│     input_content=transcript,                                           │
│     perception_ref="{agent}/session/summary",                           │
│     prompt_name="block_manager_summarizer",                             │
│   )                                                                     │
│   + Hook: letta_agent_block_update → last_session_summary               │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ EXISTING: trigger_insights                                              │
│                                                                         │
│   BlockManagerAgent(INSIGHTS_CONFIG)                                    │
│     input: last 10 messages                                             │
│     target_block: background_insights                                   │
│     tools: search_kp3                                                   │
│     kp3_storage: None                                                   │
│                                                                         │
│ BECOMES: increment_perception(                                          │
│     input_content=formatted_messages,                                   │
│     perception_ref="{agent}/insight/latest",                            │
│     prompt_name="block_manager_insights",                               │
│     search_query=<extracted from messages>                              │
│   )                                                                     │
│   + Hook: letta_agent_block_update → background_insights                │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ EXISTING: step_memory_blocks (persona)                                  │
│                                                                         │
│   BlockManagerAgent(PERSONA_STEP_CONFIG)                                │
│     input: session summary                                              │
│     reads: persona, human, world blocks from Letta                      │
│     target_block: persona                                               │
│     tools: search_kp3                                                   │
│     kp3_storage: step:persona                                           │
│                                                                         │
│ BECOMES: increment_perception(                                          │
│     input_content=session_summary,                                      │
│     perception_ref="{agent}/perception/persona",                        │
│     prompt_name="step_persona",                                         │
│     context_refs=[                                                      │
│       "{agent}/perception/human",                                       │
│       "{agent}/perception/world"                                        │
│     ],                                                                  │
│   )                                                                     │
│   + Hook: letta_agent_block_update → persona                            │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ EXISTING: step_memory_blocks (human)                                    │
│                                                                         │
│ BECOMES: increment_perception(                                          │
│     input_content=session_summary,                                      │
│     perception_ref="{agent}/perception/human",                          │
│     prompt_name="step_human",                                           │
│     context_refs=[                                                      │
│       "{agent}/perception/persona",                                     │
│       "{agent}/perception/world"                                        │
│     ],                                                                  │
│   )                                                                     │
│   + Hook: letta_agent_block_update → human                              │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ EXISTING: step_memory_blocks (world)                                    │
│                                                                         │
│ BECOMES: increment_perception(                                          │
│     input_content=session_summary,                                      │
│     perception_ref="{agent}/perception/world",                          │
│     prompt_name="step_world",                                           │
│     context_refs=[                                                      │
│       "{agent}/perception/persona",                                     │
│       "{agent}/perception/human"                                        │
│     ],                                                                  │
│   )                                                                     │
│   + Hook: letta_agent_block_update → world                              │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ EXISTING: WorldModelProcessor (KP3 batch)                               │
│                                                                         │
│   Makes 3 parallel LLM calls                                            │
│   Reads from world/*/HEAD refs                                          │
│   Creates state:* passages                                              │
│   Updates refs                                                          │
│                                                                         │
│ BECOMES: 3x increment_perception() calls (can be parallel)              │
│   - increment_perception(..., perception_ref="world/human/HEAD", ...)   │
│   - increment_perception(..., perception_ref="world/persona/HEAD", ...) │
│   - increment_perception(..., perception_ref="world/world/HEAD", ...)   │
│                                                                         │
│   Note: WorldModelProcessor also does shadow table sync - that becomes  │
│   a separate hook or post-processing step                               │
└─────────────────────────────────────────────────────────────────────────┘
```

## Orchestration: Who Calls increment_perception?

The orchestration stays in v2-runtime (job scheduling, triggers). KP3 just provides the primitive.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          V2-RUNTIME                                      │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    SAQ JOB QUEUE                                 │   │
│  │                                                                  │   │
│  │  check_session_boundaries (cron)                                 │   │
│  │    → enqueue summarize_session                                   │   │
│  │                                                                  │   │
│  │  summarize_session                                               │   │
│  │    → POST /cognition/increment (session/summary)                 │   │
│  │    → enqueue step_memory_blocks                                  │   │
│  │                                                                  │   │
│  │  step_memory_blocks                                              │   │
│  │    → POST /cognition/increment (perception/persona) ─┐          │   │
│  │    → POST /cognition/increment (perception/human)  ──┼─ parallel│   │
│  │    → POST /cognition/increment (perception/world)  ──┘          │   │
│  │                                                                  │   │
│  │  trigger_insights (after LLM response)                           │   │
│  │    → POST /cognition/increment (insight/latest)                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            KP3                                           │
│                                                                         │
│  POST /cognition/increment                                              │
│    1. Load previous from perception_ref                                 │
│    2. Load context from context_refs                                    │
│    3. Optional: search KP3 for additional context                       │
│    4. Load prompt                                                       │
│    5. Call LLM                                                          │
│    6. Create passage + derivation                                       │
│    7. Update ref (fires hooks → Letta sync)                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## What Changes, What Stays

### In v2-runtime (mostly stays):
- **Job scheduling**: cron triggers, event-based enqueueing ✓
- **Job logic**: transform to call KP3 API instead of BlockManagerAgent
- **Event publishing**: stays ✓
- **Session management**: stays ✓

### In KP3 (new):
- **`/cognition/increment` endpoint**: the single primitive
- **Perception ref management**: create/update refs
- **Hook firing**: on ref update → Letta sync

### Removed from v2-runtime:
- **`BlockManagerAgent` class**: replaced by KP3 API call
- **`OpenAICompatibleClient`**: LLM calls move to KP3
- **Direct Letta block updates**: handled by KP3 hooks

## Ref Naming for Existing Blocks

| Current Letta Block | New Perception Ref |
|---------------------|-------------------|
| `last_session_summary` | `{agent}/session/summary` |
| `background_insights` | `{agent}/insight/latest` |
| `persona` | `{agent}/perception/persona` |
| `human` | `{agent}/perception/human` |
| `world` | `{agent}/perception/world` |

## Hook Configuration

Each perception ref that should sync to Letta needs a hook:

```sql
INSERT INTO passage_ref_hooks (ref_name, action_type, config, enabled)
VALUES
  ('corindel/session/summary', 'letta_agent_block_update',
   '{"agent_id": "agent-xxx", "block_label": "last_session_summary"}', true),

  ('corindel/insight/latest', 'letta_agent_block_update',
   '{"agent_id": "agent-xxx", "block_label": "background_insights"}', true),

  ('corindel/perception/persona', 'letta_agent_block_update',
   '{"agent_id": "agent-xxx", "block_label": "persona"}', true),

  ('corindel/perception/human', 'letta_agent_block_update',
   '{"agent_id": "agent-xxx", "block_label": "human"}', true),

  ('corindel/perception/world', 'letta_agent_block_update',
   '{"agent_id": "agent-xxx", "block_label": "world"}', true);
```

## Implementation Plan

### Phase 1: Foundation Tier - Expose Existing APIs

Foundation primitives mostly exist. Expose them via HTTP.

**New API endpoints in KP3:**

1. **`kp3/src/kp3/api/refs.py`** - Ref operations
   ```
   GET  /refs/{name}           # Get ref + resolve passage
   GET  /refs?prefix=...       # List by prefix
   PUT  /refs/{name}           # Update ref (fires hooks)
   GET  /refs/{name}/history   # Historical values
   ```

2. **`kp3/src/kp3/api/derivations.py`** - Provenance operations
   ```
   GET  /passages/{id}/sources  # What was this derived from?
   GET  /passages/{id}/derived  # What derived from this?
   ```

3. **`kp3/src/kp3/api/passages.py`** - Add admin search
   ```
   GET  /admin/passages/search  # Search ALL passages (no scope)
   ```

**Existing (no changes needed):**
- `kp3/src/kp3/services/refs.py` ✓
- `kp3/src/kp3/services/derivations.py` ✓
- `kp3/src/kp3/services/search.py` ✓

### Phase 2: Cognitive Tier - CognitiveFrame

CognitiveFrame is just a passage with a ref. No new tables needed.

**New in KP3:**

1. **`kp3/src/kp3/services/frames.py`** - Frame operations
   ```python
   async def get_frame(session, ref_name: str) -> dict:
       """Load and parse frame passage."""
       passage = await get_ref_passage(session, ref_name)
       return json.loads(passage.content)

   async def create_frame(
       session,
       agent_id: str,
       name: str,
       perceptions: list[dict],
       cognition_config: dict,
   ) -> PassageRef:
       """Create frame passage and ref."""
       content = json.dumps({
           "name": name,
           "agent_id": agent_id,
           "perceptions": perceptions,  # flat list
           "cognition_config": cognition_config,
           "hooks_enabled": True,
       })
       passage = await create_passage(session, content, passage_type="cognitive_frame")
       ref_name = f"{agent_id}/frame/{slugify(name)}"
       await set_ref(session, ref_name, passage.id, fire_hooks=False)
       return ref_name

   async def fork_frame(session, source_ref: str, new_name: str) -> str:
       """Create new frame derived from source."""
       # Load source
       # Create new passage with same content
       # Link derivation
       # Create new ref

   async def update_frame_perceptions(
       session,
       frame_ref: str,
       add_perception: dict | None = None,
       remove_perception: str | None = None,
   ) -> str:
       """Update frame's perceptions (creates new version)."""
   ```

2. **`kp3/src/kp3/api/frames.py`** - HTTP endpoints
   ```
   GET  /frames                 # List frames for agent
   GET  /frames/{name}          # Get frame content
   POST /frames                 # Create new
   POST /frames/{name}/fork     # Fork
   POST /frames/{name}/activate # Set active
   ```

### Phase 3: Cognition & Perceptions

**New in KP3:**

1. **`kp3/src/kp3/services/cognition.py`** - The fold operation
   ```python
   async def compute(
       session,
       frame_ref: str,
       perception_ref: str,
       input_content: str,
       process_name: str,
   ) -> Passage:
       """Run cognition: input + previous → new."""
       # 1. Load frame to get cognition_config
       frame = await get_frame(session, frame_ref)
       process = frame["cognition_config"]["processes"][process_name]

       # 2. Load current perception
       previous = await get_ref_passage(session, perception_ref)

       # 3. Load prompt
       prompt = await get_prompt(session, process["prompt"])

       # 4. Call LLM
       new_content = await call_llm(input_content, previous.content, prompt)

       # 5. Create new passage
       passage = await create_passage(session, new_content, ...)

       # 6. Link derivation
       await create_derivation(session, passage.id, [previous.id])

       # 7. Update ref (fires hooks if frame.hooks_enabled)
       await set_ref(session, perception_ref, passage.id,
                     fire_hooks=frame["hooks_enabled"])

       return passage
   ```

2. **`kp3/src/kp3/services/perceptions.py`** - Perception operations with optional dedup
   ```python
   async def get_or_create_perception(
       session,
       agent_id: str,
       ref_prefix: str,      # e.g., "corindel/entity"
       content: str,
       frame_ref: str | None = None,  # If provided, adds to frame
       *,
       dedup: bool = False,
       similarity_threshold: float = 0.85,
   ) -> str:
       """Get existing or create new perception, optionally deduping."""
       if dedup:
           existing = await search_similar(session, ref_prefix, content, threshold)
           if existing:
               return existing.ref_name

       # Create new perception
       passage = await create_passage(session, content, ...)
       ref_name = f"{ref_prefix}/{generate_slug(content)}"
       await set_ref(session, ref_name, passage.id)

       # Optionally update frame to include new perception
       if frame_ref:
           await update_frame_perceptions(
               session, frame_ref,
               add_perception={"name": ref_name.split("/")[-1], "ref": ref_name}
           )

       return ref_name
   ```

3. **`kp3/src/kp3/api/cognition.py`** - HTTP endpoint
   ```
   POST /cognition/compute
   POST /perceptions          # Create with dedup
   GET  /perceptions          # List in frame
   ```

### Phase 4: Search Scoped by Frame

**Modify in KP3:**

1. **`kp3/src/kp3/services/search.py`**
   ```python
   async def search(
       session,
       query: str,
       agent_id: str,
       *,
       frame_ref: str | None = None,  # NEW - scope to frame
       mode: SearchMode = "hybrid",
       limit: int = 5,
   ) -> list[SearchResult]:
       if frame_ref:
           # Load frame, get all perception refs
           frame = await get_frame(session, frame_ref)
           perception_refs = [p["ref"] for p in frame["perceptions"]]

           # Get passage_ids from those refs
           passage_ids = [await get_ref(session, r) for r in perception_refs]

           # Search within those passages
           return await search_within(session, query, passage_ids, mode, limit)
       else:
           # Current behavior: all searchable types
   ```

### Phase 5: Wire Up v2-runtime

**Modify in v2-runtime:**

1. **Agent startup** - Resolve frame ref from config/DB
2. **`block_manager.py`** - Call `/cognition/compute`
3. **`summarize.py`** - Use cognition for summary
4. **Worker jobs** - Pass frame context

### Phase 6: Context Window Management

1. **`check_context_window`** job
2. **Redis lock** for summarization

### Phase 7: Social Agents (Future)

- Entity perceptions: `{agent}/entity/{name}`
- Social perceptions: `{agent}/social/{other}`
- Frame evolves to include new perceptions dynamically

## Key Design Decisions

### 1. Two-Tier Architecture
- **Foundation**: Domain-agnostic primitives (passages, refs, hooks, derivations)
- **Cognitive**: Domain-specific layer built on foundation (frames, perceptions, cognition)

### 2. CognitiveFrame IS a Passage
Frames are passages pointed to by refs. This means:
- Versioned (content hash)
- Branchable (derivations)
- Queryable (search)
- No new tables needed

### 3. Perceptions ARE Refs
At the cognitive layer, we call them "perceptions" but they're just refs with naming conventions.
- All perceptions work identically via `increment_perception`
- Ref naming by convention: `{agent}/perception/{name}`, `{agent}/entity/{name}`, etc.
- Frame lists which perceptions exist (can be extended dynamically)

### 4. Frame-Scoped Search
Search is scoped by frame, not by passage_type. The frame defines what's "visible".

### 5. Optional Deduplication
When creating new perceptions (like entities), dedup can be enabled via an API flag. This is a feature, not a type distinction.

### 6. KP3 Owns Cognition
The fold operation lives in KP3. v2-runtime is a thin client.

## Files Summary

**Create in KP3 (Foundation APIs):**
- `kp3/src/kp3/api/refs.py` - HTTP endpoints for `/refs`
- `kp3/src/kp3/api/derivations.py` - HTTP endpoints for provenance

**Create in KP3 (Cognitive Tier):**
- `kp3/src/kp3/services/frames.py` - Frame operations
- `kp3/src/kp3/services/cognition.py` - The fold operation
- `kp3/src/kp3/services/perceptions.py` - Perception ops + dedup
- `kp3/src/kp3/api/frames.py` - HTTP endpoints for `/frames`
- `kp3/src/kp3/api/cognition.py` - HTTP endpoint for `/cognition/compute`

**Modify in KP3:**
- `kp3/src/kp3/services/search.py` - Add `frame_ref` parameter

**Modify in v2-runtime:**
- `src/kairix_agent/llm/block_manager.py` - Call KP3 cognition API
- Agent startup - resolve frame ref

**Create in v2-runtime:**
- `src/kairix_agent/worker/jobs/context_window.py` - Context check job
- `src/kairix_agent/worker/jobs/locks.py` - Redis lock helpers

**Existing (already works):**
- `kp3/src/kp3/services/refs.py` - Ref CRUD + hooks ✓
- `kp3/src/kp3/services/derivations.py` - Provenance ✓
- `kp3/src/kp3/hooks/letta_sync.py` - Letta projection ✓

## Verification

1. **Foundation tests**:
   - Refs API: CRUD, history, list by prefix
   - Derivations API: sources, derived

2. **Frame tests**:
   - Create frame passage with ref
   - Fork creates derived frame
   - Update perceptions creates new version

3. **Cognition tests**:
   - `compute()` creates passage + derivation + updates ref
   - Hooks fire if `frame.hooks_enabled`

4. **Perception dedup tests** (when `dedup=True`):
   - Similar content returns existing perception ref
   - New content creates new perception
   - Without dedup flag, always creates new

5. **Search with frame**:
   - `search(frame_ref=...)` returns only frame's perceptions
   - Admin search returns all passages

6. **End-to-end**:
   - Create agent with frame
   - Run cognition on perception
   - Verify passage created, ref updated, hook fired
   - Search scoped to frame perceptions

## Final Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     FOUNDATION TIER                                      │
│                                                                         │
│   Passages ←──────── Refs ─────────► Hooks                              │
│      ↑                 │                                                │
│      │                 │                                                │
│   Derivations ─────────┘                                                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                              ▲
                              │ built on
                              │
┌─────────────────────────────────────────────────────────────────────────┐
│                     COGNITIVE TIER                                       │
│                                                                         │
│   CognitiveFrame (is a Passage with Ref)                                │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │  corindel/frame/production → {                                  │  │
│   │    perceptions: [                                               │  │
│   │      {name: "persona", ref: "corindel/perception/persona"},     │  │
│   │      {name: "human", ref: "corindel/perception/human"},         │  │
│   │      ...                                                        │  │
│   │    ],                                                           │  │
│   │    cognition_config: { processes: {...} },                      │  │
│   │    hooks_enabled: true                                          │  │
│   │  }                                                              │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                              │                                          │
│                              ▼                                          │
│   Perceptions (are Refs - all work identically)                         │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │  corindel/perception/persona → Passage                          │  │
│   │  corindel/perception/human   → Passage                          │  │
│   │  corindel/entity/mark-lubin  → Passage                          │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│   Cognition: input + previous → new (fold operation)                    │
│   Search: scoped to frame's perceptions                                 │
└─────────────────────────────────────────────────────────────────────────┘
```
