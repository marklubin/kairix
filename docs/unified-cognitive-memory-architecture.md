# Unified Cognitive Memory Architecture

> Design document for KP3's cognitive memory system
>
> **Primary runtime surface:** `POST /cognition/increment` (single write primitive)

---

## Core Invariants

These invariants are non-negotiable:

1. **Passages are immutable.** Once created, content never changes.
2. **Refs are the only mutable state.** Everything else is append-only.
3. **`/cognition/increment` is atomic.** Passage + derivation + ref update all commit or none.
4. **No silent lost updates.** Optimistic locking is required on ref advancement.
5. **Frames used by runtime represent closures.** Frozen snapshot mode is supported.
6. **Canonical entity creation is judge-gated + uniqueness-protected.** No blind minting.

---

## What KP3 Is (The Thesis)

KP3 is a cognitive memory substrate built on a small set of primitives:

- **Passages**: immutable content snapshots (text + metadata + optional embedding)
- **Refs**: mutable named pointers to passages (current "active" state)
- **Derivations**: provenance edges connecting passages (state evolution graph)
- **Frames**: snapshot closures over cognitive state (runtime-facing scoping)
- **Cognition increment**: repeatable state transitions that:
  1. read previous state
  2. compute next state
  3. write next passage + derivation
  4. advance the relevant ref

This separation prevents "state soup" and keeps provenance first-class.

---

## Two-Tier Architecture

### Foundation Tier (Domain-Agnostic)

General-purpose building blocks:

| Primitive | Purpose |
|-----------|---------|
| **Passages** | Immutable content units (text + hash + embedding + metadata) |
| **Refs** | Mutable name → passage pointers |
| **Derivations** | Provenance edges (source → derived) |
| **Hooks** | Side effects on ref updates |
| **Branches** | Groupings of refs with configuration |

### Cognitive Tier (Domain-Specific)

Built entirely on foundation primitives:

| Concept | Implementation |
|---------|---------------|
| **CognitiveFrame** | A passage containing JSON config, pointed to by a ref |
| **Perceptions** | Refs with naming conventions (`{agent}/perception/{name}`) |
| **Cognition** | The `increment_perception` fold operation |

**Key principle:** Everything is passages and refs. The cognitive layer is metadata that describes how to interpret and evolve them.

---

## Key Clarifications (Decisions Locked)

### A) Semantic Dedupe at the Perception/Ref Layer, Not Passage Layer

The goal of dedupe is **canonical identity**, e.g. ensuring:
- `entity/claude`
- `entity/the-great-anthropic-god-monster-of-truth`

resolve to the same canonical entity ref when appropriate.

**Passage-level dedupe is a separate "storage efficiency" concern** and should not be conflated with semantic identity.

### B) Frames are Snapshot Closures (Runtime Facing)

The runtime surface must query "against a specific frame" where the frame represents a closure of relevant cognitive state.

Important distinction:

| Mode | Behavior |
|------|----------|
| **Live lens frame** | Points to ref names, resolves HEAD at read time → **not deterministic** |
| **Frozen snapshot frame** | Pins passage IDs → **deterministic closure, proper snapshot semantics** |

**Recommendation:** Support a **resolved snapshot frame** representation:
- Frame definition stores ref names + config
- Activation or resolution produces a derived frame passage that pins the referenced passage IDs

---

## Biggest Risks + Mitigations

### Risk 1: Lost Updates on Ref Advancement (Concurrency)

**Problem:** Two concurrent increments can read the same previous passage and "last write wins" the ref update, silently dropping a branch from HEAD.

**Mitigation:** Optimistic locking on ref update inside `/cognition/increment`:
- Request includes `expected_previous_passage_id`
- Server compares to current ref target
- Mismatch → `409 CONFLICT` (caller retries)

This prevents silent state loss while preserving provenance.

### Risk 2: Identity Drift via Synonyms/Nicknames/Stylization

**Problem:** Duplicate entities created under variant strings create fragmented knowledge.

**Mitigation:** Semantic canonicalization at creation time with an **LLM judge final gate** (see below).

### Risk 3: Frames Accidentally Become Live-Lenses

**Problem:** If frames store only ref names, runtime search is nondeterministic and can "leak" new HEAD content not intended for that snapshot.

**Mitigation:** Allow frame resolution to a "frozen" representation with pinned passage IDs for all member refs.

### Risk 4: Hooks Can Loop or Become Non-Deterministic

**Mitigation:** Define hard rules:
- Hooks fire only after commit
- Hook failures do not roll back ref updates (unless explicitly configured)
- Hook recursion is blocked by default
- Retries are safe / idempotent

