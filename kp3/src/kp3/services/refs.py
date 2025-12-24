"""Refs service for managing mutable pointers to passages."""

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.db.models import Passage, PassageRef

# Type for hook callbacks
RefHook = Callable[[str, Passage], Awaitable[None]]

# Global hook registry
_ref_hooks: dict[str, list[RefHook]] = {}


def register_hook(ref_pattern: str, hook: RefHook) -> None:
    """Register a hook to fire when a ref matching pattern is updated.

    Args:
        ref_pattern: Exact ref name to match (glob patterns not yet supported)
        hook: Async callback that receives (ref_name, passage)
    """
    if ref_pattern not in _ref_hooks:
        _ref_hooks[ref_pattern] = []
    _ref_hooks[ref_pattern].append(hook)


def clear_hooks() -> None:
    """Clear all registered hooks. Useful for testing."""
    _ref_hooks.clear()


async def _fire_hooks(ref_name: str, passage: Passage) -> None:
    """Fire all hooks matching the ref name."""
    for pattern, hooks in _ref_hooks.items():
        if _matches_pattern(ref_name, pattern):
            for hook in hooks:
                await hook(ref_name, passage)


def _matches_pattern(name: str, pattern: str) -> bool:
    """Check if ref name matches pattern.

    Currently supports exact match only. Future: add glob/prefix matching.
    """
    return name == pattern


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
    row = result.scalar_one_or_none()
    return row


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


async def set_ref(
    session: AsyncSession,
    name: str,
    passage_id: UUID,
    *,
    metadata: dict[str, Any] | None = None,
    fire_hooks: bool = True,
) -> PassageRef:
    """Set a ref to point to a passage, creating or updating as needed.

    Args:
        session: Database session
        name: Ref name (e.g., "world/human/HEAD")
        passage_id: UUID of the passage to point to
        metadata: Optional metadata to store with the ref
        fire_hooks: Whether to fire registered hooks (default True)

    Returns:
        The created or updated PassageRef
    """
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
            "metadata_": metadata or {},
            "updated_at": stmt.excluded.updated_at,
        },
    )
    await session.execute(stmt)
    await session.flush()

    # Fetch the ref to return
    ref_stmt = select(PassageRef).where(PassageRef.name == name)
    result = await session.execute(ref_stmt)
    ref = result.scalar_one()

    if fire_hooks:
        passage = await session.get(Passage, passage_id)
        if passage:
            await _fire_hooks(name, passage)

    return ref


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
    stmt = delete(PassageRef).where(PassageRef.name == name).returning(PassageRef.name)
    result = await session.execute(stmt)
    await session.flush()
    return result.scalar_one_or_none() is not None


async def update_ref_metadata(
    session: AsyncSession,
    name: str,
    metadata: dict[str, Any],
) -> PassageRef | None:
    """Update only the metadata of a ref without changing the passage.

    Args:
        session: Database session
        name: Ref name
        metadata: New metadata to set

    Returns:
        Updated PassageRef if it exists, None otherwise
    """
    stmt = (
        update(PassageRef)
        .where(PassageRef.name == name)
        .values(metadata_=metadata)
        .returning(PassageRef)
    )
    result = await session.execute(stmt)
    await session.flush()
    return result.scalar_one_or_none()
