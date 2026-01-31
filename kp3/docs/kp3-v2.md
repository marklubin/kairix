# KP3 v2: Concept Graph Architecture

## Problem with Current Approach

The current world model uses 3 fixed blocks (human/persona/world) with monolithic fold operations. This leads to:

1. **Over-extraction**: Model treats every mention as important (GPU, tripod, parking)
2. **Size pressure**: 5000 char limit forces aggressive pruning
3. **Loss of signal**: Important concepts get pruned alongside noise
4. **No natural salience**: Can't distinguish "mentioned once" from "core to identity"

Human/Persona blocks work better because they're **narrative/interpretive**, not **enumerative**. WorldBlock fails because it tries to maintain exhaustive lists.

## Proposed: Concept Graph Model

Instead of fixed blocks, maintain a **graph of concepts** where each concept has its own fold semantics.

### Flow

```
Passage arrives
    ↓
Extract concepts mentioned (lightweight extraction)
    ↓
For each concept:
    ├── Exists? → Retrieve previous understanding
    │             Fold(old_understanding, new_occurrence) → new_understanding
    │             Update edges to related concepts
    │
    └── New? → Create node with initial understanding
               Discover edges to existing concepts
    ↓
Blocks are VIEWS projected from the graph (for agent consumption)
```

### Why This Works

1. **Natural salience through repetition**
   - "Kairix" appears 47 times → rich, evolved understanding
   - "GPU" appears once → thin node, naturally low importance
   - No need to decide importance upfront - it emerges

2. **Concept-level versioning**
   - Each concept has its own history
   - Can trace how understanding of any concept evolved
   - Individual folds are small, focused, cheap

3. **Emergence over prescription**
   - No upfront categories (project vs entity vs theme)
   - Structure emerges from connections
   - "Kairix" might be a project AND a theme AND connected to "voice AI"

4. **No size limits on the model**
   - Each concept is a small unit
   - Graph grows but nodes stay focused
   - Pruning = letting nodes decay naturally when not referenced

5. **Relationships as first-class**
   - "Mark" ←connected_to→ "Kairix" ←involves→ "Pipecat"
   - Topology tells you what matters
   - Can answer: "What's in Mark's orbit right now?"

6. **Blocks become projections**
   ```
   HumanBlock = project(graph, anchor="Mark", filter=personal_attributes)
   WorldBlock = project(graph, anchor="external_entities", filter=active)
   PersonaBlock = project(graph, anchor="relationship", filter=self_model)
   ```
   The graph is truth; blocks are compressed views for the agent.

### Data Model

```sql
concepts:
  id UUID PRIMARY KEY
  canonical_name TEXT           -- normalized identifier
  embedding VECTOR              -- for similarity matching
  current_understanding TEXT    -- latest synthesized understanding
  first_seen TIMESTAMP
  last_seen TIMESTAMP
  occurrence_count INT
  version INT

concept_history:
  id UUID PRIMARY KEY
  concept_id UUID REFERENCES concepts
  version INT
  understanding TEXT
  passage_id UUID REFERENCES passages
  created_at TIMESTAMP

relationships:
  source_id UUID REFERENCES concepts
  target_id UUID REFERENCES concepts
  relationship_type TEXT        -- "involves", "connected_to", "part_of", etc.
  strength FLOAT                -- based on co-occurrence
  last_seen TIMESTAMP
```

### Key Challenges

1. **Concept identity/matching**
   - How do you know "the Kairix project" = "kairix" = "Kairix voice AI"?
   - Embedding similarity + LLM-assisted merge step
   - Canonical key normalization (we have this in shadow tables already)

2. **Extraction granularity**
   - What counts as a "concept"?
   - Need lightweight first-pass extraction

3. **Projection logic**
   - How to compress graph into fixed-size blocks?
   - Which concepts make the cut?
   - How to synthesize narrative from graph structure?

### Relationship to Current System

The shadow tables (`world_model_projects`, `world_model_entities`, `world_model_themes`) with `occurrence_count` and `last_occurrence` are **halfway there**. Missing:

- Unified concept identity (not 3 separate typed tables)
- Relationships between concepts
- Individual fold per concept
- Projection logic to blocks

### Implementation Path

1. Design unified `concepts` table with proper identity
2. Build concept extraction step (lightweight, before fold)
3. Build per-concept fold operation
4. Build relationship discovery/update
5. Build projection step (graph → blocks)
6. Migrate existing shadow table data

### Core Insight

> "We do more computation offline, but we do it better."

The current system tries to do extraction + synthesis + pruning in one monolithic step. The graph model separates concerns:

- **Extraction**: What concepts appeared? (cheap, can be aggressive)
- **Folding**: How does this change understanding of each concept? (per-concept, focused)
- **Projection**: What fits in the agent's context? (separate compression step)

This matches how memory actually works - concepts strengthen with repetition, connections form through co-occurrence, and recall is a projection/compression of the full graph.
