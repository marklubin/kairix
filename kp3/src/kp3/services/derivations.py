"""Derivation chain queries for provenance tracking."""

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.db.models import Passage, PassageDerivation


async def create_derivations(
    session: AsyncSession,
    derived_passage_id: UUID,
    source_passage_ids: list[UUID],
    processing_run_id: UUID | None = None,
) -> list[PassageDerivation]:
    """Create derivation links from source passages to a derived passage."""
    derivations: list[PassageDerivation] = []
    for order, source_id in enumerate(source_passage_ids):
        derivation = PassageDerivation(
            derived_passage_id=derived_passage_id,
            source_passage_id=source_id,
            processing_run_id=processing_run_id,
            source_order=order,
        )
        session.add(derivation)
        derivations.append(derivation)

    await session.flush()
    return derivations


async def get_sources(session: AsyncSession, passage_id: UUID) -> list[Passage]:
    """Get immediate source passages for a derived passage."""
    stmt = (
        select(Passage)
        .join(PassageDerivation, PassageDerivation.source_passage_id == Passage.id)
        .where(PassageDerivation.derived_passage_id == passage_id)
        .order_by(PassageDerivation.source_order)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_derived(session: AsyncSession, passage_id: UUID) -> list[Passage]:
    """Get passages that were derived from this passage."""
    stmt = (
        select(Passage)
        .join(PassageDerivation, PassageDerivation.derived_passage_id == Passage.id)
        .where(PassageDerivation.source_passage_id == passage_id)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_full_provenance(
    session: AsyncSession,
    passage_id: UUID,
    max_depth: int = 10,
) -> list[dict[str, UUID | int]]:
    """
    Get full derivation chain for a passage using recursive CTE.

    Returns list of dicts with:
    - derived_passage_id: the passage in the chain
    - source_passage_id: its source
    - depth: how many levels from the starting passage
    """
    query = text("""
        WITH RECURSIVE chain AS (
            -- Base case: direct sources of the target passage
            SELECT
                derived_passage_id,
                source_passage_id,
                processing_run_id,
                1 as depth
            FROM passage_derivations
            WHERE derived_passage_id = :passage_id

            UNION ALL

            -- Recursive case: sources of sources
            SELECT
                pd.derived_passage_id,
                pd.source_passage_id,
                pd.processing_run_id,
                c.depth + 1 as depth
            FROM passage_derivations pd
            JOIN chain c ON pd.derived_passage_id = c.source_passage_id
            WHERE c.depth < :max_depth
        )
        SELECT * FROM chain ORDER BY depth, source_passage_id
    """)

    result = await session.execute(query, {"passage_id": passage_id, "max_depth": max_depth})
    rows = result.fetchall()

    return [
        {
            "derived_passage_id": row.derived_passage_id,
            "source_passage_id": row.source_passage_id,
            "processing_run_id": row.processing_run_id,
            "depth": row.depth,
        }
        for row in rows
    ]


async def get_leaf_sources(session: AsyncSession, passage_id: UUID) -> list[Passage]:
    """Get the original (leaf) source passages with no further sources."""
    query = text("""
        WITH RECURSIVE chain AS (
            SELECT
                derived_passage_id,
                source_passage_id,
                1 as depth
            FROM passage_derivations
            WHERE derived_passage_id = :passage_id

            UNION ALL

            SELECT
                pd.derived_passage_id,
                pd.source_passage_id,
                c.depth + 1 as depth
            FROM passage_derivations pd
            JOIN chain c ON pd.derived_passage_id = c.source_passage_id
        )
        SELECT DISTINCT source_passage_id
        FROM chain c
        WHERE NOT EXISTS (
            SELECT 1 FROM passage_derivations pd
            WHERE pd.derived_passage_id = c.source_passage_id
        )
    """)

    result = await session.execute(query, {"passage_id": passage_id})
    leaf_ids = [row.source_passage_id for row in result.fetchall()]

    if not leaf_ids:
        return []

    stmt = select(Passage).where(Passage.id.in_(leaf_ids))
    result = await session.execute(stmt)
    return list(result.scalars().all())
