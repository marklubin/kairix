"""Passage CRUD operations and archiving."""

import hashlib
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.db.models import Passage, PassageArchive


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of content."""
    return hashlib.sha256(content.encode()).hexdigest()


async def create_passage(
    session: AsyncSession,
    content: str,
    passage_type: str,
    *,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    metadata: dict[str, Any] | None = None,
    source_system: str | None = None,
    source_external_id: str | None = None,
    embedding_openai: list[float] | None = None,
    agent_id: str | None = None,
) -> Passage:
    """Create a new passage.

    Args:
        session: Database session
        content: Passage content text
        passage_type: Type of passage (e.g., "session_summary", "memory_shard")
        period_start: Optional start of the period this passage covers
        period_end: Optional end of the period this passage covers
        metadata: Optional metadata dict
        source_system: Optional source system identifier
        source_external_id: Optional external ID from source system
        embedding_openai: Optional pre-computed embedding vector
        agent_id: Optional agent ID to scope this passage to a specific agent
    """
    content_hash = compute_content_hash(content)

    passage = Passage(
        content=content,
        content_hash=content_hash,
        passage_type=passage_type,
        period_start=period_start,
        period_end=period_end,
        metadata_=metadata or {},
        source_system=source_system,
        source_external_id=source_external_id,
        embedding_openai=embedding_openai,
        agent_id=agent_id,
    )

    session.add(passage)
    await session.flush()
    return passage


async def get_passage(session: AsyncSession, passage_id: UUID) -> Passage | None:
    """Get a passage by ID."""
    return await session.get(Passage, passage_id)


async def get_passage_by_external_id(
    session: AsyncSession, source_system: str, source_external_id: str
) -> Passage | None:
    """Get a passage by its external source ID."""
    stmt = select(Passage).where(
        Passage.source_system == source_system,
        Passage.source_external_id == source_external_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_passage_by_hash(session: AsyncSession, content_hash: str) -> Passage | None:
    """Get a passage by content hash."""
    stmt = select(Passage).where(Passage.content_hash == content_hash)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_passages(
    session: AsyncSession,
    *,
    passage_type: str | None = None,
    source_system: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Passage]:
    """List passages with optional filters."""
    stmt = select(Passage)

    if passage_type:
        stmt = stmt.where(Passage.passage_type == passage_type)
    if source_system:
        stmt = stmt.where(Passage.source_system == source_system)

    stmt = stmt.order_by(Passage.created_at.desc()).limit(limit).offset(offset)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def archive_passage(
    session: AsyncSession,
    passage: Passage,
    run_id: UUID | None = None,
) -> PassageArchive:
    """Archive the current state of a passage before updating."""
    archive = PassageArchive(
        archived_by_run_id=run_id,
        id=passage.id,
        content=passage.content,
        content_hash=passage.content_hash,
        passage_type=passage.passage_type,
        period_start=passage.period_start,
        period_end=passage.period_end,
        metadata_=passage.metadata_,
        source_system=passage.source_system,
        source_external_id=passage.source_external_id,
        embedding_openai=passage.embedding_openai,
        created_at=passage.created_at,
    )

    session.add(archive)
    await session.flush()
    return archive


async def update_passage(
    session: AsyncSession,
    passage: Passage,
    updates: dict[str, Any],
    *,
    run_id: UUID | None = None,
    archive: bool = True,
) -> Passage:
    """Update a passage, optionally archiving the previous version."""
    if archive:
        await archive_passage(session, passage, run_id)

    for key, value in updates.items():
        if key == "metadata":
            passage.metadata_ = value
        elif hasattr(passage, key):
            setattr(passage, key, value)

    # Recompute hash if content changed
    if "content" in updates:
        passage.content_hash = compute_content_hash(passage.content)

    await session.flush()
    return passage
