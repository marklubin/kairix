⏺ Layered Progressive Summarization System

  Design Document v1.0

  ---
  1. Problem Statement

  Voice AI agents need persistent, evolving memory to maintain coherent identity
  across conversations. Current approaches have critical limitations:

  1. Context window exhaustion: Long conversations exceed token limits
  2. Latency impact: Real-time summarization blocks conversation flow
  3. Identity fragmentation: External LLM calls for reflection break persona
  coherence
  4. Flat memory: No hierarchical organization (sessions → days → topics)
  5. Stale context: Background info doesn't adapt to conversation shifts

  We need a memory system that:
  - Summarizes incrementally without blocking conversation
  - Maintains agent persona through self-authored reflections
  - Organizes memories hierarchically for efficient retrieval
  - Proactively surfaces relevant context before it's needed

  ---
  2. Motivating Use Case

  Kairix: A voice AI companion for job seekers

  ┌─────────────────────────────────────────────────────────────────┐
  │  Week 1: User discusses resume, target companies, anxiety       │
  │  Week 2: Mock interviews, feedback on communication style       │
  │  Week 3: Real interview prep for Google, salary negotiation     │
  │  Week 4: Post-interview debrief, next steps planning            │
  └─────────────────────────────────────────────────────────────────┘

  The agent must:
  - Remember specific companies discussed across sessions
  - Track emotional arc (anxiety → confidence)
  - Recall advice given to ensure consistency
  - Surface "you mentioned Google last week" without explicit retrieval
  - Evolve its own understanding of the relationship

  ---
  3. Executive Summary

  We build a three-layer progressive summarization system that:

  1. Captures conversation turns in real-time (zero latency impact)
  2. Summarizes via dedicated Reflector Agent after session ends
  3. Rolls up session summaries into daily/weekly/topic aggregates
  4. Injects relevant context into core memory proactively

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
  │   Triggers: SAQ job with session data                           │
  └──────────────────────────────┼──────────────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │                      SAQ BACKGROUND WORKER                      │
  │  ┌─────────────────────────────────────────────────────────┐   │
  │  │ summarize_session_job                                    │   │
  │  │   → Sends turns to Reflector Agent                       │   │
  │  │   → Reflector produces summary with consistent voice     │   │
  │  │   → Stores in Letta archival memory                      │   │
  │  └─────────────────────────────────────────────────────────┘   │
  │  ┌─────────────────────────────────────────────────────────┐   │
  │  │ update_background_context_job (CRON: every 5 min)        │   │
  │  │   → Searches archival for recent summaries               │   │
  │  │   → Updates core memory background_context block         │   │
  │  └─────────────────────────────────────────────────────────┘   │
  │  ┌─────────────────────────────────────────────────────────┐   │
  │  │ [PHASE 2] daily_rollup_job, weekly_rollup_job            │   │
  │  │ [PHASE 3] topic_cluster_job                              │   │
  │  └─────────────────────────────────────────────────────────┘   │
  └─────────────────────────────────────────────────────────────────┘

  Key insight: The Reflector Agent shares memory blocks with Primary Agent but has
  its own persona tuned for introspection. This maintains coherent identity while
  enabling specialized reflection.

  ---
  4. High-Level Design

  4.1 Multi-Agent Architecture

  ┌────────────────────────────────────────────────────────────────────────┐
  │                           LETTA SERVER                                 │
  │                                                                        │
  │  ┌─────────────────────┐          ┌─────────────────────┐             │
  │  │   PRIMARY AGENT     │          │   REFLECTOR AGENT   │             │
  │  │   (Kairix)          │          │   (Kairix-Reflector)│             │
  │  │                     │          │                     │             │
  │  │  Persona: Warm,     │          │  Persona: Same core │             │
  │  │  supportive coach   │◀────────▶│  identity, but      │             │
  │  │                     │  shared  │  introspective mode │             │
  │  │  Tools:             │  memory  │                     │             │
  │  │  - archival_search  │  blocks  │  Tools:             │             │
  │  │  - send_message     │          │  - archival_insert  │             │
  │  │                     │          │  - core_memory_edit │             │
  │  └──────────┬──────────┘          └──────────▲──────────┘             │
  │             │                                │                         │
  │             │ conversation                   │ cross-agent message     │
  │             ▼                                │ (via SAQ job)           │
  │  ┌─────────────────────┐          ┌──────────┴──────────┐             │
  │  │   CORE MEMORY       │          │   ARCHIVAL MEMORY   │             │
  │  │   (in-context)      │          │   (vector DB)       │             │
  │  │                     │          │                     │             │
  │  │  ┌───────────────┐  │          │  [SUMMARY:SESSION]  │             │
  │  │  │ persona       │  │          │  [SUMMARY:DAILY]    │             │
  │  │  │ human         │  │          │  [SUMMARY:TOPIC]    │             │
  │  │  │ self_perception│ │          │  [RAW passages...]  │             │
  │  │  │ relationship  │  │          │                     │             │
  │  │  │ background_ctx│◀─┼──────────│  (searchable)       │             │
  │  │  └───────────────┘  │  update  │                     │             │
  │  └─────────────────────┘          └─────────────────────┘             │
  └────────────────────────────────────────────────────────────────────────┘

  4.2 Core Memory Block Layout

  | Block              | Owner         | Purpose                     | Update
  Frequency  |
  |--------------------|---------------|-----------------------------|-------------
  ------|
  | persona            | Letta default | Who the agent IS            | Rarely (by
  agent) |
  | human              | Letta default | Who the user IS             | Agent-driven
        |
  | self_perception    | NEW           | Agent's evolving self-model | After
  reflection  |
  | relationship       | NEW           | Model of the relationship   | After
  reflection  |
  | background_context | NEW           | Recent/relevant summaries   | Watchdog (5
  min)  |

  4.3 Summary Type Hierarchy

                      ┌─────────────────────┐
                      │   TOPIC SUMMARIES   │  ← "All job search conversations"
                      │   (Phase 3)         │
                      └──────────┬──────────┘
                                 │ clusters by semantic similarity
                      ┌──────────┴──────────┐
                      │  WEEKLY SUMMARIES   │  ← "This week with Mark"
                      │  (Phase 2)          │
                      └──────────┬──────────┘
                                 │ aggregates by time
            ┌────────────────────┼────────────────────┐
            │                    │                    │
  ┌─────────┴─────────┐ ┌───────┴───────┐ ┌─────────┴─────────┐
  │ SESSION SUMMARY   │ │ SESSION SUMMARY│ │ SESSION SUMMARY   │
  │ Mon 9am           │ │ Mon 2pm        │ │ Tue 10am          │
  │ (Phase 1 - MVP)   │ │                │ │                   │
  └───────────────────┘ └────────────────┘ └───────────────────┘
            ▲                    ▲                    ▲
            │                    │                    │
      [turns...]           [turns...]           [turns...]

  ---
  5. Low-Level Design

  5.1 Module: memory/models.py

  Owner: Any engineer
  Dependencies: Pydantic, UUID, datetime

  from enum import Enum
  from uuid import UUID
  from datetime import datetime
  from pydantic import BaseModel

  class SummaryType(str, Enum):
      SESSION = "session"
      DAILY = "daily"
      WEEKLY = "weekly"
      TOPIC = "topic"

  class ConversationTurn(BaseModel):
      """Single exchange in a conversation."""
      user_message: str
      agent_response: str
      timestamp: datetime

  class ConversationSummary(BaseModel):
      """Stored in Letta archival memory."""
      summary_id: UUID
      summary_type: SummaryType
      agent_id: str
      period_start: datetime
      period_end: datetime
      summary_text: str
      topics: list[str]
      key_entities: list[str]
      source_summary_ids: list[UUID]  # For rollups
      turn_count: int
      created_at: datetime

      def to_archival_text(self) -> str:
          """Format for Letta archival storage with markers."""
          return f"""[SUMMARY:{self.summary_type.value.upper()}]
  Period: {self.period_start.isoformat()} to {self.period_end.isoformat()}
  Topics: {', '.join(self.topics)}
  Entities: {', '.join(self.key_entities)}
  Turns: {self.turn_count}

  {self.summary_text}
  [/SUMMARY:{self.summary_type.value.upper()}]"""

  class ActiveSession(BaseModel):
      """Tracks in-progress conversation."""
      session_id: UUID
      agent_id: str
      connection_id: str
      started_at: datetime
      last_activity: datetime
      turns: list[ConversationTurn]

      def is_expired(self, timeout_seconds: int = 300) -> bool:
          elapsed = (datetime.now(tz=timezone.utc) -
  self.last_activity).total_seconds()
          return elapsed >= timeout_seconds

  class BackgroundContext(BaseModel):
      """Rendered into core memory block."""
      last_updated: datetime
      recent_session_summary: str | None
      active_topics: list[str]
      persistent_context: list[str]

      def to_block_value(self, max_chars: int = 2000) -> str:
          lines = []
          if self.recent_session_summary:
              lines.append(f"Recent: {self.recent_session_summary}")
          if self.active_topics:
              lines.append(f"Active topics: {', '.join(self.active_topics)}")
          for ctx in self.persistent_context:
              lines.append(f"- {ctx}")
          result = "\n".join(lines)
          return result[:max_chars]

  5.2 Module: memory/session_tracker.py

  Owner: Backend engineer
  Dependencies: asyncio, models.py, SAQ queue

  from uuid import uuid4
  from datetime import datetime, timezone
  from typing import Callable
  import asyncio

  class SessionTracker:
      """Singleton tracking active voice sessions."""

      _instance: "SessionTracker | None" = None

      def __init__(self) -> None:
          self._sessions: dict[str, ActiveSession] = {}  # connection_id -> session
          self._timeout_seconds = 300  # 5 minutes
          self._on_session_end: Callable | None = None

      @classmethod
      def get_instance(cls) -> "SessionTracker":
          if cls._instance is None:
              cls._instance = cls()
          return cls._instance

      def set_session_end_callback(self, callback: Callable) -> None:
          """Register callback for session end (enqueues SAQ job)."""
          self._on_session_end = callback

      async def start_session(self, agent_id: str, connection_id: str) -> UUID:
          """Called when WebSocket connects."""
          session = ActiveSession(
              session_id=uuid4(),
              agent_id=agent_id,
              connection_id=connection_id,
              started_at=datetime.now(tz=timezone.utc),
              last_activity=datetime.now(tz=timezone.utc),
              turns=[],
          )
          self._sessions[connection_id] = session
          return session.session_id

      def record_turn(
          self, 
          connection_id: str, 
          user_message: str, 
          agent_response: str
      ) -> None:
          """Called after each completed exchange."""
          if connection_id not in self._sessions:
              return
          session = self._sessions[connection_id]
          session.turns.append(ConversationTurn(
              user_message=user_message,
              agent_response=agent_response,
              timestamp=datetime.now(tz=timezone.utc),
          ))
          session.last_activity = datetime.now(tz=timezone.utc)

      async def end_session(
          self, 
          connection_id: str, 
          reason: str = "disconnect"
      ) -> None:
          """Called on WebSocket disconnect or silence timeout."""
          if connection_id not in self._sessions:
              return
          session = self._sessions.pop(connection_id)
          if session.turns and self._on_session_end:
              await self._on_session_end(session, reason)

      async def check_timeouts(self) -> None:
          """Called periodically to detect silence timeouts."""
          now = datetime.now(tz=timezone.utc)
          expired = [
              cid for cid, session in self._sessions.items()
              if session.is_expired(self._timeout_seconds)
          ]
          for connection_id in expired:
              await self.end_session(connection_id, reason="silence_timeout")

  5.3 Module: memory/letta_memory.py

  Owner: Backend engineer
  Dependencies: letta-client, models.py

  from letta_client import AsyncLetta

  class LettaMemoryService:
      """Wrapper for Letta memory operations."""

      def __init__(self, client: AsyncLetta) -> None:
          self._client = client

      # ─────────────────────────────────────────────────────────────
      # Archival Memory Operations
      # ─────────────────────────────────────────────────────────────

      async def store_summary(
          self, 
          agent_id: str, 
          summary: ConversationSummary
      ) -> None:
          """Store summary in archival memory with structured markers."""
          await self._client.agents.archival_memory.create(
              agent_id=agent_id,
              text=summary.to_archival_text(),
          )

      async def search_summaries(
          self,
          agent_id: str,
          query: str,
          summary_type: SummaryType | None = None,
          limit: int = 10,
      ) -> list[str]:
          """Search archival memory, optionally filtering by type."""
          passages = await self._client.agents.passages.list(
              agent_id=agent_id,
              query_text=query,
              limit=limit * 2,  # Over-fetch to filter
          )
          results = []
          marker = f"[SUMMARY:{summary_type.value.upper()}]" if summary_type else
  "[SUMMARY:"
          for passage in passages:
              if marker in passage.text:
                  results.append(passage.text)
              if len(results) >= limit:
                  break
          return results

      async def get_recent_summaries(
          self,
          agent_id: str,
          summary_type: SummaryType,
          hours: int = 24,
      ) -> list[str]:
          """Get summaries from the last N hours."""
          # Use recency search with type filter
          return await self.search_summaries(
              agent_id=agent_id,
              query=f"recent {summary_type.value} summary",
              summary_type=summary_type,
              limit=20,
          )

      # ─────────────────────────────────────────────────────────────
      # Core Memory Operations
      # ─────────────────────────────────────────────────────────────

      async def ensure_block_exists(
          self,
          agent_id: str,
          label: str,
          initial_value: str = "",
      ) -> str:
          """Create block if missing, return block_id."""
          blocks = await self._client.agents.blocks.list(agent_id=agent_id)
          for block in blocks:
              if block.label == label:
                  return block.id
          # Create new block
          block = await self._client.blocks.create(
              label=label,
              value=initial_value,
          )
          await self._client.agents.blocks.attach(
              agent_id=agent_id,
              block_id=block.id,
          )
          return block.id

      async def update_block(
          self,
          agent_id: str,
          label: str,
          value: str,
      ) -> None:
          """Update core memory block value."""
          await self._client.agents.blocks.modify(
              agent_id=agent_id,
              block_label=label,
              value=value,
          )

      async def update_background_context(
          self,
          agent_id: str,
          context: BackgroundContext,
      ) -> None:
          """Update the background_context block."""
          await self.ensure_block_exists(agent_id, "background_context")
          await self.update_block(
              agent_id=agent_id,
              label="background_context",
              value=context.to_block_value(),
          )

  5.4 Module: worker/jobs.py (Extended)

  Owner: Backend engineer
  Dependencies: SAQ, letta-client, models.py

  from uuid import UUID
  from datetime import datetime, timezone
  from letta_client import AsyncLetta, MessageCreate

  # Existing heartbeat job...

  async def summarize_session_job(
      ctx: dict[str, object],
      *,
      session_id: str,
      agent_id: str,
      reflector_agent_id: str,
      started_at: str,
      ended_at: str,
      turns: list[dict[str, str]],
  ) -> dict[str, str]:
      """
      Triggered when session ends. Sends turns to Reflector Agent
      for summarization, stores result in archival memory.
      """
      client = AsyncLetta(base_url=os.getenv("LETTA_URL", "http://localhost:9000"))
      memory_service = LettaMemoryService(client)

      # Format turns for reflector
      turns_text = "\n".join([
          f"User: {t['user_message']}\nAgent: {t['agent_response']}"
          for t in turns
      ])

      # Send to Reflector Agent
      reflection_prompt = f"""Reflect on this conversation session and create a 
  summary.

  SESSION START: {started_at}
  SESSION END: {ended_at}

  CONVERSATION:
  {turns_text}

  Please provide:
  1. A 2-3 sentence summary capturing the essence of this conversation
  2. Key topics discussed (comma-separated)
  3. Important entities mentioned (people, companies, dates)
  4. Any notable emotional tone or relationship developments

  Respond naturally as yourself reflecting on this interaction."""

      response = await client.agents.messages.create(
          agent_id=reflector_agent_id,
          messages=[MessageCreate(role="user", content=reflection_prompt)],
      )

      # Parse response (Reflector should output structured reflection)
      reflection_text = response.messages[-1].content

      # Create summary object
      summary = ConversationSummary(
          summary_id=UUID(session_id),
          summary_type=SummaryType.SESSION,
          agent_id=agent_id,
          period_start=datetime.fromisoformat(started_at),
          period_end=datetime.fromisoformat(ended_at),
          summary_text=reflection_text,
          topics=extract_topics(reflection_text),  # Simple extraction
          key_entities=extract_entities(reflection_text),
          source_summary_ids=[],
          turn_count=len(turns),
          created_at=datetime.now(tz=timezone.utc),
      )

      # Store in archival
      await memory_service.store_summary(agent_id, summary)

      return {"status": "ok", "summary_id": str(summary.summary_id)}


  async def update_background_context_job(
      ctx: dict[str, object],
      *,
      agent_id: str,
  ) -> dict[str, str]:
      """
      CRON job (every 5 min). Updates background_context core memory
      block with recent relevant summaries.
      """
      client = AsyncLetta(base_url=os.getenv("LETTA_URL", "http://localhost:9000"))
      memory_service = LettaMemoryService(client)

      # Get recent session summaries
      recent = await memory_service.get_recent_summaries(
          agent_id=agent_id,
          summary_type=SummaryType.SESSION,
          hours=24,
      )

      # Build context
      context = BackgroundContext(
          last_updated=datetime.now(tz=timezone.utc),
          recent_session_summary=recent[0] if recent else None,
          active_topics=extract_all_topics(recent),
          persistent_context=[],
      )

      await memory_service.update_background_context(agent_id, context)

      return {"status": "ok", "topics": context.active_topics}

  5.5 Integration Points

  main.py - Session lifecycle hooks:

  @app.websocket("/voice")
  async def voice_endpoint(websocket: WebSocket):
      connection_id = str(uuid4())
      agent_id = os.getenv("LETTA_AGENT_ID")
      tracker = SessionTracker.get_instance()

      # Register SAQ job trigger
      async def on_session_end(session: ActiveSession, reason: str):
          await queue.enqueue(
              "summarize_session_job",
              session_id=str(session.session_id),
              agent_id=session.agent_id,
              reflector_agent_id=os.getenv("LETTA_REFLECTOR_AGENT_ID"),
              started_at=session.started_at.isoformat(),
              ended_at=datetime.now(tz=timezone.utc).isoformat(),
              turns=[t.model_dump() for t in session.turns],
          )

      tracker.set_session_end_callback(on_session_end)
      await tracker.start_session(agent_id, connection_id)

      try:
          # ... existing pipeline code ...
          pass
      finally:
          await tracker.end_session(connection_id, reason="disconnect")

  pipecat/letta_llm.py - Turn recording:

  async def process_frame(self, frame: Frame, direction: FrameDirection):
      # ... existing processing ...

      # After response completes, record turn
      if isinstance(frame, UserTurnMessageFrame):
          tracker = SessionTracker.get_instance()
          tracker.record_turn(
              connection_id=self._connection_id,
              user_message=frame.text,
              agent_response=self._last_response,
          )

  ---
  6. Trade-offs and Decision Rationale

  | Decision                        | Alternatives Considered           | Rationale
                                                                                  |
  |---------------------------------|-----------------------------------|----------
  --------------------------------------------------------------------------------|
  | Separate Reflector Agent        | Same agent with system message    | Cleaner
  separation; extensible for other sub-agents; dedicated persona for introspection
  |
  | SAQ over Celery                 | Celery, Dramatiq, RQ              | Already
  set up; lightweight; Redis-native; good enough for our scale
  |
  | 5-min silence timeout           | Message count, explicit "goodbye" | Balances
  session granularity vs over-fragmentation; matches natural conversation pauses  |
  | In-memory session tracker       | Redis, PostgreSQL                 | Sessions
  are ephemeral (<1hr); single-server for MVP; can add persistence later          |
  | Archival markers [SUMMARY:TYPE] | Separate collections, metadata    | Letta
  archival is single-store; markers enable filtering without schema changes
    |
  | Prompting over tool rules       | Letta tool rules for RAG          | Simpler;
  tool rules are new/experimental; prompting is debuggable                        |
  | Build vs Letta sleep-time       | Use Letta's experimental feature  |
  Sleep-time is undocumented/unstable; our needs are specific; full control
          |
  | Watchdog cron (5 min)           | Event-driven updates              | Decouples
   from session end; handles multi-session scenarios; simpler reasoning           |

  ---
  7. Implementation Roadmap

  Phase 1: MVP (Session Summarization + Watchdog)

  | Task                                           | Effort | Owner  | Dependencies
   |
  |------------------------------------------------|--------|--------|-------------
  -|
  | 1.1 Create memory/models.py                    | 2hr    | Junior | None
   |
  | 1.2 Implement SessionTracker                   | 4hr    | Mid    | models.py
   |
  | 1.3 Implement LettaMemoryService               | 4hr    | Mid    | Letta SDK
   |
  | 1.4 Create Reflector Agent in Letta            | 1hr    | Mid    | Letta UI/API
   |
  | 1.5 Implement summarize_session_job            | 4hr    | Mid    | 1.1-1.4
   |
  | 1.6 Implement update_background_context_job    | 3hr    | Mid    | 1.3
   |
  | 1.7 Integrate SessionTracker with main.py      | 2hr    | Mid    | 1.2
   |
  | 1.8 Integrate turn recording with letta_llm.py | 2hr    | Mid    | 1.2
   |
  | 1.9 End-to-end testing                         | 4hr    | Mid    | All above
   |

  Total Phase 1: ~26 hours (1 mid-level engineer, 1 week)

  Phase 2: Time-Based Rollups

  | Task                                       | Effort | Owner  | Dependencies |
  |--------------------------------------------|--------|--------|--------------|
  | 2.1 Design rollup cursor tracking          | 2hr    | Mid    | Phase 1      |
  | 2.2 Implement daily_rollup_job             | 4hr    | Mid    | 2.1          |
  | 2.3 Implement weekly_rollup_job            | 3hr    | Mid    | 2.2          |
  | 2.4 Update background_context with rollups | 2hr    | Junior | 2.2, 2.3     |
  | 2.5 Testing                                | 3hr    | Mid    | All above    |

  Total Phase 2: ~14 hours

  Phase 3: Topic Clustering

  | Task                                            | Effort | Owner | Dependencies
   |
  |-------------------------------------------------|--------|-------|-------------
  -|
  | 3.1 Research topic extraction approaches        | 4hr    | Mid   | None
   |
  | 3.2 Implement topic embedding/clustering        | 8hr    | Mid   | 3.1
   |
  | 3.3 Implement topic_cluster_job                 | 4hr    | Mid   | 3.2
   |
  | 3.4 Topic-aware retrieval in background_context | 4hr    | Mid   | 3.3
   |
  | 3.5 Testing                                     | 4hr    | Mid   | All above
   |

  Total Phase 3: ~24 hours

  Phase 4: Production Hardening

  | Task                            | Effort | Owner | Dependencies |
  |---------------------------------|--------|-------|--------------|
  | 4.1 Agent provisioning script   | 4hr    | Mid   | Phase 1      |
  | 4.2 Replay/re-derive capability | 8hr    | Mid   | Phase 1-3    |
  | 4.3 Monitoring/alerting         | 4hr    | Mid   | Phase 1      |
  | 4.4 Performance optimization    | 8hr    | Mid   | Phase 1-3    |

  ---
  8. Risks and Unknowns

  High Risk

  | Risk                             | Impact              | Mitigation
                           |
  |----------------------------------|---------------------|-----------------------
  -------------------------|
  | Letta API changes                | Breaks integration  | Pin SDK version; wrap
  in abstraction layer     |
  | Reflector response parsing fails | Corrupted summaries | Structured output
  format; fallback to raw text |
  | SAQ job failures                 | Lost summaries      | Dead letter queue;
  retry logic; session backup |

  Medium Risk

  | Risk                         | Impact                      | Mitigation
                          |
  |------------------------------|-----------------------------|-------------------
  ------------------------|
  | 5-min timeout too short/long | Poor session boundaries     | Make configurable;
   tune based on usage    |
  | Archival search quality      | Irrelevant context surfaced | Improve markers;
  consider hybrid search   |
  | Context block size limits    | Truncated background        | Prioritization
  logic; summarize summaries |

  Unknowns

  | Unknown                      | Impact              | Resolution Plan
                   |
  |------------------------------|---------------------|---------------------------
  -----------------|
  | Letta cross-agent latency    | May slow reflection | Benchmark; async
  fire-and-forget if needed |
  | Embedding quality for topics | Clustering accuracy | Prototype in Phase 3; may
  need fine-tuning |
  | Optimal cron frequency       | Freshness vs load   | Start 5 min; tune based on
   metrics         |

  ---
  9. FAQ

  Q: Why not use Letta's built-in context compaction?

  A: Letta's compaction is automatic and opaque. We need explicit control over what
   gets summarized, when, and how it's organized hierarchically. Our approach lets
  the agent author its own reflections, maintaining persona consistency.

  Q: Why a separate Reflector Agent instead of same-agent system messages?

  A: Three reasons: (1) Cleaner separation of concerns - Primary handles
  conversation, Reflector handles introspection. (2) Different system prompts
  optimized for each task. (3) Extensibility - future sub-agents for research,
  planning, etc. can follow the same pattern.

  Q: What happens if the user reconnects during the 5-min timeout?

  A: For MVP, we treat it as a new session. The previous session's summary will
  eventually be available in background_context. Phase 2 rollups heal this
  fragmentation by aggregating across sessions.

  Q: How does the agent know about the background_context block?

  A: We modify the Primary Agent's system prompt to explain: "Your
  background_context memory block contains recent conversation summaries that a
  background process updates. Use this for continuity. For older or unrelated
  topics, use archival_memory_search."

  Q: What if archival memory search is slow?

  A: The agent only searches archival on topic shifts (via prompting guidance).
  Most context comes from background_context block which is always in-context.
  Archival search is the fallback, not the primary path.

  Q: Can we replay conversations to rebuild agent memory?

  A: Yes (Phase 4). We store structured session data. Replay feeds turns to
  Reflector in sequence, rebuilding summaries and rollups. Useful for agent
  migration or recovery.

  Q: How do we prevent duplicate summaries?

  A: Session IDs are UUIDs tied to WebSocket connections. Each session produces
  exactly one summary. Rollup jobs track cursor position to avoid re-processing.

  Q: What's the latency impact on conversation?

  A: Zero. Session tracking is in-memory writes. SAQ jobs run asynchronously after
  session ends. Watchdog updates background_context between conversations. Voice
  pipeline never blocks on memory operations.

  ---
  Document version: 1.0
  Last updated: 2025-12-02
  Authors: Claude + Mark (collaborative design)
