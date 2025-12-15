# Kairix

A voice-first AI agent with persistent memory across conversations.

Kairix explores what it takes for an AI to develop genuine understanding over time — reflecting on past interactions, building a model of who you are, inferring goals from behavior, and evolving through feedback.

## Structure

```
kairix/
├── v0-apiana/          # Early iteration
├── v1-cognitive/       # Custom cognitive engine (~22K lines)
├── v2-runtime/         # Current: Pipecat + Letta
├── kp3/                # Passage processing pipeline
├── kairix-app/         # KMP mobile companion
├── experiments/        # Side explorations
├── docs/               # Architecture documentation
└── ops/                # Deployment tooling
```

## Evolution

### v0: Apiana (`/v0-apiana`)

Initial exploration with Gradio interfaces and conversation persistence experiments. Established the core questions but confirmed that bolting memory onto an LLM isn't enough.

### v1: Custom Cognitive Engine (`/v1-cognitive`)

Built a complete agent infrastructure from scratch to understand the problem space deeply.

**kairix-core** — The cognitive foundation:
- Hierarchical memory with semantic graph storage
- Perceptor system for incremental reflection and insight generation  
- Persona management (conversational and notebook modes)
- Embedding pipeline (Nomic)
- Environment tracking and context awareness

**kairix-offline** — Background processing:
- ChatGPT conversation importer (load years of history)
- Multi-agent fact extraction (world facts, user profile, assistant cognition)
- Semantic graph construction from extracted facts
- Summary synthesis pipeline

**kairix-apps** — Application layer:
- FastAPI server with MCP integration
- Model and prompt management
- Telemetry

**kairix-website** — Web client:
- TypeScript/React/Vite
- Voice UI with push-to-talk and continuous modes
- Real-time conversation display

**Voice interface**: ElevenLabs Conversational AI agent with Twilio webhook binding for phone calls. Manual configuration (no code in repo) — worked well but tightly coupled to their platform.

v1 taught me what mattered. It also taught me I was rebuilding infrastructure that mature platforms were starting to provide.

### v2: Pipecat + Letta (`/v2-runtime`)

Rebuilt on established infrastructure as those platforms matured:

- **Pipecat** — Voice pipeline (Deepgram STT, ElevenLabs TTS, VAD, WebSocket streaming)
- **Letta** — Hierarchical memory with archival/core memory blocks, agent orchestration
- **PostgreSQL** — Replaced SQLite for production persistence
- **SAQ workers** — Background jobs for session summarization, insights generation

**Current capabilities**:
- Real-time voice conversations with natural turn-taking
- Session boundary detection (silence timeout, disconnect)
- Background summarization via dedicated Reflector agent
- Layered memory (session → daily → topic summaries)
- Core memory blocks for persona, relationship model, background context

### Kairix App (`/kairix-app`)

Kotlin Multiplatform mobile app (iOS target). Voice interface for phone conversations. Live streams the agent's background and offline thinking — you can watch reflection happen in real-time.

### Experiments (`/experiments`)

Side explorations that informed the main work:
- **claudetopia** — Decision simulation, Claude utility experiments
- **perceptor-inspector** — Tooling for inspecting agent cognitive state
- **self_bootstrapping_agent** — Agent self-modification experiments

## Roadmap

### Rebuild from v1
- **Conversation import** — ChatGPT importer to bootstrap memory from years of history
- **Semantic graph** — Knowledge graph as auxiliary data store for richer entity relationships
- **Entity extraction pipeline** — Multi-agent fact extraction (world facts, user profile, assistant cognition)

### Memory & Reflection
- **Hierarchical summarization** — Time-based rollups (session → daily → weekly → topic)
- **Topic clustering** — Identify conversation themes, generate cross-conversation summaries
- **V1 reflection backfill** — Import experiential foundation from v1 archives

### Processing Pipeline (`/kp3`)
General-purpose infrastructure for tracking text passages through multi-step processing pipelines with full provenance.

**Core concepts:**
- **Passages** — Immutable text content at any granularity (conversation, day summary, week summary, etc.)
- **Derivation chains** — Track how passages derive from other passages (many-to-one consolidation)
- **Processing runs** — Configure and execute jobs that query subsets and produce new passages
- **Tagging** — Flexible tagging system for filtering and organization
- **Full provenance** — Always trace back to source material

**Implementation:**
- SQLAlchemy models with PostgreSQL + pgvector
- Alembic migrations for schema management
- Service layer for passages, derivations, and processing runs
- Processors for LLM-based transformations and embedding generation
- Importer for v1 Kairix memory shards (SQLite → kp3)
- CLI for running imports and embedding jobs

This powers the hierarchical summarization system but is designed as reusable infrastructure.

### Environmental Context
- **Location intelligence** — Semantic context from GPS ("at coffee shop for 20 min", "commuting on BART")
- **Environmental awareness** — Weather, time, mood tracking over time
- **Passive signal awareness** — Interruptions, engagement patterns, backchannels as implicit feedback

### Contextual Personalization Engine (CPE)
Real-time learning system using contextual bandits (Vowpal Wabbit) to personalize responses based on user state.

The insight: user state vector serves dual purpose — INPUT (what's user's state now?) and FEEDBACK (how did state change after response? Δstate = learning signal).

Voice provides richer implicit signals than text: hesitation, interruption, pace, tone. Training data nobody else is capturing.

Phases: state vector definition → response feature schema → instrumentation → reward function → VW integration → steering injection → confidence-weighted application → observability dashboard

### Latency & Response
- **Tiered LLM responses** — Preemptive lightweight response for perceived speed, then full model response
- **Active feedback tracking** — Traditional thumbs up/down alongside passive signals

### Longer-term: Agent Desktop
The single-agent architecture is scaffolding for something bigger: an agent desktop environment.

- **LiveKit room as desktop** — Persistent environment where agents live
- **Concierge agent as launcher** — Personal context + intent recognition + routing (like macOS Spotlight)
- **Specialist agents as applications** — Calendar, research, code, health — each with deep domain expertise
- **Multi-agent awareness** — Agents perceive each other, collaborate, hand off
- **Voice as shell** — Never break out of the interface

*"The room is like an environment. Like the desktop environment equivalent. And then you can call up different individual agents where they have specialization... they're like individual applications."*

The background processing infrastructure being built now is the foundation. You can't have autonomous specialist agents without agents that can think independently.

## Core Ideas

**Memory is not RAG.** Most "memory-enabled" agents bolt on retrieval. That's search, not memory. Real memory is layered (working/episodic/semantic), experiential (the agent lived through it), personal (model of you specifically), and active (reflection happens in the background, not at query time).

**Voice changes the interaction model.** Voice as primary interface — always-on, contextually aware, zero-latency — is fundamentally different from chat. The UX patterns, latency requirements, and turn-taking dynamics are distinct problems.

**Background processing is the unlock.** Agents that think when you're not talking to them behave fundamentally differently. They can reflect, consolidate, prepare context. The conversation becomes a window into ongoing cognition, not a cold start.

## Tech Stack

- Python (vast majority of codebase)
- Kotlin Multiplatform (iOS app)
- Pipecat, Letta
- PostgreSQL + pgvector
- Deepgram, ElevenLabs
- Anthropic, OpenAI

## Contact

Mark Lubin  
[GitHub](https://github.com/marklubin) · [LinkedIn](https://linkedin.com/in/marklubin)
