# Plan: Session Tracking System & Duplicate Summary Cleanup

## Problem Summary

The Letta `messages.reset()` API only clears `message_ids` on the agent but does NOT delete messages from the database. When querying `/messages/`, all historical messages are still returned. This caused:

1. Session boundary detection to repeatedly find the same "completed" session
2. Summarization job to run every minute on the same 28 messages
3. ~50+ duplicate summaries created, burning Opus API credits

## Solution Overview

Create a proper session tracking system in our PostgreSQL database to:
- Track which sessions have been processed
- Prevent re-summarization of already-processed sessions
- Associate message IDs with sessions for validation

---

## Part 1: Database Schema Changes

### New Table: `sessions`

```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(64) NOT NULL,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    message_count INTEGER NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',  -- pending, summarized, failed
    summary_passage_id VARCHAR(128),  -- Letta passage ID once summarized
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    summarized_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX ix_sessions_agent_id ON sessions(agent_id);
CREATE INDEX ix_sessions_status ON sessions(status);
CREATE UNIQUE INDEX ix_sessions_agent_period ON sessions(agent_id, period_start, period_end);
```

### New Table: `session_messages` (Join Table)

```sql
CREATE TABLE session_messages (
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    message_id VARCHAR(128) NOT NULL,  -- Letta message ID
    PRIMARY KEY (session_id, message_id)
);

CREATE INDEX ix_session_messages_message_id ON session_messages(message_id);
```

### Files to Create/Modify

1. **New migration**: `alembic/versions/xxxx_create_sessions_tables.py`
2. **New model**: `src/kairix_agent/sessions/models.py`
3. **New service**: `src/kairix_agent/sessions/service.py`

---

## Part 2: Session Boundary Detection Changes

### File: `src/kairix_agent/worker/jobs/session_boundary.py`

**Current Flow:**
1. Fetch messages from Letta
2. Check if gap >= SESSION_GAP_MINUTES
3. If yes → emit event + enqueue summarization

**New Flow:**
1. Fetch messages from Letta
2. Check if gap >= SESSION_GAP_MINUTES
3. If gap < threshold → session still active, skip
4. **NEW: Query `session_messages` to check message associations**
   - Extract all message IDs from current batch
   - Query: `SELECT DISTINCT session_id FROM session_messages WHERE message_id IN (:ids)`
5. **Decision Logic:**
   - **All unassociated** (0 rows): Create new session entry → emit event → enqueue summarization
   - **All associated with ONE session**: Already processed → skip silently
   - **Partial association OR multiple sessions**: Raise error (inconsistent state)
6. When creating session entry:
   - Insert into `sessions` table with status='pending'
   - Insert all message_ids into `session_messages`
   - Pass `session_id` to summarize job

### Pseudocode

```python
async def _check_agent_session(agent_config, queue, letta_url):
    # ... existing message fetching ...

    if gap < SESSION_GAP_MINUTES:
        # Session still active
        return

    message_ids = [m.id for m in conversation_messages]

    # Check for existing associations
    async with db_session() as session:
        existing = await session.execute(
            select(SessionMessage.session_id)
            .where(SessionMessage.message_id.in_(message_ids))
            .distinct()
        )
        associated_sessions = existing.scalars().all()

    if len(associated_sessions) == 0:
        # All new - create session and proceed
        new_session = await create_session(
            agent_id=agent_config.agent_id,
            message_ids=message_ids,
            period_start=first_message.date,
            period_end=last_message.date,
        )
        await queue.enqueue("summarize_session", session_id=new_session.id, ...)

    elif len(associated_sessions) == 1:
        # Already processed - check status
        existing_session = await get_session(associated_sessions[0])
        if existing_session.status == 'pending':
            # Summarization in progress or failed - could retry
            logger.info(f"Session {existing_session.id} already pending")
        else:
            logger.debug(f"Session {existing_session.id} already summarized")
        return

    else:
        # Inconsistent state - some messages in multiple sessions
        raise SessionIntegrityError(
            f"Messages span {len(associated_sessions)} sessions: {associated_sessions}"
        )
```

---

## Part 3: Summarization Job Changes

### File: `src/kairix_agent/worker/jobs/summarize.py`

**Changes:**
1. Accept `session_id` parameter instead of raw `message_ids`
2. Load session from DB to get message_ids
3. On success: Update session status to 'summarized', record passage_id
4. On failure: Update session status to 'failed', record error_message
5. **Keep Letta message reset** for context window management (defense in depth)

```python
async def summarize_session(
    _ctx: Context,
    *,
    session_id: str,  # NEW: Session ID instead of message_ids
    agent_id: str,
    letta_url: str,
    archive_id: str,
    reflector_agent_id: str | None,
) -> dict[str, object]:

    # Load session from our DB
    session = await get_session(session_id)
    message_ids = await get_session_message_ids(session_id)

    try:
        # ... existing summarization logic ...

        # On success: update session
        await update_session(
            session_id=session_id,
            status='summarized',
            summary_passage_id=passage.id,
            summarized_at=datetime.now(UTC),
        )

    except Exception as e:
        await update_session(
            session_id=session_id,
            status='failed',
            error_message=str(e),
        )
        raise
```

