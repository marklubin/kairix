"""Refs service for managing mutable pointers to passages."""

import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.db.models import Passage, PassageRef, PassageRefHistory, PassageRefHook

if TYPE_CHECKING:
    from kp3.db.models import WorldModelBranch

logger = logging.getLogger(__name__)


async def get_ref(session: AsyncSession, name: str) -> UUID | None:
    """Get the passage ID a ref points to.

    Args:
        session: Database session
        name: Ref name (e.g., "world/human/HEAD")

    Returns:
        Passage UUID if ref exists, None otherwise
    """
    stmt = select(PassageRef.passage_id).where(PassageRef.name == name)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_ref_passage(session: AsyncSession, name: str) -> Passage | None:
    """Get the passage a ref points to.

    Args:
        session: Database session
        name: Ref name (e.g., "world/human/HEAD")

    Returns:
        Passage if ref exists, None otherwise
    """
    stmt = (
        select(Passage)
        .join(PassageRef, PassageRef.passage_id == Passage.id)
        .where(PassageRef.name == name)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_branch_for_ref(session: AsyncSession, name: str) -> "WorldModelBranch | None":
    """Get the branch that owns a specific ref.

    Args:
        session: Database session
        name: Ref name (e.g., "corindel/human/experiment-1")

    Returns:
        WorldModelBranch if the ref belongs to a branch, None otherwise
    """
    from kp3.db.models import WorldModelBranch

    stmt = select(WorldModelBranch).where(
        (WorldModelBranch.human_ref == name)
        | (WorldModelBranch.persona_ref == name)
        | (WorldModelBranch.world_ref == name)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def should_fire_hooks_for_ref(session: AsyncSession, name: str) -> bool:
    """Determine if hooks should fire for a ref based on its branch settings.

    If the ref belongs to a branch with hooks_enabled=False, returns False.
    Otherwise returns True (default behavior for refs without branches).

    Args:
        session: Database session
        name: Ref name

    Returns:
        True if hooks should fire, False otherwise
    """
    branch = await get_branch_for_ref(session, name)
    if branch is not None:
        return branch.hooks_enabled
    return True  # Default: fire hooks for refs not in branches


async def set_ref(
    session: AsyncSession,
    name: str,
    passage_id: UUID,
    *,
    metadata: dict[str, Any] | None = None,
    fire_hooks: bool = True,
) -> PassageRef:
    """Set a ref to point to a passage, creating or updating as needed.

    Records history and fires DB-configured hooks.

    Args:
        session: Database session
        name: Ref name (e.g., "world/human/HEAD")
        passage_id: UUID of the passage to point to
        metadata: Optional metadata to store with the ref
        fire_hooks: Whether to fire DB-configured hooks (default True).
            If True, also checks branch settings - refs belonging to branches
            with hooks_enabled=False will not fire hooks.

    Returns:
        The created or updated PassageRef
    """
    # Get current ref state for history
    previous_passage_id = await get_ref(session, name)

    # Use upsert (INSERT ... ON CONFLICT UPDATE)
    stmt = insert(PassageRef).values(
        name=name,
        passage_id=passage_id,
        metadata_=metadata or {},
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["name"],
        set_={
            "passage_id": passage_id,
            "metadata": metadata or {},  # Use actual column name, not Python attr
            "updated_at": stmt.excluded.updated_at,
        },
    )
    await session.execute(stmt)

    # Record history
    history_entry = PassageRefHistory(
        ref_name=name,
        passage_id=passage_id,
        previous_passage_id=previous_passage_id,
        metadata_=metadata or {},
    )
    session.add(history_entry)
    await session.flush()

    # Fetch the ref to return
    ref_stmt = select(PassageRef).where(PassageRef.name == name)
    result = await session.execute(ref_stmt)
    ref = result.scalar_one()

    # Fire DB-configured hooks
    # Check both explicit fire_hooks flag AND branch settings
    should_fire = fire_hooks and await should_fire_hooks_for_ref(session, name)
    if should_fire:
        passage = await session.get(Passage, passage_id)
        if passage:
            await _execute_db_hooks(session, name, passage)

    return ref


async def _execute_db_hooks(session: AsyncSession, ref_name: str, passage: Passage) -> None:
    """Execute hooks configured in the database for this ref."""
    stmt = select(PassageRefHook).where(
        PassageRefHook.ref_name == ref_name,
        PassageRefHook.enabled == True,  # noqa: E712
    )
    result = await session.execute(stmt)
    hooks = result.scalars().all()

    for hook in hooks:
        try:
            await _execute_hook_action(hook, passage)
        except Exception as e:
            logger.exception("Hook %s failed for ref %s: %s", hook.id, ref_name, e)
            # Re-raise to let caller handle - hooks should not silently fail
            raise


async def _execute_hook_action(hook: PassageRefHook, passage: Passage) -> None:
    """Execute a single hook action based on its type.

    Hook types can be extended by adding new action_type handlers here.
    Currently supported:
        - "webhook": POST to a URL with passage content (future)
        - Custom types can be added as needed

    Note: The previous "letta_agent_block_update" type has been removed.
    For external integrations, use the REST API or implement a custom hook.
    """
    # Log unknown hook types - they are silently skipped
    # This allows forward compatibility with new hook types
    logger.warning(
        "Hook action type '%s' is not implemented. "
        "Configure external integrations via the REST API instead.",
        hook.action_type,
    )


async def list_refs(
    session: AsyncSession,
    *,
    prefix: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List all refs, optionally filtered by prefix.

    Args:
        session: Database session
        prefix: Optional prefix to filter by (e.g., "world/human/")
        limit: Maximum number of refs to return

    Returns:
        List of dicts with name, passage_id, updated_at, metadata
    """
    stmt = select(PassageRef)

    if prefix:
        stmt = stmt.where(PassageRef.name.like(f"{prefix}%"))

    stmt = stmt.order_by(PassageRef.name).limit(limit)

    result = await session.execute(stmt)
    refs = result.scalars().all()

    return [
        {
            "name": ref.name,
            "passage_id": ref.passage_id,
            "updated_at": ref.updated_at,
            "metadata": ref.metadata_,
        }
        for ref in refs
    ]


async def delete_ref(session: AsyncSession, name: str) -> bool:
    """Delete a ref.

    Args:
        session: Database session
        name: Ref name to delete

    Returns:
        True if the ref existed and was deleted, False otherwise
    """
    from sqlalchemy import delete

    stmt = delete(PassageRef).where(PassageRef.name == name).returning(PassageRef.name)
    result = await session.execute(stmt)
    await session.flush()
    return result.scalar_one_or_none() is not None


async def get_ref_history(
    session: AsyncSession,
    name: str,
    *,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Get history of changes for a ref.

    Args:
        session: Database session
        name: Ref name
        limit: Maximum number of history entries to return

    Returns:
        List of history entries, newest first
    """
    stmt = (
        select(PassageRefHistory)
        .where(PassageRefHistory.ref_name == name)
        .order_by(PassageRefHistory.changed_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    entries = result.scalars().all()

    return [
        {
            "id": entry.id,
            "ref_name": entry.ref_name,
            "passage_id": entry.passage_id,
            "previous_passage_id": entry.previous_passage_id,
            "changed_at": entry.changed_at,
            "metadata": entry.metadata_,
        }
        for entry in entries
    ]


async def create_ref_hook(
    session: AsyncSession,
    ref_name: str,
    action_type: str,
    config: dict[str, Any],
    *,
    enabled: bool = True,
) -> PassageRefHook:
    """Create a new hook for a ref.

    Args:
        session: Database session
        ref_name: Ref name to attach hook to
        action_type: Hook action type (e.g., "webhook")
        config: Action-specific configuration
        enabled: Whether hook is enabled (default True)

    Returns:
        The created PassageRefHook
    """
    hook = PassageRefHook(
        ref_name=ref_name,
        action_type=action_type,
        config=config,
        enabled=enabled,
    )
    session.add(hook)
    await session.flush()
    return hook


async def list_ref_hooks(
    session: AsyncSession,
    ref_name: str | None = None,
    *,
    enabled_only: bool = True,
) -> list[PassageRefHook]:
    """List hooks, optionally filtered by ref name.

    Args:
        session: Database session
        ref_name: Optional ref name to filter by
        enabled_only: Only return enabled hooks (default True)

    Returns:
        List of PassageRefHook objects
    """
    stmt = select(PassageRefHook)

    if ref_name:
        stmt = stmt.where(PassageRefHook.ref_name == ref_name)

    if enabled_only:
        stmt = stmt.where(PassageRefHook.enabled == True)  # noqa: E712

    result = await session.execute(stmt)
    return list(result.scalars().all())
