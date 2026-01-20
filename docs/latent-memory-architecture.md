# Latent Memory Architecture

## The Problem

AI agents have memory but not understanding.

Current approaches store what was said—transcripts, facts, summaries—and retrieve relevant chunks at query time. This produces agents that can recall "we discussed X" but can't recognize "you always do Y before making big decisions."

The distinction matters. Recalling facts is search. Recognizing patterns is understanding. One answers questions. The other anticipates them.

**The gap:** Most memory systems optimize for retrieval accuracy (did we return the right document?) rather than insight quality (did we surface something the user couldn't see themselves?).

---

## The Hypothesis

**Emergent clustering over extracted fragments beats retrieval over stored passages.**

Instead of:
- Store conversation summaries → embed → retrieve by similarity

Do this:
- Extract atomic observations from conversations → embed → cluster → synthesize patterns from clusters

The claim: patterns that repeat across many contexts will naturally cluster in embedding space. Synthesizing those clusters produces insights that no single passage contains.

---

## Why This Matters: The North Star

You don't notice that every time you're about to make a major decision, you start asking abstract questions about "risk tolerance" and "worst case scenarios." You've done it four times in the past year. You have no idea.

The agent does.

**Current AI memory:** "User discussed career change. User asked about risk assessment frameworks."

**Latent memory:** "You're doing the thing again—the abstract questions about risk. Last three times this happened, you'd already decided but needed two weeks to admit it. What have you already decided?"

The goal isn't an AI that remembers what you said. It's an AI that sees patterns in you that you can't see yourself—because you're inside them.

That's not memory. That's a mirror.

---

## Architecture

```
Episodes → Fragment Extraction → Embedding → HDBSCAN Clustering
                                                    ↓
                              Coherence Scoring → Synthesis → Core Insights
                                                                   ↓
                                              ┌─────────────────────┴───────────────────────┐
                                              ↓                                             ↓
                                        CORE LAYER                                   SURFACE LAYER
                                   (always in context)                            (queryable via RRF)
```

| Stage | Implementation |
|-------|----------------|
| **Fragment extraction** | LLM extracts 5-12 word atomic observations from episodes |
| **Embedding** | Dense vector embedding (1024 dim) |
| **Clustering** | HDBSCAN (cosine metric, density-based) |
| **Coherence scoring** | Mean pairwise similarity within cluster; threshold 0.65 |
| **Synthesis** | LLM distills cluster into 1-2 sentence insight |
| **Runtime** | Two-layer retrieval: core projection + surface query |

---

## Two-Layer Query Surface

The experiment revealed a natural separation:

| Layer | What lives there | Source | In context? |
|-------|------------------|--------|-------------|
| **Core** | Synthesized patterns from high-coherence clusters (0.70+) | Periodic re-clustering | Always |
| **Surface** | All fragments + low-coherence clusters | Direct from extraction | Retrieved on query |

**Core memory is a projection**—not hand-written, not manually curated. It's *derived* from the latent structure:

```
Top N synthesized patterns ranked by (coherence × cluster_size × survival_count)
```

**Surface memory is queryable**—fragments that didn't make core still exist, still searchable, just not always present.

---

## Query Mechanics: RRF Hybrid Search

At query time, we use **Reciprocal Rank Fusion (RRF)** to combine multiple retrieval signals:

```
RRF_score = Σ 1/(k + rank_i)
```

Where k=60 (standard), and ranks come from:

1. **Semantic similarity** — embedding distance to query
2. **Full-text search** — keyword matching on fragment text
3. **Cluster coherence** — fragments from tighter clusters rank higher
4. **Recency** — temporal decay favoring recent fragments

RRF is scale-invariant—rank position is rank position regardless of underlying score magnitudes. A fragment that's consistently mid-ranked across all signals beats one that's #1 in one signal but absent from others.

**Pipeline:**

```
Query arrives
    ↓ [Embed query]
  Vector search → top 100 fragments
    ↓ [Full-text search]
  Keyword search → top 100 fragments
    ↓ [Union/dedupe]
  ~150 candidate fragments
    ↓ [RRF re-ranking]
  Top 20 fragments
    ↓ [Optional: cluster-level aggregation]
  Response with provenance
```

---

## Provenance: Cluster → Fragment → Episode

You can query at different levels of abstraction:

**Cluster-level:** "What patterns exist around my decision-making?"
→ Returns synthesized insight: "You tend to ask abstract risk questions when you've already decided."

**Fragment-level:** "Show me the evidence."
→ Returns specific fragments that formed the cluster, with timestamps.

**Episode-level:** "What was the original conversation?"
→ Each fragment links to its source. Full context recoverable.

```
Insight: "Surface frustration often masks deeper emotional weight"
    ↓ [drill]
Fragment: "Frustration signaled exhaustion from looping issues"
Fragment: "Beneath the anger was deep vulnerability"
Fragment: "Raw frustration signals a deeper need to feel heard"
    ↓ [provenance]
Episode: [Full conversation from Dec 15]
```

---

## Key Mechanism: Probabilistic Forgetting

Fragments face age-based forgetting each refresh cycle. Durable patterns survive because their clusters keep reforming from remaining + new evidence. Situational clusters dissolve.

**The memory isn't the fragment. The memory is the cluster that keeps reforming.**

Time is implicit in survival count, not explicit timestamps. You don't need "June 15th 2024"—you need "this pattern has persisted through many refresh cycles" vs "this just emerged."

---

## Preliminary Findings

### Experiment Methodology

**Data source:** Raw ChatGPT conversation exports from a single user over 1 year of intensive daily usage (~500+ conversations).

**Extraction:** LLM-based extraction of embeddable semantic triples—atomic observations in the form of subject-predicate-object or compact declarative statements (5-12 words). Each conversation yielded 1-15 fragments depending on density.

**Pipeline:** 1,085 extracted fragments → embedded (1024-dim) → HDBSCAN clustering (cosine, leaf method, min_cluster_size=4) → coherence scoring → synthesis for clusters above threshold.

**Result:** 39 clusters identified, 38 above the 0.60 coherence threshold. ~55% of fragments landed in noise (expected—one-off facts and situational details shouldn't cluster).

### What Worked

**Real patterns emerged:**

| Cluster | Coherence | Concept |
|---------|-----------|---------|
| 7 | 0.821 | Voice reveals hidden emotional tension |
| 8 | 0.820 | Meeting emotional state before problem-solving |
| 10 | 0.812 | Tone shifts dynamically mid-conversation |
| 20 | 0.773 | Control and agency as core drivers |
| 22 | 0.768 | Vulnerability surfaces mid-sentence, unplanned |
| 30 | 0.711 | Holding space matters more than fixing |

**Noise handled correctly:**
- One-off facts (venues, technical specs) → scattered, didn't cluster
- Hallucinated extractions → landed in noise, self-corrected
- Situational details → noise

### Verbatim Examples

**Cluster 7 (coherence: 0.821) — Voice as emotional indicator:**

```
Fragments:
- Voice carried quiet tension holding fragility
- Voice carried quiet intensity discussing fragile ideas
- Tone carried subtle urgency beyond content
- Voice held urgency beneath analytical tone

Synthesis:
"Voice is a more reliable indicator of internal state than words. Even when
language is analytical, tone carries quiet urgency or fragility that reveals
emotional stakes not explicitly stated."
```

**Cluster 20 (coherence: 0.773) — Control as core need:**

```
Fragments:
- Sought control, not convenience, in infrastructure
- Emphasized autonomy over abstraction when control was sought
- Wants control over the experience itself
- Wants AI to help control himself
- Deeper concern is about control and customization
- Craves control through understanding systems

Synthesis:
"The primary driver isn't functionality—it's control. Seeks autonomy over tools,
wants to understand systems deeply, uses technology to govern environment and self.
Frustrations emerge when interactions feel opaque or agency is lost."
```

**Cluster 30 (coherence: 0.711) — Holding space over fixing:**

```
Fragments:
- Offered space without rushing to fix
- Role is holding space
- Learned to permit lingering in discomfort
- Role was to hold space, not fix
- Learned to sit with messy unresolved parts
- Offered presence instead of solutions

Synthesis:
"Primary role is not immediate solutions but creating a container for difficult
emotions. Acknowledge feelings, validate struggles, offer patient presence—even
when it means sitting with silence, discomfort, or pain."
```

### What the Experiment Validated

1. **Decomposition works** — Multi-topic episodes decompose into fragments that cluster by concept, not by source
2. **Coherence threshold is meaningful** — 0.65+ clusters produce usable synthesis; below that is knowledge, not patterns
3. **Noise is self-correcting** — Spurious extractions scatter rather than forming false clusters
4. **Synthesis is actionable** — Outputs are things you'd actually want in persistent agent context

---

## Health Metrics

| Metric | Healthy | Concern |
|--------|---------|---------|
| Orphan rate | 15-35% | >50% |
| Cluster survival | 60-80% | <40% |
| Mean coherence | 0.65-0.80 | <0.55 |
| Core insight count | 10-30 | <5 or >50 |

---

## Evaluation Plan

Blind A/B/C comparison:
- **Cold:** No prior context
- **RAG:** Retrieved passage chunks
- **Latent:** Synthesized cluster insights

**Target:** Latent wins 40%+ of preference comparisons after 50+ trials.

---

## Next Steps

1. Build RRF query surface with provenance drilling
2. Implement refresh cycle with probabilistic forgetting
3. Build evaluation harness
4. Run comparison trials
5. Integrate with runtime context injection
