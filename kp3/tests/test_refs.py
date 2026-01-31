"""Tests for refs service."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.db.models import Passage
from kp3.services.passages import create_passage
from kp3.services.refs import (
    create_ref_hook,
    delete_ref,
    get_ref,
    get_ref_history,
    get_ref_passage,
    list_ref_hooks,
    list_refs,
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


async def test_create_ref(db_session: AsyncSession, sample_passage: Passage) -> None:
    """Create a new ref pointing to a passage."""
    ref = await set_ref(db_session, "test/ref/HEAD", sample_passage.id, fire_hooks=False)

    assert ref.name == "test/ref/HEAD"
    assert ref.passage_id == sample_passage.id
    assert ref.updated_at is not None


async def test_get_ref(db_session: AsyncSession, sample_passage: Passage) -> None:
    """Get passage ID from a ref."""
    await set_ref(db_session, "test/ref/HEAD", sample_passage.id, fire_hooks=False)

    passage_id = await get_ref(db_session, "test/ref/HEAD")
    assert passage_id == sample_passage.id


async def test_get_ref_not_found(db_session: AsyncSession) -> None:
    """Return None for non-existent ref."""
    passage_id = await get_ref(db_session, "nonexistent/ref")
    assert passage_id is None


async def test_get_ref_passage(db_session: AsyncSession, sample_passage: Passage) -> None:
    """Get full passage object from a ref."""
    await set_ref(db_session, "test/ref/HEAD", sample_passage.id, fire_hooks=False)

    passage = await get_ref_passage(db_session, "test/ref/HEAD")
    assert passage is not None
    assert passage.id == sample_passage.id
    assert passage.content == "Test passage content"


async def test_update_ref(
    db_session: AsyncSession, sample_passage: Passage, another_passage: Passage
) -> None:
    """Update an existing ref to point to a different passage."""
    # Create initial ref
    await set_ref(db_session, "test/ref/HEAD", sample_passage.id, fire_hooks=False)

    # Update to point to different passage
    ref = await set_ref(db_session, "test/ref/HEAD", another_passage.id, fire_hooks=False)

    assert ref.passage_id == another_passage.id

    # Verify via get
    current_id = await get_ref(db_session, "test/ref/HEAD")
    assert current_id == another_passage.id


async def test_list_refs(
    db_session: AsyncSession, sample_passage: Passage, another_passage: Passage
) -> None:
    """List all refs."""
    await set_ref(db_session, "world/human/HEAD", sample_passage.id, fire_hooks=False)
    await set_ref(db_session, "world/persona/HEAD", another_passage.id, fire_hooks=False)

    refs = await list_refs(db_session)
    assert len(refs) == 2

    names = {r["name"] for r in refs}
    assert names == {"world/human/HEAD", "world/persona/HEAD"}


async def test_list_refs_with_prefix(
    db_session: AsyncSession, sample_passage: Passage, another_passage: Passage
) -> None:
    """List refs filtered by prefix."""
    await set_ref(db_session, "world/human/HEAD", sample_passage.id, fire_hooks=False)
    await set_ref(db_session, "world/persona/HEAD", another_passage.id, fire_hooks=False)
    await set_ref(db_session, "other/ref", sample_passage.id, fire_hooks=False)

    world_refs = await list_refs(db_session, prefix="world/")
    assert len(world_refs) == 2

    other_refs = await list_refs(db_session, prefix="other/")
    assert len(other_refs) == 1


async def test_delete_ref(db_session: AsyncSession, sample_passage: Passage) -> None:
    """Delete an existing ref."""
    await set_ref(db_session, "test/delete/HEAD", sample_passage.id, fire_hooks=False)

    # Verify it exists
    assert await get_ref(db_session, "test/delete/HEAD") is not None

    # Delete it
    deleted = await delete_ref(db_session, "test/delete/HEAD")
    assert deleted is True

    # Verify it's gone
    assert await get_ref(db_session, "test/delete/HEAD") is None


async def test_delete_nonexistent_ref(db_session: AsyncSession) -> None:
    """Deleting a non-existent ref returns False."""
    deleted = await delete_ref(db_session, "nonexistent/ref")
    assert deleted is False


async def test_ref_with_metadata(db_session: AsyncSession, sample_passage: Passage) -> None:
    """Refs can store metadata."""
    ref = await set_ref(
        db_session,
        "test/metadata/HEAD",
        sample_passage.id,
        metadata={"branch": "experiment-v2", "created_by": "test"},
        fire_hooks=False,
    )

    assert ref.metadata_ == {"branch": "experiment-v2", "created_by": "test"}


async def test_ref_history_recorded(
    db_session: AsyncSession, sample_passage: Passage, another_passage: Passage
) -> None:
    """Setting refs records history."""
    # Create initial ref
    await set_ref(db_session, "test/history/HEAD", sample_passage.id, fire_hooks=False)
    await db_session.commit()

    # Update ref
    await set_ref(db_session, "test/history/HEAD", another_passage.id, fire_hooks=False)
    await db_session.commit()

    # Check history
    history = await get_ref_history(db_session, "test/history/HEAD")
    assert len(history) == 2

    # Most recent first
    assert history[0]["passage_id"] == another_passage.id
    assert history[0]["previous_passage_id"] == sample_passage.id

    assert history[1]["passage_id"] == sample_passage.id
    assert history[1]["previous_passage_id"] is None


async def test_create_ref_hook(db_session: AsyncSession) -> None:
    """Create a ref hook in the database."""
    hook = await create_ref_hook(
        db_session,
        ref_name="world/human/HEAD",
        action_type="webhook",
        config={"agent_id": "test-agent", "block_label": "human"},
    )
    await db_session.commit()

    assert hook.ref_name == "world/human/HEAD"
    assert hook.action_type == "webhook"
    assert hook.config == {"agent_id": "test-agent", "block_label": "human"}
    assert hook.enabled is True


async def test_list_ref_hooks(db_session: AsyncSession) -> None:
    """List hooks for a ref."""
    await create_ref_hook(
        db_session,
        ref_name="world/persona/HEAD",
        action_type="webhook",
        config={"agent_id": "agent-1", "block_label": "persona"},
    )
    await create_ref_hook(
        db_session,
        ref_name="world/persona/HEAD",
        action_type="custom_action",
        config={"custom": "config"},
    )
    await db_session.commit()

    hooks = await list_ref_hooks(db_session, "world/persona/HEAD")
    assert len(hooks) == 2

    action_types = {h.action_type for h in hooks}
    assert action_types == {"webhook", "custom_action"}


async def test_disabled_hooks_not_listed(db_session: AsyncSession) -> None:
    """Disabled hooks are filtered out by default."""
    await create_ref_hook(
        db_session,
        ref_name="world/disabled/HEAD",
        action_type="test_action",
        config={},
        enabled=False,
    )
    await db_session.commit()

    # By default, list only enabled hooks
    hooks = await list_ref_hooks(db_session, "world/disabled/HEAD")
    assert len(hooks) == 0

    # Can include disabled with enabled_only=False
    hooks = await list_ref_hooks(db_session, "world/disabled/HEAD", enabled_only=False)
    assert len(hooks) == 1
    assert hooks[0].enabled is False
