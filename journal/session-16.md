# Session 16 - Date: 2025-12-02

## Goals
- [x] Design layered progressive summarization system
- [x] Research Letta memory APIs (archival, core memory, cross-agent)
- [x] Explore Kairix v1 implementation as reference
- [x] Design multi-agent architecture (Primary + Reflector)
- [x] Create comprehensive design document
- [ ] Begin implementation (deferred to next session)

## What We Covered
- **Letta Memory System**: Core memory (in-context blocks) vs Archival memory (vector DB)
- **Kairix v1 Reference**: Single-layer incremental summarization with embeddings
- **Multi-Agent Architecture**: Primary agent for conversation, Reflector agent for summarization
- **Progressive Summarization Hierarchy**: Session → Daily/Weekly → Topic clustering
- **Sleep-Time Agents**: Letta has experimental support, decided to build ourselves
- **Cross-Agent Messaging**: `send_message_to_agent_async` for fire-and-forget reflection

## Key Concepts Learned

1. **Letta Memory Architecture**
   - Core Memory: Always in-context, editable by agent, labeled blocks
   - Archival Memory: Vector DB, infinite capacity, searchable via embeddings
   - Memory Blocks: Can be shared across agents, have character limits

2. **Progressive Summarization Layers**
   ```
   Layer 3: Topic Summaries (semantic clustering)
        ↑
   Layer 2: Weekly/Daily Rollups (time-based aggregation)
        ↑
   Layer 1: Session Summaries (MVP - after silence timeout)
        ↑
   Raw Turns: Captured in real-time, zero latency impact
   ```

3. **Multi-Agent Pattern**
   - Primary Agent (Kairix): Handles real-time conversation
   - Reflector Agent (Kairix-Reflector): Handles introspection/summarization
   - Shared memory blocks for continuity
   - Cross-agent messaging via SAQ jobs (async, no latency impact)

4. **Core Memory Block Layout**
   | Block | Purpose |
   |-------|---------|
   | persona | Who the agent IS (Letta default) |
   | human | Who the user IS (Letta default) |
   | self_perception | Agent's evolving self-model (NEW) |
   | relationship | Agent's model of the relationship (NEW) |
   | background_context | Recent summaries from watchdog (NEW) |

5. **Session Detection**
   - 5-minute silence timeout OR WebSocket disconnect
   - Triggers SAQ job with session turns
   - Session fragmentation healed at rollup layers

6. **Real-Time RAG via Prompting**
   - Agent already has `archival_memory_search` tool
   - Solve via system prompt: "use archival search on topic shifts"
   - No need to build separate topic detection infrastructure

7. **Why Build vs Use Letta Sleep-Time**
   - Sleep-time agents are experimental/undocumented
   - Triggers every N steps, not on session end
   - Our needs are specific (silence timeout, cross-agent reflection)
   - Full control over the summarization process

## Architecture Designed

```
┌─────────────────────────────────────────────────────────────────┐
│                     REAL-TIME VOICE PIPELINE                    │
│   STT ──▶ Aggregator ──▶ Letta Agent ──▶ TTS                   │
│                              │                                  │
│                    Records turns to tracker                     │
└──────────────────────────────┼──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SESSION TRACKER (In-Memory)                  │
│   Detects: 5-min silence OR WebSocket disconnect                │
└──────────────────────────────┼──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SAQ BACKGROUND WORKER                      │
│  - summarize_session_job → Reflector Agent → Archival           │
│  - update_background_context_job (CRON 5 min) → Core Memory     │
│  - [Phase 2] daily_rollup_job, weekly_rollup_job                │
│  - [Phase 3] topic_cluster_job                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Design Decisions & Rationale

| Decision | Why |
|----------|-----|
| Separate Reflector Agent | Cleaner separation; extensible; dedicated introspection persona |
| SAQ over Celery | Already set up; lightweight; Redis-native |
| 5-min silence timeout | Balances granularity vs over-fragmentation |
| In-memory session tracker | Sessions ephemeral; single-server MVP |
| Archival markers `[SUMMARY:TYPE]` | Enables filtering without schema changes |
| Prompting over tool rules | Simpler; tool rules experimental; debuggable |
| Build own sleep-time | Letta's is unstable; our needs are specific |

## Files Planned (Not Yet Created)

```
src/agent_server/memory/
├── __init__.py
├── models.py           # ConversationSummary, ActiveSession, etc.
├── session_tracker.py  # In-memory session management
├── letta_memory.py     # Archival/core memory operations
└── summarizer.py       # Triggers reflector agent
```

## Insights & Aha Moments

- **"Use Letta agent for summaries, not Claude directly"**: Maintains coherent identity; agent authors its own reflections
- **"Async everything"**: Principal tenet - never impact conversational latency
- **"Solve via prompting first"**: Letta already has tool use; don't over-engineer
- **"Session fragmentation heals at rollup"**: Don't need perfect session detection; time-based aggregation catches gaps
- **"Separate agents = extension point"**: Future sub-agents (research, planning) can follow same pattern

## Challenges & Solutions

- **Challenge**: How to maintain agent identity during reflection
- **Solution**: Separate Reflector Agent with same core persona but introspection-tuned system prompt

- **Challenge**: Real-time RAG for topic shifts
- **Solution**: Agent's built-in archival_memory_search + prompting guidance; no new infrastructure

- **Challenge**: Letta sleep-time agents experimental
- **Solution**: Build ourselves; trigger via SAQ on session end instead of N-step intervals

- **Challenge**: Context block size limits
- **Solution**: BackgroundContext model with prioritization logic and max_chars truncation

## Implementation Roadmap

**Phase 1 (MVP)**: Session summarization + watchdog (~26 hours)
- models.py, SessionTracker, LettaMemoryService
- summarize_session_job, update_background_context_job
- Integration with main.py and letta_llm.py

**Phase 2**: Time-based rollups (~14 hours)
- daily_rollup_job, weekly_rollup_job
- Cursor tracking for aggregation

**Phase 3**: Topic clustering (~24 hours)
- Topic extraction/embedding
- Semantic clustering across time

**Phase 4**: Production hardening
- Agent provisioning script
- Replay/re-derive capability
- Monitoring/alerting

## Next Steps
- [ ] Create `memory/` module structure
- [ ] Implement data models (models.py)
- [ ] Implement SessionTracker
- [ ] Implement LettaMemoryService
- [ ] Create Reflector Agent in Letta
- [ ] Implement summarize_session_job
- [ ] Wire up to main.py

## Questions/Blockers
- Need to create Reflector Agent in Letta (can do via UI for now)
- Letta cross-agent latency unknown (benchmark during implementation)
- Topic clustering approach TBD in Phase 3

## Session Victory

**Comprehensive design complete!** Designed full progressive summarization system:
- Multi-agent architecture (Primary + Reflector)
- Three-layer summarization hierarchy
- Core memory block layout for agent self-model
- Zero-latency-impact async processing via SAQ
- Clear implementation roadmap

Ready to start building next session!
