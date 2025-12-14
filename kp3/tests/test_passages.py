"""Tests for passages service."""

from sqlalchemy.ext.asyncio import AsyncSession

from kp3.services.passages import (
    archive_passage,
    compute_content_hash,
    create_passage,
    get_passage,
    get_passage_by_external_id,
    get_passage_by_hash,
    list_passages,
    update_passage,
)


def test_compute_content_hash():
    """Content hash is deterministic."""
    content = "Hello world"
    hash1 = compute_content_hash(content)
    hash2 = compute_content_hash(content)
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex


def test_different_content_different_hash():
    """Different content produces different hash."""
    hash1 = compute_content_hash("Hello")
    hash2 = compute_content_hash("World")
    assert hash1 != hash2


async def test_create_passage(session: AsyncSession):
    """Create a basic passage."""
    passage = await create_passage(
        session,
        content="Test content",
        passage_type="test",
    )

    assert passage.id is not None
    assert passage.content == "Test content"
    assert passage.passage_type == "test"
    assert passage.content_hash == compute_content_hash("Test content")


async def test_create_passage_with_metadata(session: AsyncSession):
    """Create passage with all fields."""
    passage = await create_passage(
        session,
        content="Full passage",
        passage_type="memory_shard",
        source_system="kairix_sqlite",
        source_external_id="r1-abc123",
        metadata={"key": "value"},
    )

    assert passage.source_system == "kairix_sqlite"
    assert passage.source_external_id == "r1-abc123"
    assert passage.metadata_ == {"key": "value"}


async def test_get_passage(session: AsyncSession):
    """Retrieve passage by ID."""
    created = await create_passage(session, content="Find me", passage_type="test")
    await session.commit()

    found = await get_passage(session, created.id)
    assert found is not None
    assert found.id == created.id
    assert found.content == "Find me"


async def test_get_passage_not_found(session: AsyncSession):
    """Return None for missing passage."""
    from uuid import uuid4

    found = await get_passage(session, uuid4())
    assert found is None


async def test_get_passage_by_external_id(session: AsyncSession):
    """Find passage by source system and external ID."""
    await create_passage(
        session,
        content="External",
        passage_type="test",
        source_system="test_system",
        source_external_id="ext-123",
    )
    await session.commit()

    found = await get_passage_by_external_id(session, "test_system", "ext-123")
    assert found is not None
    assert found.content == "External"


async def test_get_passage_by_hash(session: AsyncSession):
    """Find passage by content hash."""
    content = "Unique content for hash test"
    await create_passage(session, content=content, passage_type="test")
    await session.commit()

    found = await get_passage_by_hash(session, compute_content_hash(content))
    assert found is not None
    assert found.content == content


async def test_list_passages(session: AsyncSession):
    """List passages with filters."""
    await create_passage(session, content="Type A 1", passage_type="type_a")
    await create_passage(session, content="Type A 2", passage_type="type_a")
    await create_passage(session, content="Type B", passage_type="type_b")
    await session.commit()

    all_passages = await list_passages(session)
    assert len(all_passages) == 3

    type_a = await list_passages(session, passage_type="type_a")
    assert len(type_a) == 2


async def test_archive_passage(session: AsyncSession):
    """Archive preserves passage state."""
    passage = await create_passage(
        session,
        content="Original content",
        passage_type="test",
        metadata={"version": 1},
    )
    await session.commit()

    archive = await archive_passage(session, passage)

    assert archive.id == passage.id
    assert archive.content == "Original content"
    assert archive.metadata_ == {"version": 1}
    assert archive.archived_at is not None


async def test_update_passage_with_archive(session: AsyncSession):
    """Update passage creates archive of old version."""
    passage = await create_passage(
        session,
        content="Version 1",
        passage_type="test",
    )
    await session.commit()

    original_hash = passage.content_hash

    updated = await update_passage(
        session,
        passage,
        {"content": "Version 2"},
        archive=True,
    )

    assert updated.content == "Version 2"
    assert updated.content_hash != original_hash
    assert updated.content_hash == compute_content_hash("Version 2")
