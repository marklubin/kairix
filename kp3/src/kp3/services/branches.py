"""World model branches service.

Branches group the 3 world model refs (human/persona/world) as a unit.
They enable running fold operations without firing hooks on production agents.
"""

import logging
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.db.models import WorldModelBranch

logger = logging.getLogger(__name__)


class BranchError(Exception):
    """Error during branch operations."""

    pass


class BranchNotFoundError(BranchError):
    """Branch not found."""

    pass


class BranchExistsError(BranchError):
    """Branch already exists."""

    pass


def _build_ref_names(ref_prefix: str, branch_name: str) -> tuple[str, str, str]:
    """Build the 3 ref names for a branch.

    Returns:
        Tuple of (human_ref, persona_ref, world_ref)
    """
    return (
        f"{ref_prefix}/human/{branch_name}",
        f"{ref_prefix}/persona/{branch_name}",
        f"{ref_prefix}/world/{branch_name}",
    )


async def create_branch(
    session: AsyncSession,
    ref_prefix: str,
    branch_name: str,
    *,
    description: str | None = None,
    is_main: bool = False,
    hooks_enabled: bool | None = None,
) -> WorldModelBranch:
    """Create a new world model branch (new lineage, empty refs).

    Use fork_branch() to derive from an existing branch with copied refs.

    Args:
        session: Database session
        ref_prefix: The agent/entity prefix (e.g., "corindel")
        branch_name: The branch name (e.g., "experiment-1" or "HEAD")
        description: Optional description for the branch
        is_main: Whether this is the main/production branch
        hooks_enabled: Whether hooks are enabled. Defaults to True for main, False otherwise.

    Returns:
        The created WorldModelBranch

    Raises:
        BranchExistsError: If a branch with this name already exists
    """
    # Check if branch already exists
    existing = await get_branch(session, ref_prefix, branch_name)
    if existing:
        raise BranchExistsError(f"Branch '{ref_prefix}/{branch_name}' already exists")

    # Build ref names
    human_ref, persona_ref, world_ref = _build_ref_names(ref_prefix, branch_name)

    # Determine hooks_enabled default
    if hooks_enabled is None:
        hooks_enabled = is_main

    branch = WorldModelBranch(
        name=f"{ref_prefix}/{branch_name}",
        ref_prefix=ref_prefix,
        branch_name=branch_name,
        human_ref=human_ref,
        persona_ref=persona_ref,
        world_ref=world_ref,
        parent_branch_id=None,  # New lineage, no parent
        is_main=is_main,
        hooks_enabled=hooks_enabled,
        description=description,
    )
    session.add(branch)
    await session.flush()

    logger.info("Created branch %s (hooks_enabled=%s)", branch.name, branch.hooks_enabled)
    return branch


