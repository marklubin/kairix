"""Tests for derivations service."""


from sqlalchemy.ext.asyncio import AsyncSession

from kp3.db.models import ProcessingRun
from kp3.services.derivations import (
    create_derivations,
    get_derived,
    get_full_provenance,
    get_leaf_sources,
    get_sources,
)
from kp3.services.passages import create_passage


async def test_create_derivations(session: AsyncSession):
    """Create derivation links between passages."""
    # Create source passages
    source1 = await create_passage(session, content="Source 1", passage_type="raw")
    source2 = await create_passage(session, content="Source 2", passage_type="raw")

    # Create derived passage
    derived = await create_passage(session, content="Derived", passage_type="summary")

    # Create a processing run
    run = ProcessingRun(
        input_sql="SELECT ...",
        processor_type="test",
        processor_config={},
        status="completed",
    )
    session.add(run)
    await session.flush()

    # Create derivations
    derivations = await create_derivations(
        session,
        derived_passage_id=derived.id,
        source_passage_ids=[source1.id, source2.id],
        processing_run_id=run.id,
    )

    assert len(derivations) == 2
    assert derivations[0].source_order == 0
    assert derivations[1].source_order == 1


async def test_get_sources(session: AsyncSession):
    """Get immediate source passages."""
    source1 = await create_passage(session, content="Source A", passage_type="raw")
    source2 = await create_passage(session, content="Source B", passage_type="raw")
    derived = await create_passage(session, content="Derived", passage_type="summary")

    run = ProcessingRun(
        input_sql="SELECT ...",
        processor_type="test",
        processor_config={},
        status="completed",
    )
    session.add(run)
    await session.flush()

    await create_derivations(
        session,
        derived_passage_id=derived.id,
        source_passage_ids=[source1.id, source2.id],
        processing_run_id=run.id,
    )
    await session.commit()

    sources = await get_sources(session, derived.id)
    assert len(sources) == 2
    assert sources[0].id == source1.id
    assert sources[1].id == source2.id


async def test_get_derived(session: AsyncSession):
    """Get passages derived from a source."""
    source = await create_passage(session, content="Source", passage_type="raw")
    derived1 = await create_passage(session, content="Derived 1", passage_type="summary")
    derived2 = await create_passage(session, content="Derived 2", passage_type="summary")

    run = ProcessingRun(
        input_sql="SELECT ...",
        processor_type="test",
        processor_config={},
        status="completed",
    )
    session.add(run)
    await session.flush()

    await create_derivations(session, derived1.id, [source.id], run.id)
    await create_derivations(session, derived2.id, [source.id], run.id)
    await session.commit()

    derived = await get_derived(session, source.id)
    assert len(derived) == 2
    derived_ids = {p.id for p in derived}
    assert derived1.id in derived_ids
    assert derived2.id in derived_ids


async def test_get_full_provenance(session: AsyncSession):
    """Get full derivation chain with depth."""
    # Create a chain: leaf1, leaf2 -> mid -> final
    leaf1 = await create_passage(session, content="Leaf 1", passage_type="raw")
    leaf2 = await create_passage(session, content="Leaf 2", passage_type="raw")
    mid = await create_passage(session, content="Middle", passage_type="summary")
    final = await create_passage(session, content="Final", passage_type="aggregate")

    run = ProcessingRun(
        input_sql="SELECT ...",
        processor_type="test",
        processor_config={},
        status="completed",
    )
    session.add(run)
    await session.flush()

    # mid derived from leaf1, leaf2
    await create_derivations(session, mid.id, [leaf1.id, leaf2.id], run.id)
    # final derived from mid
    await create_derivations(session, final.id, [mid.id], run.id)
    await session.commit()

    # Get full provenance of final
    provenance = await get_full_provenance(session, final.id)

    assert len(provenance) == 3  # mid->final, leaf1->mid, leaf2->mid

    # Check depths
    depth_1 = [p for p in provenance if p["depth"] == 1]
    depth_2 = [p for p in provenance if p["depth"] == 2]

    assert len(depth_1) == 1  # mid is direct source
    assert depth_1[0]["source_passage_id"] == mid.id

    assert len(depth_2) == 2  # leaf1 and leaf2 are depth 2


async def test_get_leaf_sources(session: AsyncSession):
    """Get original leaf sources with no further derivation."""
    # Create chain: leaf1, leaf2 -> mid -> final
    leaf1 = await create_passage(session, content="Original 1", passage_type="raw")
    leaf2 = await create_passage(session, content="Original 2", passage_type="raw")
    mid = await create_passage(session, content="Middle", passage_type="summary")
    final = await create_passage(session, content="Final", passage_type="aggregate")

    run = ProcessingRun(
        input_sql="SELECT ...",
        processor_type="test",
        processor_config={},
        status="completed",
    )
    session.add(run)
    await session.flush()

    await create_derivations(session, mid.id, [leaf1.id, leaf2.id], run.id)
    await create_derivations(session, final.id, [mid.id], run.id)
    await session.commit()

    # Get leaf sources of final
    leaves = await get_leaf_sources(session, final.id)

    assert len(leaves) == 2
    leaf_ids = {p.id for p in leaves}
    assert leaf1.id in leaf_ids
    assert leaf2.id in leaf_ids


async def test_get_sources_empty(session: AsyncSession):
    """Get sources returns empty for passages with no sources."""
    passage = await create_passage(session, content="Standalone", passage_type="raw")
    await session.commit()

    sources = await get_sources(session, passage.id)
    assert sources == []


async def test_get_leaf_sources_is_leaf(session: AsyncSession):
    """Leaf source of a leaf is empty."""
    leaf = await create_passage(session, content="Leaf", passage_type="raw")
    await session.commit()

    leaves = await get_leaf_sources(session, leaf.id)
    assert leaves == []
