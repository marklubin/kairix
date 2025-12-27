"""Tests for world model branches service."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.db.models import Passage, WorldModelBranch
from kp3.services.branches import (
    BranchError,
    BranchExistsError,
    BranchNotFoundError,
    create_branch,
    delete_branch,
    fork_branch,
    get_branch,
    get_branch_by_name,
    get_branch_for_ref,
    initialize_refs_for_branch,
    list_branches,
    promote_branch,
)
from kp3.services.passages import create_passage
from kp3.services.refs import get_ref, set_ref, should_fire_hooks_for_ref


@pytest.fixture
async def sample_passage(db_session: AsyncSession) -> Passage:
    """Create a sample passage for testing."""
    passage = await create_passage(
        db_session,
        content="Test passage content for branching",
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
        content="Another passage for branch testing",
        passage_type="test",
    )
    await db_session.commit()
    await db_session.refresh(passage)
    return passage


@pytest.fixture
async def third_passage(db_session: AsyncSession) -> Passage:
    """Create a third passage for testing."""
    passage = await create_passage(
        db_session,
        content="Third passage for world model",
        passage_type="test",
    )
    await db_session.commit()
    await db_session.refresh(passage)
    return passage


# =============================================================================
# Branch CRUD Tests
# =============================================================================


async def test_create_branch(db_session: AsyncSession) -> None:
    """Create a new branch."""
    branch = await create_branch(
        db_session,
        ref_prefix="testagent",
        branch_name="experiment-1",
        description="Test experiment",
    )
    await db_session.commit()

    assert branch.name == "testagent/experiment-1"
    assert branch.ref_prefix == "testagent"
    assert branch.branch_name == "experiment-1"
    assert branch.human_ref == "testagent/human/experiment-1"
    assert branch.persona_ref == "testagent/persona/experiment-1"
    assert branch.world_ref == "testagent/world/experiment-1"
    assert branch.is_main is False
    assert branch.hooks_enabled is False
    assert branch.description == "Test experiment"


async def test_create_main_branch(db_session: AsyncSession) -> None:
    """Create a main/production branch."""
    branch = await create_branch(
        db_session,
        ref_prefix="testagent",
        branch_name="HEAD",
        is_main=True,
    )
    await db_session.commit()

    assert branch.name == "testagent/HEAD"
    assert branch.is_main is True
    assert branch.hooks_enabled is True  # Main branches have hooks enabled by default


async def test_create_branch_explicit_hooks(db_session: AsyncSession) -> None:
    """Create a branch with explicit hooks_enabled setting."""
    branch = await create_branch(
        db_session,
        ref_prefix="testagent",
        branch_name="custom",
        hooks_enabled=True,  # Non-main branch with hooks
    )
    await db_session.commit()

    assert branch.is_main is False
    assert branch.hooks_enabled is True


async def test_create_duplicate_branch_fails(db_session: AsyncSession) -> None:
    """Creating a duplicate branch should fail."""
    await create_branch(db_session, ref_prefix="testagent", branch_name="exp-1")
    await db_session.commit()

    with pytest.raises(BranchExistsError) as exc:
        await create_branch(db_session, ref_prefix="testagent", branch_name="exp-1")

    assert "already exists" in str(exc.value)


async def test_get_branch(db_session: AsyncSession) -> None:
    """Get a branch by prefix and name."""
    await create_branch(db_session, ref_prefix="testagent", branch_name="exp-1")
    await db_session.commit()

    branch = await get_branch(db_session, "testagent", "exp-1")
    assert branch is not None
    assert branch.name == "testagent/exp-1"


async def test_get_branch_not_found(db_session: AsyncSession) -> None:
    """Return None for non-existent branch."""
    branch = await get_branch(db_session, "testagent", "nonexistent")
    assert branch is None


async def test_get_branch_by_name(db_session: AsyncSession) -> None:
    """Get a branch by its full name."""
    await create_branch(db_session, ref_prefix="testagent", branch_name="exp-1")
    await db_session.commit()

    branch = await get_branch_by_name(db_session, "testagent/exp-1")
    assert branch is not None
    assert branch.ref_prefix == "testagent"
    assert branch.branch_name == "exp-1"


async def test_list_branches(db_session: AsyncSession) -> None:
    """List all branches."""
    await create_branch(db_session, ref_prefix="agent1", branch_name="HEAD", is_main=True)
    await create_branch(db_session, ref_prefix="agent1", branch_name="exp-1")
    await create_branch(db_session, ref_prefix="agent2", branch_name="HEAD", is_main=True)
    await db_session.commit()

    branches = await list_branches(db_session)
    assert len(branches) == 3

    names = {b.name for b in branches}
    assert names == {"agent1/HEAD", "agent1/exp-1", "agent2/HEAD"}


async def test_list_branches_by_prefix(db_session: AsyncSession) -> None:
    """List branches filtered by prefix."""
    await create_branch(db_session, ref_prefix="agent1", branch_name="HEAD", is_main=True)
    await create_branch(db_session, ref_prefix="agent1", branch_name="exp-1")
    await create_branch(db_session, ref_prefix="agent2", branch_name="HEAD", is_main=True)
    await db_session.commit()

    agent1_branches = await list_branches(db_session, ref_prefix="agent1")
    assert len(agent1_branches) == 2

    agent2_branches = await list_branches(db_session, ref_prefix="agent2")
    assert len(agent2_branches) == 1


async def test_delete_branch(db_session: AsyncSession) -> None:
    """Delete a branch."""
    await create_branch(db_session, ref_prefix="testagent", branch_name="exp-1")
    await db_session.commit()

    deleted = await delete_branch(db_session, "testagent", "exp-1")
    await db_session.commit()

    assert deleted is True
    assert await get_branch(db_session, "testagent", "exp-1") is None


async def test_delete_nonexistent_branch(db_session: AsyncSession) -> None:
    """Deleting a non-existent branch returns False."""
    deleted = await delete_branch(db_session, "testagent", "nonexistent")
    assert deleted is False


async def test_delete_main_branch_fails(db_session: AsyncSession) -> None:
    """Cannot delete a main branch."""
    await create_branch(db_session, ref_prefix="testagent", branch_name="HEAD", is_main=True)
    await db_session.commit()

    with pytest.raises(BranchError) as exc:
        await delete_branch(db_session, "testagent", "HEAD")

    assert "Cannot delete main branch" in str(exc.value)


async def test_delete_branch_with_refs(
    db_session: AsyncSession, sample_passage: Passage, another_passage: Passage, third_passage: Passage
) -> None:
    """Delete a branch and its refs."""
    branch = await create_branch(db_session, ref_prefix="testagent", branch_name="exp-1")
    await db_session.commit()

    # Set up refs
    await initialize_refs_for_branch(
        db_session, branch, sample_passage.id, another_passage.id, third_passage.id
    )
    await db_session.commit()

    # Verify refs exist
    assert await get_ref(db_session, branch.human_ref) is not None
    assert await get_ref(db_session, branch.persona_ref) is not None
    assert await get_ref(db_session, branch.world_ref) is not None

    # Delete with refs
    deleted = await delete_branch(db_session, "testagent", "exp-1", delete_refs=True)
    await db_session.commit()

    assert deleted is True
    assert await get_ref(db_session, "testagent/human/exp-1") is None
    assert await get_ref(db_session, "testagent/persona/exp-1") is None
    assert await get_ref(db_session, "testagent/world/exp-1") is None


# =============================================================================
# Branch Ref Lookup Tests
# =============================================================================


async def test_get_branch_for_ref(db_session: AsyncSession) -> None:
    """Get branch that owns a ref."""
    branch = await create_branch(db_session, ref_prefix="testagent", branch_name="exp-1")
    await db_session.commit()

    # All 3 refs should return the same branch
    for ref_name in [branch.human_ref, branch.persona_ref, branch.world_ref]:
        found = await get_branch_for_ref(db_session, ref_name)
        assert found is not None
        assert found.id == branch.id


async def test_get_branch_for_ref_not_found(db_session: AsyncSession) -> None:
    """Return None for refs not in any branch."""
    branch = await get_branch_for_ref(db_session, "random/untracked/ref")
    assert branch is None


# =============================================================================
# Hook Behavior Tests
# =============================================================================


async def test_should_fire_hooks_for_hookless_branch(db_session: AsyncSession) -> None:
    """Refs in hookless branches should not fire hooks."""
    branch = await create_branch(
        db_session, ref_prefix="testagent", branch_name="exp-1", hooks_enabled=False
    )
    await db_session.commit()

    # Check all 3 refs
    for ref_name in [branch.human_ref, branch.persona_ref, branch.world_ref]:
        should_fire = await should_fire_hooks_for_ref(db_session, ref_name)
        assert should_fire is False


async def test_should_fire_hooks_for_main_branch(db_session: AsyncSession) -> None:
    """Refs in main branches should fire hooks."""
    branch = await create_branch(
        db_session, ref_prefix="testagent", branch_name="HEAD", is_main=True, hooks_enabled=True
    )
    await db_session.commit()

    for ref_name in [branch.human_ref, branch.persona_ref, branch.world_ref]:
        should_fire = await should_fire_hooks_for_ref(db_session, ref_name)
        assert should_fire is True


async def test_should_fire_hooks_for_untracked_ref(db_session: AsyncSession) -> None:
    """Refs not in any branch should fire hooks by default."""
    should_fire = await should_fire_hooks_for_ref(db_session, "untracked/ref")
    assert should_fire is True


# =============================================================================
# Initialize and Fork Tests
# =============================================================================


async def test_initialize_refs_for_branch(
    db_session: AsyncSession, sample_passage: Passage, another_passage: Passage, third_passage: Passage
) -> None:
    """Initialize refs for a branch."""
    branch = await create_branch(db_session, ref_prefix="testagent", branch_name="exp-1")
    await db_session.commit()

    await initialize_refs_for_branch(
        db_session, branch, sample_passage.id, another_passage.id, third_passage.id
    )
    await db_session.commit()

    # Verify refs are set
    assert await get_ref(db_session, branch.human_ref) == sample_passage.id
    assert await get_ref(db_session, branch.persona_ref) == another_passage.id
    assert await get_ref(db_session, branch.world_ref) == third_passage.id


async def test_fork_branch(
    db_session: AsyncSession, sample_passage: Passage, another_passage: Passage, third_passage: Passage
) -> None:
    """Fork a branch, copying its refs."""
    # Create source branch with refs
    source = await create_branch(
        db_session, ref_prefix="testagent", branch_name="HEAD", is_main=True
    )
    await db_session.commit()

    await initialize_refs_for_branch(
        db_session, source, sample_passage.id, another_passage.id, third_passage.id
    )
    await db_session.commit()

    # Fork to new branch
    forked = await fork_branch(
        db_session, "testagent", "HEAD", "exp-1", description="Experiment"
    )
    await db_session.commit()

    # Verify new branch
    assert forked.name == "testagent/exp-1"
    assert forked.parent_branch_id == source.id
    assert forked.hooks_enabled is False  # Forked branches have hooks disabled

    # Verify refs are copied
    assert await get_ref(db_session, forked.human_ref) == sample_passage.id
    assert await get_ref(db_session, forked.persona_ref) == another_passage.id
    assert await get_ref(db_session, forked.world_ref) == third_passage.id


async def test_fork_nonexistent_branch_fails(db_session: AsyncSession) -> None:
    """Forking a non-existent branch should fail."""
    with pytest.raises(BranchNotFoundError):
        await fork_branch(db_session, "testagent", "nonexistent", "exp-1")


# =============================================================================
# Promote Tests
# =============================================================================


async def test_promote_branch(
    db_session: AsyncSession, sample_passage: Passage, another_passage: Passage, third_passage: Passage
) -> None:
    """Promote a branch to HEAD."""
    # Create HEAD branch
    head = await create_branch(
        db_session, ref_prefix="testagent", branch_name="HEAD", is_main=True
    )

    # Create experiment branch with different refs
    exp = await create_branch(
        db_session, ref_prefix="testagent", branch_name="exp-1"
    )
    await db_session.commit()

    # Set up initial HEAD refs (using first passage for all)
    await set_ref(db_session, head.human_ref, sample_passage.id, fire_hooks=False)
    await set_ref(db_session, head.persona_ref, sample_passage.id, fire_hooks=False)
    await set_ref(db_session, head.world_ref, sample_passage.id, fire_hooks=False)

    # Set experiment refs to different passages
    await set_ref(db_session, exp.human_ref, another_passage.id, fire_hooks=False)
    await set_ref(db_session, exp.persona_ref, another_passage.id, fire_hooks=False)
    await set_ref(db_session, exp.world_ref, third_passage.id, fire_hooks=False)
    await db_session.commit()

    # Promote experiment to HEAD
    target = await promote_branch(db_session, "testagent", "exp-1", "HEAD")
    await db_session.commit()

    assert target.name == "testagent/HEAD"

    # HEAD should now have experiment's values
    assert await get_ref(db_session, head.human_ref) == another_passage.id
    assert await get_ref(db_session, head.persona_ref) == another_passage.id
    assert await get_ref(db_session, head.world_ref) == third_passage.id


async def test_promote_nonexistent_source_fails(db_session: AsyncSession) -> None:
    """Promoting a non-existent source branch should fail."""
    # Create target only
    await create_branch(db_session, ref_prefix="testagent", branch_name="HEAD", is_main=True)
    await db_session.commit()

    with pytest.raises(BranchNotFoundError) as exc:
        await promote_branch(db_session, "testagent", "nonexistent", "HEAD")

    assert "Source branch" in str(exc.value)


async def test_promote_nonexistent_target_fails(
    db_session: AsyncSession, sample_passage: Passage
) -> None:
    """Promoting to a non-existent target branch should fail."""
    # Create source only
    source = await create_branch(db_session, ref_prefix="testagent", branch_name="exp-1")
    await set_ref(db_session, source.human_ref, sample_passage.id, fire_hooks=False)
    await db_session.commit()

    with pytest.raises(BranchNotFoundError) as exc:
        await promote_branch(db_session, "testagent", "exp-1", "HEAD")

    assert "Target branch" in str(exc.value)


# =============================================================================
# Integration Tests - set_ref with Branch Hook Logic
# =============================================================================


async def test_set_ref_respects_branch_hooks_disabled(
    db_session: AsyncSession, sample_passage: Passage
) -> None:
    """set_ref should not fire hooks for refs in hookless branches."""
    branch = await create_branch(
        db_session, ref_prefix="testagent", branch_name="exp-1", hooks_enabled=False
    )
    await db_session.commit()

    # Set ref with fire_hooks=True - should still not fire due to branch settings
    # (We can't easily verify hook execution without mocking, but we can verify
    # the should_fire_hooks_for_ref logic)
    should_fire = await should_fire_hooks_for_ref(db_session, branch.human_ref)
    assert should_fire is False

    # Set the ref (no error since no hooks configured)
    await set_ref(db_session, branch.human_ref, sample_passage.id, fire_hooks=True)
    await db_session.commit()

    assert await get_ref(db_session, branch.human_ref) == sample_passage.id


async def test_set_ref_explicit_fire_hooks_false_overrides(
    db_session: AsyncSession, sample_passage: Passage
) -> None:
    """Explicit fire_hooks=False should prevent hooks even for main branches."""
    branch = await create_branch(
        db_session, ref_prefix="testagent", branch_name="HEAD", is_main=True, hooks_enabled=True
    )
    await db_session.commit()

    # Even though branch has hooks_enabled=True, explicit fire_hooks=False wins
    await set_ref(db_session, branch.human_ref, sample_passage.id, fire_hooks=False)
    await db_session.commit()

    assert await get_ref(db_session, branch.human_ref) == sample_passage.id


# =============================================================================
# Parent Branch Lineage Tests
# =============================================================================


async def test_branch_parent_lineage_via_fork(
    db_session: AsyncSession, sample_passage: Passage, another_passage: Passage, third_passage: Passage
) -> None:
    """Fork establishes parent relationship."""
    # Create parent branch
    head = await create_branch(
        db_session, ref_prefix="testagent", branch_name="HEAD", is_main=True
    )
    await db_session.commit()

    # Initialize refs for HEAD
    await initialize_refs_for_branch(
        db_session, head, sample_passage.id, another_passage.id, third_passage.id
    )
    await db_session.commit()

    # Fork creates child with parent
    child = await fork_branch(
        db_session, ref_prefix="testagent", source_branch="HEAD", new_branch_name="exp-1"
    )
    await db_session.commit()

    assert child.parent_branch_id == head.id

    # Refresh to get relationship
    await db_session.refresh(child)
    assert child.parent_branch is not None
    assert child.parent_branch.id == head.id


async def test_create_branch_has_no_parent(db_session: AsyncSession) -> None:
    """Create starts new lineage with no parent."""
    branch = await create_branch(
        db_session, ref_prefix="testagent", branch_name="HEAD", is_main=True
    )
    await db_session.commit()

    assert branch.parent_branch_id is None