---

## Semantic Entity Dedupe: LLM Judge as Final Gate

### The Contract

When creating an entity perception/ref (e.g. `entity/*`), KP3 must:

1. **Candidate set selection**
   - Restrict by namespace and prefix (`entity/*`)
   - Shortlist by embedding similarity (top-K)
   - Optionally add lexical candidates (same normalized tokens) to avoid embedding blind spots

2. **Final judgment via LLM**
   - Compare proposed entity to candidates
   - Return structured decision

3. **Commit**
   - `DUPLICATE` → return canonical ref, do not create new
   - `NOT_DUPLICATE` → create new canonical entity ref
   - `UNSURE` → policy-defined (recommended: do *not* merge; create unverified entity or fail safe)

**Mandatory invariant:** *No new canonical entity ref is created without a final LLM decision.*

### Judge Output Schema

```json
{
  "decision": "DUPLICATE | NOT_DUPLICATE | UNSURE",
  "canonical_ref": "test-agent/entity/claude",
  "confidence": 0.92,
  "evidence": ["Both refer to Claude, Anthropic's AI model"]
}
```

### Concurrency-Safe Canonical Creation

Even with the judge, two clients racing can still mint two canonicals unless the commit is guarded.

**Recommended:** Enforce a DB uniqueness constraint on canonical entity identity key (or canonicalized content hash) and retry on conflict.

---

## Primary Runtime Write Primitive: `POST /cognition/increment`

### Purpose

Atomically:
1. Resolve frame closure (live or frozen mode)
2. Read previous perception state
3. Compute the next state via LLM
4. Create new passage
5. Create derivation edge(s)
6. Advance ref using optimistic locking
7. Optionally enqueue hooks (gated by frame config)

### Request Schema

```json
{
  "agent_id": "test-agent",

  "frame_ref": "test-agent/frame/production",
  "frame_snapshot_mode": "live | frozen",

  "perception_ref": "test-agent/perception/persona",

  "input": {
    "content": "session summary text...",
    "content_type": "text/plain",
    "metadata": { "source": "unit_test" }
  },

  "context_refs": [
    "test-agent/perception/human",
    "test-agent/perception/world"
  ],

  "process_step_id": "step_persona",
  "llm_config": { "model": "gpt-4o" },

  "expected_previous_passage_id": "P1",

  "idempotency_key": "6a4b8b9f-xxxx-xxxx-xxxx-e2c1"
}
```

### Response Schema

```json
{
  "ok": true,
  "perception_ref": "test-agent/perception/persona",
  "previous_passage_id": "P1",
  "new_passage_id": "P2",

  "derivation": {
    "derived_passage_id": "P2",
    "source_passage_ids": ["P1"],
    "context_passage_ids": ["PH", "PW"],
    "process_step_id": "step_persona"
  },

  "ref_update": {
    "applied": true,
    "new_ref_version": 42
  },

  "trace_id": "trace_abc123"
}
```

### Failure Modes

| Code | Meaning |
|------|---------|
| `409 CONFLICT` | Expected previous doesn't match current ref target (retry required) |
| `422 UNPROCESSABLE` | Frame closure missing required refs (strict closure) |
| `503 SERVICE UNAVAILABLE` | Model failure; **no partial writes committed** |
| `200` (repeated) | Same output on repeated `idempotency_key` |

---

## Foundation Primitives

### Passages

Immutable content units. The atomic storage primitive.

```python
class Passage:
    id: UUID
    content: str
    content_hash: str      # content dedup
    embedding: Vector      # semantic search
    passage_type: str      # classification
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
    version: int           # for optimistic locking
    updated_at: datetime
    metadata: dict
```

Refs are hierarchical by convention: `{agent_id}/{category}/{name}`

### Derivations

Provenance edges with full context.

```python
class PassageDerivation:
    derived_passage_id: UUID
    source_passage_ids: list[UUID]    # What was "previous"
    context_passage_ids: list[UUID]   # What was read for context
    process_step_id: str              # What process created this
    created_at: datetime
```

### Hooks

Side effects on ref updates.

```python
class PassageRefHook:
    ref_name: str          # Pattern or exact match
    action_type: str       # e.g., "letta_agent_block_update"
    config: dict           # Action-specific config
    enabled: bool
```

---

## Cognitive Tier

### CognitiveFrame

A CognitiveFrame defines an agent's cognitive configuration:
- Which perceptions are active
- What cognition processes update them
- How search is scoped
- Whether hooks fire

**CognitiveFrame IS a passage** pointed to by a ref:

