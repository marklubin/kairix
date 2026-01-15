"""Cognition increment service - the primary runtime write primitive.

This service implements the atomic cognition increment operation:
1. Resolve frame closure (live or frozen mode)
2. Read previous perception state
3. Compute next state via LLM
4. Create new passage
5. Create derivation edge(s)
6. Advance ref using optimistic locking
7. Optionally fire hooks (gated by frame config)
"""

import hashlib
import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from kp3.db.models import Passage
from kp3.services.derivations import create_derivations
from kp3.services.frames import get_frame_by_ref, get_ref_version
from kp3.services.passages import create_passage
from kp3.services.refs import get_ref, get_ref_passage, set_ref

logger = logging.getLogger(__name__)


# In-memory idempotency cache (would use Redis in production)
_idempotency_cache: dict[str, dict[str, Any]] = {}


class CognitionConflictError(Exception):
    """Raised when optimistic locking fails due to concurrent modification."""

    def __init__(
        self,
        ref_name: str,
        expected_passage_id: UUID,
        actual_passage_id: UUID,
    ) -> None:
        self.ref_name = ref_name
        self.expected_passage_id = expected_passage_id
        self.actual_passage_id = actual_passage_id
        super().__init__(
            f"Conflict on ref '{ref_name}': expected passage {expected_passage_id}, "
            f"but current is {actual_passage_id}"
        )


class CognitionFrameError(Exception):
    """Raised when frame resolution fails."""

    def __init__(self, message: str, missing_refs: list[str] | None = None) -> None:
        self.missing_refs = missing_refs or []
        super().__init__(message)


async def increment_perception(
    session: AsyncSession,
    *,
    agent_id: str,
    frame_ref: str,
    frame_snapshot_mode: str = "live",
    perception_ref: str,
    input_content: str,
    input_content_type: str = "text/plain",
    input_metadata: dict[str, Any] | None = None,
    context_refs: list[str] | None = None,
    process_step_id: str,
    llm_config: dict[str, Any] | None = None,
    expected_previous_passage_id: UUID | None = None,
    idempotency_key: str | None = None,
    llm_stub: bool = False,
) -> dict[str, Any]:
    """Execute an atomic cognition increment.

    This is the primary write primitive for cognitive state transitions.

    Args:
        session: Database session
        agent_id: Agent ID
        frame_ref: Ref to the cognitive frame
        frame_snapshot_mode: 'live' or 'frozen'
        perception_ref: Ref to the perception being updated
        input_content: New input content to process
        input_content_type: MIME type of input
        input_metadata: Optional metadata for input
        context_refs: Additional refs to include as context
        process_step_id: ID of the cognition process step
        llm_config: Optional LLM configuration overrides
        expected_previous_passage_id: For optimistic locking
        idempotency_key: For deduplication
        llm_stub: If True, use deterministic stub instead of real LLM

    Returns:
        Result dict with new passage ID, derivation info, etc.

    Raises:
        CognitionConflictError: If optimistic lock fails (409)
        CognitionFrameError: If frame resolution fails (422)
    """
    # Check idempotency cache
    if idempotency_key and idempotency_key in _idempotency_cache:
        logger.info("Returning cached result for idempotency key: %s", idempotency_key)
        return _idempotency_cache[idempotency_key]

    # 1. Resolve frame
    frame = await get_frame_by_ref(session, frame_ref)
    if not frame:
        raise CognitionFrameError(f"Frame not found: {frame_ref}")

    # 2. Get previous perception state
    previous_passage_id = await get_ref(session, perception_ref)
    previous_passage: Passage | None = None
    previous_content = ""

    if previous_passage_id:
        previous_passage = await session.get(Passage, previous_passage_id)
        if previous_passage:
            previous_content = previous_passage.content

    # 3. Optimistic locking check
    if expected_previous_passage_id is not None:
        if previous_passage_id != expected_previous_passage_id:
            raise CognitionConflictError(
                ref_name=perception_ref,
                expected_passage_id=expected_previous_passage_id,
                actual_passage_id=previous_passage_id,  # type: ignore
            )

    # 4. Resolve context refs
    context_passage_ids: list[UUID] = []
    context_contents: list[str] = []

    for ctx_ref in context_refs or []:
        ctx_passage = await get_ref_passage(session, ctx_ref)
        if ctx_passage:
            context_passage_ids.append(ctx_passage.id)
            context_contents.append(ctx_passage.content)

    # 5. Compute next state via LLM (or stub)
    if llm_stub:
        # Deterministic stub: OUT:<sha256(input + prev + prompt)[:16]>
        hash_input = f"{input_content}{previous_content}{process_step_id}"
        content_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
        new_content = f"OUT:{content_hash}"
    else:
        # Real LLM call would go here
        # For now, use a simple template
        new_content = await _compute_next_state(
            input_content=input_content,
            previous_content=previous_content,
            context_contents=context_contents,
            process_step_id=process_step_id,
            llm_config=llm_config or {},
        )

    # 6. Create new passage
    new_passage = await create_passage(
        session,
        content=new_content,
        passage_type=f"perception:{process_step_id}",
        agent_id=agent_id,
        metadata={
            "process_step_id": process_step_id,
            "frame_ref": frame_ref,
            **(input_metadata or {}),
        },
    )

    # 7. Create derivation edges
    source_ids: list[UUID] = []
    if previous_passage_id:
        source_ids.append(previous_passage_id)

    await create_derivations(
        session,
        derived_passage_id=new_passage.id,
        source_passage_ids=source_ids + context_passage_ids,
    )

    # 8. Advance ref with optimistic locking
    # Check hooks_enabled from frame
    fire_hooks = frame.get("hooks_enabled", True)

    await set_ref(
        session,
        perception_ref,
        new_passage.id,
        metadata={"process_step_id": process_step_id},
        fire_hooks=fire_hooks,
    )

    # Get new version
    new_version = await get_ref_version(session, perception_ref)

    await session.flush()

    # Build result
    result = {
        "ok": True,
        "perception_ref": perception_ref,
        "previous_passage_id": previous_passage_id,
        "new_passage_id": new_passage.id,
        "derivation": {
            "derived_passage_id": new_passage.id,
            "source_passage_ids": source_ids,
            "context_passage_ids": context_passage_ids,
            "process_step_id": process_step_id,
        },
        "ref_update": {
            "applied": True,
            "new_ref_version": new_version,
        },
        "trace_id": f"trace_{new_passage.id.hex[:8]}",
    }

    # Cache for idempotency
    if idempotency_key:
        _idempotency_cache[idempotency_key] = result

    return result


