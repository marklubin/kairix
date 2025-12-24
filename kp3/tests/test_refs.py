"""Tests for refs service."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.db.models import Passage
from kp3.services.passages import create_passage
from kp3.services.refs import (
    clear_hooks,
    delete_ref,
    get_ref,
    get_ref_passage,
    list_refs,
    register_hook,
    set_ref,
)


@pytest.fixture
async def sample_passage(db_session: AsyncSession) -> Passage:
    """Create a sample passage for testing."""
    passage = await create_passage(
        db_session,
        content="Test passage content",
        passage_type="test",
    )
    await db_session.commit()
    await db_session.refresh(passage)
    return passage


@pytest.fixture
async def another_passage(db_session: AsyncSession) -> Passage:
    """Create another passage for testing."""
    passage = await create_passage(
        db_session,
        content="Another passage content",
        passage_type="test",
    )
    await db_session.commit()
    await db_session.refresh(passage)
    return passage


@pytest.fixture(autouse=True)
def clear_hooks_fixture():
    """Clear hooks before and after each test."""
    clear_hooks()
    yield
    clear_hooks()


async def test_create_ref(db_session: AsyncSession, sample_passage: Passage):
    """Create a new ref pointing to a passage."""
    ref = await set_ref(db_session, "test/ref/HEAD", sample_passage.id, fire_hooks=False)

    assert ref.name == "test/ref/HEAD"
    assert ref.passage_id == sample_passage.id
    assert ref.updated_at is not None


async def test_get_ref(db_session: AsyncSession, sample_passage: Passage):
    """Get passage ID from a ref."""
    await set_ref(db_session, "test/ref/HEAD", sample_passage.id, fire_hooks=False)

    passage_id = await get_ref(db_session, "test/ref/HEAD")
    assert passage_id == sample_passage.id


async def test_get_ref_not_found(db_session: AsyncSession):
    """Return None for non-existent ref."""
    passage_id = await get_ref(db_session, "nonexistent/ref")
    assert passage_id is None


async def test_get_ref_passage(db_session: AsyncSession, sample_passage: Passage):
    """Get full passage object from a ref."""
    await set_ref(db_session, "test/ref/HEAD", sample_passage.id, fire_hooks=False)

    passage = await get_ref_passage(db_session, "test/ref/HEAD")
    assert passage is not None
    assert passage.id == sample_passage.id
    assert passage.content == "Test passage content"


async def test_update_ref(
    db_session: AsyncSession, sample_passage: Passage, another_passage: Passage
):
    """Update an existing ref to point to a different passage."""
    # Create initial ref
    await set_ref(db_session, "test/ref/HEAD", sample_passage.id, fire_hooks=False)

    # Update to point to different passage
    ref = await set_ref(db_session, "test/ref/HEAD", another_passage.id, fire_hooks=False)

    assert ref.passage_id == another_passage.id

    # Verify via get
    current_id = await get_ref(db_session, "test/ref/HEAD")
    assert current_id == another_passage.id


async def test_ref_hooks_fire(db_session: AsyncSession, sample_passage: Passage):
    """Hooks are called when refs are updated."""
    hook_calls: list[tuple[str, Passage]] = []

    async def test_hook(ref_name: str, passage: Passage) -> None:
        hook_calls.append((ref_name, passage))

    register_hook("test/hook/HEAD", test_hook)

    # Set ref should trigger hook
    await set_ref(db_session, "test/hook/HEAD", sample_passage.id, fire_hooks=True)

    assert len(hook_calls) == 1
    assert hook_calls[0][0] == "test/hook/HEAD"
    assert hook_calls[0][1].id == sample_passage.id


async def test_hooks_not_fired_when_disabled(db_session: AsyncSession, sample_passage: Passage):
    """Hooks are not called when fire_hooks=False."""
    hook_calls: list[tuple[str, Passage]] = []

    async def test_hook(ref_name: str, passage: Passage) -> None:
        hook_calls.append((ref_name, passage))

    register_hook("test/no-hook/HEAD", test_hook)

    await set_ref(db_session, "test/no-hook/HEAD", sample_passage.id, fire_hooks=False)

    assert len(hook_calls) == 0


async def test_list_refs(db_session: AsyncSession, sample_passage: Passage, another_passage: Passage):
    """List all refs."""
    await set_ref(db_session, "world/human/HEAD", sample_passage.id, fire_hooks=False)
    await set_ref(db_session, "world/persona/HEAD", another_passage.id, fire_hooks=False)

    refs = await list_refs(db_session)
    assert len(refs) == 2

    names = {r["name"] for r in refs}
    assert names == {"world/human/HEAD", "world/persona/HEAD"}


async def test_list_refs_with_prefix(
    db_session: AsyncSession, sample_passage: Passage, another_passage: Passage
):
    """List refs filtered by prefix."""
    await set_ref(db_session, "world/human/HEAD", sample_passage.id, fire_hooks=False)
    await set_ref(db_session, "world/persona/HEAD", another_passage.id, fire_hooks=False)
    await set_ref(db_session, "other/ref", sample_passage.id, fire_hooks=False)

    world_refs = await list_refs(db_session, prefix="world/")
    assert len(world_refs) == 2

    other_refs = await list_refs(db_session, prefix="other/")
    assert len(other_refs) == 1


async def test_delete_ref(db_session: AsyncSession, sample_passage: Passage):
    """Delete an existing ref."""
    await set_ref(db_session, "test/delete/HEAD", sample_passage.id, fire_hooks=False)

    # Verify it exists
    assert await get_ref(db_session, "test/delete/HEAD") is not None

    # Delete it
    deleted = await delete_ref(db_session, "test/delete/HEAD")
    assert deleted is True

    # Verify it's gone
    assert await get_ref(db_session, "test/delete/HEAD") is None


async def test_delete_nonexistent_ref(db_session: AsyncSession):
    """Deleting a non-existent ref returns False."""
    deleted = await delete_ref(db_session, "nonexistent/ref")
    assert deleted is False


async def test_ref_with_metadata(db_session: AsyncSession, sample_passage: Passage):
    """Refs can store metadata."""
    ref = await set_ref(
        db_session,
        "test/metadata/HEAD",
        sample_passage.id,
        metadata={"branch": "experiment-v2", "created_by": "test"},
        fire_hooks=False,
    )

    assert ref.metadata_ == {"branch": "experiment-v2", "created_by": "test"}