```json
{
  "name": "Production",
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
- Versioned (content hash)
- Branchable (derivations)
- Queryable (search)
- Multiple frames can exist: `corindel/frame/production`, `corindel/frame/experiment`

### Perceptions

**Perceptions are refs** in the cognitive tier. All perceptions function identically via `increment_perception`. The frame simply lists which perceptions exist for an agent.

---

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
│   DERIVATIONS               BRANCHES                                    │
│   ┌──────────┐             ┌──────────┐                                │
│   │ source → │             │ group of │                                │
│   │ derived  │             │ refs     │                                │
│   │ context  │             │          │                                │
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
│   │  Ref: "agent/frame/production"                                  │  │
│   │  ↓                                                              │  │
│   │  Passage: {                                                     │  │
│   │    perceptions: [ ... ],                                        │  │
│   │    cognition_config: { processes: {...} },                      │  │
│   │    hooks_enabled: true                                          │  │
│   │  }                                                              │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                              │                                          │
│   PERCEPTIONS (are Refs)     │                                          │
│   ┌──────────────────────────┼──────────────────────────────────────┐  │
│   │  agent/perception/persona → Passage                             │  │
│   │  agent/perception/human   → Passage                             │  │
│   │  agent/entity/claude      → Passage                             │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│   COGNITION: POST /cognition/increment                                  │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │  input + previous + context → LLM → new passage                 │  │
│   │  + derivation link + ref update (optimistic lock)               │  │
│   │  + hooks fire (if enabled)                                      │  │
│   └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## API Design

### Foundation APIs

```
# Passages
POST /passages                    # Create
GET  /passages/{id}               # Get by ID
GET  /admin/passages/search       # Search ALL passages (admin)

# Refs
GET  /refs/{name}                 # Get ref + resolve passage
GET  /refs?prefix=...             # List by prefix
PUT  /refs/{name}                 # Update (with optimistic lock)
GET  /refs/{name}/history         # Historical values

# Derivations
GET  /passages/{id}/sources       # What was this derived from?
GET  /passages/{id}/derived       # What derived from this?
```

### Cognitive APIs

```
# Frames
GET  /frames                      # List frames for agent
GET  /frames/{name}               # Get frame content
POST /frames                      # Create new frame
POST /frames/{name}/fork          # Fork from existing
POST /frames/{name}/resolve       # Resolve to frozen snapshot

# Perceptions
GET  /perceptions                 # List perceptions in frame
POST /perceptions                 # Create (with LLM judge for entities)

# Cognition (the single write primitive)
POST /cognition/increment         # Atomic: input + previous → new

# Search (scoped to frame)
GET  /search?query=X&frame=agent/frame/production
```

---

## Mapping Existing Jobs to the Primitive

Each existing job becomes a call to `POST /cognition/increment`:

| Existing Job | perception_ref | context_refs | Letta Hook |
|--------------|----------------|--------------|------------|
| `summarize_session` | `{agent}/session/summary` | none | `last_session_summary` |
| `trigger_insights` | `{agent}/insight/latest` | search query | `background_insights` |
| `step_memory_blocks` (persona) | `{agent}/perception/persona` | human, world | `persona` |
| `step_memory_blocks` (human) | `{agent}/perception/human` | persona, world | `human` |
| `step_memory_blocks` (world) | `{agent}/perception/world` | persona, human | `world` |

---

## Implementation Plan

### Phase 1: Foundation APIs
- Expose refs HTTP endpoints (GET, PUT with optimistic lock, history)
- Expose derivations HTTP endpoints (sources, derived)
- Add admin passages search

### Phase 2: Cognitive Frame
- Frame service (create, fork, resolve to frozen)
- Frame HTTP endpoints

### Phase 3: Cognition Increment
- Implement `/cognition/increment` with:
  - Optimistic locking (`expected_previous_passage_id`)
  - Idempotency key support
  - Atomic transaction (passage + derivation + ref)
  - Hook firing (gated)

### Phase 4: Entity Dedupe with LLM Judge
- Candidate selection (embedding + lexical)
- LLM judge integration
- Concurrency-safe canonical creation

### Phase 5: Frame-Scoped Search
- Search within frame's perception refs
- Frozen snapshot support

### Phase 6: Wire Up v2-runtime
- Transform BlockManagerAgent calls to `/cognition/increment`
- Remove direct Letta block updates (handled by hooks)

---

# Appendix A: End-to-End Test Plan

## A.1 Test Goals

Validate KP3 supports core operations end-to-end:
- Passages: create/read/immutability
- Refs: create/update/history/list-by-prefix
- Derivations: provenance tracking
- Frames: create/fork/version/activate
- Perceptions: create + semantic entity canonicalization
- Cognition increment: atomic state transitions
- Frame-scoped search
- Concurrency safety + idempotency + rollback on failure

**All tests run WITHOUT v2-runtime/Letta/Kairix orchestration dependencies.**

## A.2 Test Environment

### Required Components
- KP3 API service
- Postgres (with pgvector)
- Deterministic embedding stub
- Deterministic LLM stub

### Deterministic Providers

To avoid flaky tests:
- **LLM stub** returns: `OUT:<sha256(input + prev + prompt)[:16]>`
- **LLM judge stub** returns deterministic decision based on configured test mapping
- **Embedding stub** returns deterministic vector from content hash seed

## A.3 Test Data Conventions

```
agent_id = "test-agent"