async def get_branch(
    session: AsyncSession,
    ref_prefix: str,
    branch_name: str,
) -> WorldModelBranch | None:
    """Get a branch by prefix and name.

    Args:
        session: Database session
        ref_prefix: The agent/entity prefix (e.g., "corindel")
        branch_name: The branch name (e.g., "experiment-1")

    Returns:
        WorldModelBranch if found, None otherwise
    """
    stmt = select(WorldModelBranch).where(
        WorldModelBranch.ref_prefix == ref_prefix,
        WorldModelBranch.branch_name == branch_name,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_branch_by_name(
    session: AsyncSession,
    full_name: str,
) -> WorldModelBranch | None:
    """Get a branch by its full name (e.g., "corindel/experiment-1").

    Args:
        session: Database session
        full_name: Full branch name

    Returns:
        WorldModelBranch if found, None otherwise
    """
    stmt = select(WorldModelBranch).where(WorldModelBranch.name == full_name)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_branch_for_ref(
    session: AsyncSession,
    ref_name: str,
) -> WorldModelBranch | None:
    """Get the branch that owns a specific ref.

    Args:
        session: Database session
        ref_name: The ref name (e.g., "corindel/human/experiment-1")

    Returns:
        WorldModelBranch if the ref belongs to a branch, None otherwise
    """
    stmt = select(WorldModelBranch).where(
        (WorldModelBranch.human_ref == ref_name)
        | (WorldModelBranch.persona_ref == ref_name)
        | (WorldModelBranch.world_ref == ref_name)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_branches(
    session: AsyncSession,
    *,
    ref_prefix: str | None = None,
    limit: int = 100,
) -> list[WorldModelBranch]:
    """List branches, optionally filtered by prefix.

    Args:
        session: Database session
        ref_prefix: Optional prefix to filter by
        limit: Maximum number of branches to return

    Returns:
        List of WorldModelBranch objects
    """
    stmt = select(WorldModelBranch).order_by(WorldModelBranch.name).limit(limit)

    if ref_prefix:
        stmt = stmt.where(WorldModelBranch.ref_prefix == ref_prefix)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def promote_branch(
    session: AsyncSession,
    ref_prefix: str,
    source_branch: str,
    target_branch: str = "HEAD",
) -> WorldModelBranch:
    """Promote a branch to another branch (typically HEAD).

    This copies the current passage IDs from the source branch refs to the
    target branch refs, firing hooks on the target refs.

    Args:
        session: Database session
        ref_prefix: The agent/entity prefix (e.g., "corindel")
        source_branch: Source branch name (e.g., "experiment-1")
        target_branch: Target branch name (default "HEAD")

    Returns:
        The target branch

    Raises:
        BranchNotFoundError: If either branch doesn't exist
    """
    from kp3.services.refs import get_ref, set_ref

    # Get both branches
    source = await get_branch(session, ref_prefix, source_branch)
    if not source:
        raise BranchNotFoundError(f"Source branch '{ref_prefix}/{source_branch}' not found")

    target = await get_branch(session, ref_prefix, target_branch)
    if not target:
        raise BranchNotFoundError(f"Target branch '{ref_prefix}/{target_branch}' not found")

    # Get current passage IDs from source refs
    human_passage_id = await get_ref(session, source.human_ref)
    persona_passage_id = await get_ref(session, source.persona_ref)
    world_passage_id = await get_ref(session, source.world_ref)

    # Set target refs with hooks enabled (if target has hooks_enabled)
    fire_hooks = target.hooks_enabled

    if human_passage_id:
        await set_ref(session, target.human_ref, human_passage_id, fire_hooks=fire_hooks)
        logger.info("Promoted %s → %s", source.human_ref, target.human_ref)

    if persona_passage_id:
        await set_ref(session, target.persona_ref, persona_passage_id, fire_hooks=fire_hooks)
        logger.info("Promoted %s → %s", source.persona_ref, target.persona_ref)

    if world_passage_id:
        await set_ref(session, target.world_ref, world_passage_id, fire_hooks=fire_hooks)
        logger.info("Promoted %s → %s", source.world_ref, target.world_ref)

    logger.info(
        "Promoted branch %s → %s (hooks_fired=%s)",
        source.name,
        target.name,
        fire_hooks,
    )
    return target


async def delete_branch(
    session: AsyncSession,
    ref_prefix: str,
    branch_name: str,
    *,
    delete_refs: bool = False,
) -> bool:
    """Delete a branch.

    Args:
        session: Database session
        ref_prefix: The agent/entity prefix
        branch_name: The branch name
        delete_refs: Whether to also delete the underlying refs (default False)

    Returns:
        True if the branch existed and was deleted, False otherwise

    Raises:
        BranchError: If trying to delete a main branch
    """
    branch = await get_branch(session, ref_prefix, branch_name)
    if not branch:
        return False

    if branch.is_main:
        raise BranchError(f"Cannot delete main branch '{branch.name}'")

    # Optionally delete the underlying refs
    if delete_refs:
        from kp3.services.refs import delete_ref

        await delete_ref(session, branch.human_ref)
        await delete_ref(session, branch.persona_ref)
        await delete_ref(session, branch.world_ref)
        logger.info("Deleted refs for branch %s", branch.name)

    # Delete the branch record
    stmt = delete(WorldModelBranch).where(WorldModelBranch.id == branch.id)
    await session.execute(stmt)
    await session.flush()

    logger.info("Deleted branch %s", branch.name)
    return True


async def initialize_refs_for_branch(
    session: AsyncSession,
    branch: WorldModelBranch,
    human_passage_id: UUID,
    persona_passage_id: UUID,
    world_passage_id: UUID,
) -> None:
    """Initialize refs for a branch with the given passage IDs.

    This sets the refs without firing hooks (useful for branch creation/forking).

    Args:
        session: Database session
        branch: The branch to initialize
        human_passage_id: Passage ID for human ref
        persona_passage_id: Passage ID for persona ref
        world_passage_id: Passage ID for world ref
    """
    from kp3.services.refs import set_ref

    await set_ref(session, branch.human_ref, human_passage_id, fire_hooks=False)
    await set_ref(session, branch.persona_ref, persona_passage_id, fire_hooks=False)
    await set_ref(session, branch.world_ref, world_passage_id, fire_hooks=False)

    logger.info("Initialized refs for branch %s", branch.name)


async def fork_branch(
    session: AsyncSession,
    ref_prefix: str,
    source_branch: str,
    new_branch_name: str,
    *,
    description: str | None = None,
) -> WorldModelBranch:
    """Fork a branch, copying its current refs to a new branch.

    Args:
        session: Database session
        ref_prefix: The agent/entity prefix
        source_branch: Source branch to fork from
        new_branch_name: Name for the new branch
        description: Optional description

    Returns:
        The newly created branch

    Raises:
        BranchNotFoundError: If source branch doesn't exist
        BranchExistsError: If new branch already exists
    """
    from kp3.services.refs import get_ref

    # Get source branch
    source = await get_branch(session, ref_prefix, source_branch)
    if not source:
        raise BranchNotFoundError(f"Source branch '{ref_prefix}/{source_branch}' not found")

    # Create new branch (starts as new lineage)
    new_branch = await create_branch(
        session,
        ref_prefix,
        new_branch_name,
        description=description,
        is_main=False,
        hooks_enabled=False,
    )

    # Set parent to establish lineage from fork
    new_branch.parent_branch_id = source.id
    await session.flush()

    # Copy refs from source
    human_id = await get_ref(session, source.human_ref)
    persona_id = await get_ref(session, source.persona_ref)
    world_id = await get_ref(session, source.world_ref)

    if human_id and persona_id and world_id:
        await initialize_refs_for_branch(session, new_branch, human_id, persona_id, world_id)
    else:
        logger.warning(
            "Source branch %s has missing refs, new branch %s created without refs",
            source.name,
            new_branch.name,
        )

    return new_branch