async def _compute_next_state(
    *,
    input_content: str,
    previous_content: str,
    context_contents: list[str],
    process_step_id: str,
    llm_config: dict[str, Any],
) -> str:
    """Compute the next state using LLM.

    This is a placeholder that would integrate with the actual LLM provider.
    """
    # For testing, use deterministic output
    hash_input = f"{input_content}{previous_content}{process_step_id}"
    content_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    return f"OUT:{content_hash}"


async def bootstrap_perception(
    session: AsyncSession,
    *,
    agent_id: str,
    perception_ref: str,
    initial_content: str,
    process_step_id: str = "bootstrap",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Bootstrap a new perception with initial content.

    Used when creating a perception for the first time (no previous state).

    Args:
        session: Database session
        agent_id: Agent ID
        perception_ref: Ref name for the perception
        initial_content: Initial content
        process_step_id: Process step ID (default 'bootstrap')
        metadata: Optional metadata

    Returns:
        Result dict with passage ID
    """
    # Check ref doesn't exist
    existing = await get_ref(session, perception_ref)
    if existing:
        raise ValueError(f"Perception ref '{perception_ref}' already exists")

    # Create passage
    passage = await create_passage(
        session,
        content=initial_content,
        passage_type=f"perception:{process_step_id}",
        agent_id=agent_id,
        metadata=metadata or {},
    )

    # Create ref
    await set_ref(
        session,
        perception_ref,
        passage.id,
        metadata={"process_step_id": process_step_id},
        fire_hooks=False,  # Bootstrap doesn't fire hooks
    )

    version = await get_ref_version(session, perception_ref)

    await session.flush()

    return {
        "ok": True,
        "perception_ref": perception_ref,
        "passage_id": passage.id,
        "ref_version": version,
    }


def clear_idempotency_cache() -> None:
    """Clear the idempotency cache. Used for testing."""
    global _idempotency_cache
    _idempotency_cache = {}