---

## Part 4: Duplicate Summary Cleanup

### One-time cleanup script: `scripts/cleanup_duplicate_summaries.py`

```python
async def cleanup_duplicate_summaries(agent_id: str, archive_id: str, dry_run: bool = True):
    """
    Find and delete duplicate session summaries from Letta archival memory.

    Strategy:
    1. List all passages with "[Session Summary:" prefix
    2. Group by (period_start, period_end) from the text
    3. For each group with >1 passage:
       - Keep the oldest (by created_at)
       - Delete the rest
    """
    client = AsyncLetta(base_url=LETTA_BASE_URL)

    # Search for all session summaries
    passages = await client.passages.search(
        archive_id=archive_id,
        query="Session Summary",
        limit=500,
    )

    # Group by period
    by_period = defaultdict(list)
    for p in passages:
        # Parse period from text: "[Session Summary: {start} to {end}]"
        match = re.match(r'\[Session Summary: (.+) to (.+)\]', p.text)
        if match:
            period_key = (match.group(1), match.group(2))
            by_period[period_key].append(p)

    # Find duplicates
    to_delete = []
    for period, passages in by_period.items():
        if len(passages) > 1:
            # Sort by created_at, keep oldest
            sorted_passages = sorted(passages, key=lambda p: p.created_at)
            to_delete.extend(sorted_passages[1:])  # All but the first

    print(f"Found {len(to_delete)} duplicate summaries to delete")

    if dry_run:
        for p in to_delete:
            print(f"  Would delete: {p.id} - {p.text[:80]}...")
        return

    # Delete duplicates
    for p in to_delete:
        await client.archives.passages.delete(
            archive_id=archive_id,
            passage_id=p.id,
        )
        print(f"  Deleted: {p.id}")
```

### Usage

```bash
# Dry run first
uv run python scripts/cleanup_duplicate_summaries.py --agent-id agent-56a10649-... --dry-run

# Actually delete
uv run python scripts/cleanup_duplicate_summaries.py --agent-id agent-56a10649-...
```

---

## Part 5: Implementation Order

### Phase 1: Database & Models
1. Create Alembic migration for `sessions` and `session_messages` tables
2. Create SQLAlchemy models in `src/kairix_agent/sessions/models.py`
3. Create session service in `src/kairix_agent/sessions/service.py`

### Phase 2: Session Boundary Changes
4. Modify `session_boundary.py` to use session tracking
5. Add message association check before emitting boundary event
6. Pass session_id to summarize job

### Phase 3: Summarization Changes
7. Modify `summarize.py` to use session_id parameter
8. Update session status on success/failure
9. Keep Letta message reset call for context window management (defense in depth)

### Phase 4: Cleanup
10. Create cleanup script for duplicate summaries
11. Run cleanup on salinas
12. Verify archival memory is clean

### Phase 5: Deploy & Test
13. Run migration on salinas
14. Deploy updated worker
15. Monitor for correct behavior

---

## Files to Modify

| File | Changes |
|------|---------|
| `alembic/versions/xxxx_create_sessions.py` | NEW: Migration |
| `src/kairix_agent/sessions/__init__.py` | NEW: Package |
| `src/kairix_agent/sessions/models.py` | NEW: Session, SessionMessage models |
| `src/kairix_agent/sessions/service.py` | NEW: CRUD operations |
| `src/kairix_agent/worker/jobs/session_boundary.py` | Add session tracking |
| `src/kairix_agent/worker/jobs/summarize.py` | Use session_id, update status |
| `scripts/cleanup_duplicate_summaries.py` | NEW: Cleanup script |

---

## Design Decisions

1. **Message reset**: Keep calling Letta `messages.reset()` for context window management, but don't rely on it for deduplication - our session tracking is the source of truth
2. **Retry logic**: No automatic retry - mark failed sessions as 'failed' and require manual intervention
3. **Cleanup**: After deleting duplicates, update both:
   - The kept archival memory passage with a note about this incident
   - The `last_session_summary` memory block with the canonical summary + incident context

---

## Part 6: Incident Documentation for Agent

As part of cleanup, we'll add context about this incident so the agent (Corindel) understands what happened:

### Update to Kept Summary Passage

Append to the oldest (kept) summary:
```
---
[System Note: Dec 18, 2025]
Due to a Letta API behavior change where message reset only clears message_ids
but doesn't delete messages from the database, this session was re-summarized
~50 times before being caught. Duplicate summaries have been cleaned up.
A session tracking system has been implemented to prevent recurrence.
```

### Update to `last_session_summary` Block

Replace with canonical summary + note:
```
[Session: {period_start} to {period_end}]

{canonical_summary_text}

---
[System Note: This session experienced a summarization loop due to Letta API
behavior. ~50 duplicate summaries were created and cleaned up on Dec 18, 2025.
Session tracking now prevents recurrence.]
```