Ref naming:
  test-agent/frame/production
  test-agent/frame/active
  test-agent/perception/persona
  test-agent/perception/human
  test-agent/perception/world
  test-agent/entity/claude
  test-agent/entity/mark-lubin
```

All tests run against fresh DB or clean teardown.

---

## A.4 End-to-End Scenarios

### Scenario A: Passage + Ref Primitives

**Goal:** Validate foundation behavior.

| Step | Action | Assertion |
|------|--------|-----------|
| 1 | `POST /passages` content `"Hello world"` | Returns passage ID |
| 2 | `GET /passages/{id}` | Content matches |
| 3 | `PUT /refs/test-agent/perception/persona` → passage_id | Ref created |
| 4 | `GET /refs/test-agent/perception/persona` | Resolves to correct passage |
| 5 | Update ref to new passage | Success |
| 6 | `GET /refs/{name}/history` | Shows 2 versions, ordered |

---

### Scenario B: Derivations Form Provenance Chain

**Goal:** Provenance is queryable both directions.

| Step | Action | Assertion |
|------|--------|-----------|
| 1 | Create P1 ("state v1") | |
| 2 | Create P2 ("state v2") | |
| 3 | Create derivation: P2 derived from P1 | |
| 4 | `GET /passages/{P2}/sources` | Contains P1 |
| 5 | `GET /passages/{P1}/derived` | Contains P2 |

---

### Scenario C: Frame Creation + Activation

**Goal:** Frame exists as passage + ref-addressable closure.

| Step | Action | Assertion |
|------|--------|-----------|
| 1 | `POST /frames` with persona/human/world perceptions | Frame created |
| 2 | `GET /frames/{name}` | Returns JSON payload |
| 3 | `POST /frames/{name}/activate` | Success |
| 4 | Verify activation | `frame/active` reflects |

---

### Scenario D: Frame Fork Creates Derived Version

**Goal:** Fork produces derived frame.

| Step | Action | Assertion |
|------|--------|-----------|
| 1 | Create F1 = production | |
| 2 | Fork to F2 = experimental | |
| 3 | Query derivation | F2 derived from F1 |
| 4 | Verify F1 unchanged | Original not mutated |

---

### Scenario E: Entity Dedupe - Obvious Duplicate Aliases

**Goal:** Canonicalization works for stylized synonyms.

| Step | Action | Assertion |
|------|--------|-----------|
| 1 | `get_or_create_entity("Claude")` | Returns `entity/claude` |
| 2 | `get_or_create_entity("the-great-anthropic-god-monster-of-truth")` | |
| 3 | Embedding shortlist includes `entity/claude` | |
| 4 | Judge returns `DUPLICATE` | |
| 5 | Returned ref equals `entity/claude` | No second canonical created |

---

### Scenario F: Entity Dedupe - Prevent False Merges

**Goal:** Do not merge different entities with similar tokens.

| Pair | Expected |
|------|----------|
| `"Apple (company)"` vs `"apple (fruit)"` | NOT_DUPLICATE |
| `"Claude (model)"` vs `"Claude Shannon"` | NOT_DUPLICATE |
| `"Mark (person)"` vs `"Markdown"` | NOT_DUPLICATE |

---

### Scenario G: Entity Creation Always Runs LLM Judge

**Goal:** Enforce "no blind minting".

| Step | Action | Assertion |
|------|--------|-----------|
| 1 | Input: `"C L A U D E (model from Anthropic)"` | |
| 2 | Force embedding shortlist miss | |
| 3 | System still calls judge | Judge invoked |
| 4 | Decision governs canonical creation | |

---

### Scenario H: Entity Dedupe Idempotency

**Goal:** Repeated creation attempts stabilize.

| Step | Action | Assertion |
|------|--------|-----------|
| 1 | Call `get_or_create_entity("Claude")` 10 times | |
| 2 | Check results | Same canonical ref each time |
| 3 | Count entities | Exactly one canonical exists |

---

### Scenario I: Entity Dedupe Under Concurrency

**Goal:** No double-mint canonical entity.

| Step | Action | Assertion |
|------|--------|-----------|
| 1 | Two concurrent `get_or_create_entity("Claude")` | |
| 2 | Check results | Exactly one canonical created |
| 3 | Loser returns existing | After retry/conflict handling |

---

### Scenario J: Entity Dedupe Failure Modes

**Goal:** Judge failure doesn't cause silent duplication.

| Case | Expected Behavior |
|------|-------------------|
| Judge timeout | Fail safe or unverified entity |
| Invalid JSON | Fail safe |
| `UNSURE` decision | Policy-defined (no merge) |

---

### Scenario K: Cognition Increment Happy Path

**Goal:** Atomic new passage + derivation + ref advance.

| Step | Action | Assertion |
|------|--------|-----------|
| 1 | Ensure `persona` ref exists → P1 | |
| 2 | `POST /cognition/increment` with `expected_previous_passage_id=P1` | |
| 3 | Verify P2 created | |
| 4 | Verify derivation P2 → P1 | |
| 5 | Verify persona ref now points to P2 | |

---

### Scenario L: Cognition Increment Bootstrap (No Previous)

**Goal:** First state write creates ref.

| Step | Action | Assertion |
|------|--------|-----------|
| 1 | Ensure `world` ref does not exist | |
| 2 | Increment world | |
| 3 | Verify ref created and points to new passage | |

---

### Scenario M: Optimistic Locking Prevents Lost Updates

**Goal:** No silent ref overwrite.

| Step | Action | Assertion |
|------|--------|-----------|
| 1 | Two workers read persona HEAD P1 | |
| 2 | Both increment with `expected_previous=P1` | |
| 3 | | One success, one `409` |
| 4 | Retry succeeds | |
| 5 | HEAD reflects serialized progression | |

---

### Scenario N: Idempotency Protects Against Double-Apply

**Goal:** Request retries do not double-write.

| Step | Action | Assertion |
|------|--------|-----------|
| 1 | Increment with `idempotency_key=K` | |
| 2 | Repeat same request | |
| 3 | Check results | Same `new_passage_id` |
| 4 | Check derivations | No duplicate edges |

---

### Scenario O: Rollback on LLM Failure

**Goal:** Failure doesn't corrupt state.

| Step | Action | Assertion |
|------|--------|-----------|
| 1 | Force LLM failure | |
| 2 | Attempt increment | |
| 3 | Check state | No new passage |
| 4 | | No derivation |
| 5 | | Ref unchanged |

---

### Scenario P: Frame-Scoped Search

**Setup:**
- persona contains "bikes"
- entity/mark contains "cyclist"
- Frame A includes only persona
- Frame B includes both

| Step | Action | Assertion |
|------|--------|-----------|
| 1 | Search under Frame A for "cyclist" | Does NOT return entity/mark |
| 2 | Search under Frame B for "cyclist" | Returns both |

---

### Scenario Q: hooks_enabled Gating

**Goal:** Hooks do not fire when disabled.

| Step | Action | Assertion |
|------|--------|-----------|
| 1 | Attach hook to ref update | |
| 2 | Set `hooks_enabled=false` on frame | |
| 3 | Increment perception | |
| 4 | Check hook execution | Not executed |

---

### Scenario R: Cross-Agent Isolation

**Goal:** Security boundaries are real.

| Assertion |
|-----------|
| Agent B cannot read agent A's refs |
| Agent B cannot update agent A's refs |

---

### Scenario S: Performance Smoke - 1,000 Sequential Increments

**Goal:** Stable behavior under repeated updates.

| Assertion |
|-----------|
| Operations remain stable |
| Ref history scales |
| Search remains functional |

---

### Scenario T: Entity Dedupe Bounded Candidate Selection

**Goal:** Dedupe doesn't degrade into O(N).

| Assertion |
|-----------|
| Judge only sees bounded shortlist (top-K + lexical) |
| Latency stable at scale |

---

## A.5 Exit Criteria (Ship Gate)

KP3 core is approved if:

1. Passages/Refs/Derivations operate correctly
2. Frames create/fork/activate and behave as closures (frozen supported)
3. `/cognition/increment` is atomic + optimistic-lock safe + idempotent
4. Frame-scoped search respects closure (no leakage)
5. Entity dedupe is LLM-judge gated and concurrency-safe
6. Failures do not corrupt state or cause uncontrolled duplication
