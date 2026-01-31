"""Memory Scopes service for managing dynamic search closures.

Scopes define a closure of passage IDs via refs and literal IDs.
Scope definitions are stored as passages (type="scope_definition"),
leveraging existing passage infrastructure for versioning via refs.
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.db.models import MemoryScope, Passage
from kp3.schemas.scope import ScopeDefinition
from kp3.services.passages import create_passage
from kp3.services.refs import delete_ref, get_ref, get_ref_history, get_ref_passage, set_ref

logger = logging.getLogger(__name__)

SCOPE_DEFINITION_TYPE = "scope_definition"


# =============================================================================
# Scope CRUD
# =============================================================================


async def create_scope(
    session: AsyncSession,
    name: str,
    agent_id: str,
    *,
    description: str | None = None,
) -> MemoryScope:
    """Create a new memory scope.

    Creates the scope record and initializes it with an empty definition passage
    pointed to by the head ref.

    Args:
        session: Database session
        name: Scope name (unique per agent)
        agent_id: Agent ID for scoping
        description: Optional description

    Returns:
        The created MemoryScope

    Raises:
        ValueError: If a scope with this name already exists for the agent
    """
    # Check for existing scope
    existing = await get_scope(session, name, agent_id)
    if existing is not None:
        raise ValueError(f"Scope '{name}' already exists for agent '{agent_id}'")

    # Generate ref name: agent_id/scope/name/HEAD
    head_ref = f"{agent_id}/scope/{name}/HEAD"

    # Create initial empty scope definition
    initial_def = ScopeDefinition(refs=[], passages=[], version=1, created_from=None)
    def_passage = await create_passage(
        session,
        content=initial_def.model_dump_json(),
        passage_type=SCOPE_DEFINITION_TYPE,
        agent_id=agent_id,
    )

    # Create head ref pointing to definition
    await set_ref(session, head_ref, def_passage.id, fire_hooks=False)

    # Create scope record
    scope = MemoryScope(
        agent_id=agent_id,
        name=name,
        head_ref=head_ref,
        description=description,
    )
    session.add(scope)
    await session.flush()

    logger.info("Created scope '%s' for agent '%s' with head_ref '%s'", name, agent_id, head_ref)
    return scope


async def get_scope(
    session: AsyncSession,
    name: str,
    agent_id: str,
) -> MemoryScope | None:
    """Get a scope by name and agent ID.

    Args:
        session: Database session
        name: Scope name
        agent_id: Agent ID

    Returns:
        MemoryScope if found, None otherwise
    """
    stmt = select(MemoryScope).where(
        MemoryScope.name == name,
        MemoryScope.agent_id == agent_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_scope_by_id(
    session: AsyncSession,
    scope_id: UUID,
    agent_id: str,
) -> MemoryScope | None:
    """Get a scope by ID, verifying agent ownership.

    Args:
        session: Database session
        scope_id: Scope UUID
        agent_id: Agent ID (for ownership verification)

    Returns:
        MemoryScope if found and owned by agent, None otherwise
    """
    stmt = select(MemoryScope).where(
        MemoryScope.id == scope_id,
        MemoryScope.agent_id == agent_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_scopes(
    session: AsyncSession,
    agent_id: str,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[MemoryScope]:
    """List all scopes for an agent.

    Args:
        session: Database session
        agent_id: Agent ID
        limit: Maximum number of results
        offset: Pagination offset

    Returns:
        List of MemoryScope objects
    """
    stmt = (
        select(MemoryScope)
        .where(MemoryScope.agent_id == agent_id)
        .order_by(MemoryScope.name)
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def delete_scope(
    session: AsyncSession,
    name: str,
    agent_id: str,
) -> bool:
    """Delete a scope.

    Note: This does not delete the scope definition passages or ref history,
    as those may be useful for auditing.

    Args:
        session: Database session
        name: Scope name
        agent_id: Agent ID

    Returns:
        True if scope was deleted, False if not found
    """
    scope = await get_scope(session, name, agent_id)
    if scope is None:
        return False

    # Delete the head ref
    await delete_ref(session, scope.head_ref)

    # Delete the scope record
    stmt = delete(MemoryScope).where(
        MemoryScope.name == name,
        MemoryScope.agent_id == agent_id,
    )
    await session.execute(stmt)
    await session.flush()

    logger.info("Deleted scope '%s' for agent '%s'", name, agent_id)
    return True


# =============================================================================
# Scope Definition Helpers
# =============================================================================


async def _get_current_definition(
    session: AsyncSession,
    scope: MemoryScope,
) -> tuple[ScopeDefinition, Passage]:
    """Get the current scope definition and its passage.

    Args:
        session: Database session
        scope: The scope to get definition for

    Returns:
        Tuple of (ScopeDefinition, definition Passage)

    Raises:
        ValueError: If the head ref or definition passage is missing
    """
    def_passage = await get_ref_passage(session, scope.head_ref)
    if def_passage is None:
        raise ValueError(f"Scope '{scope.name}' has missing head ref '{scope.head_ref}'")

    scope_def = ScopeDefinition.model_validate_json(def_passage.content)
    return scope_def, def_passage


async def _update_scope_definition(
    session: AsyncSession,
    scope: MemoryScope,
    new_def: ScopeDefinition,
    previous_def_id: UUID,
) -> int:
    """Create a new definition passage and update the head ref.

    Args:
        session: Database session
        scope: The scope to update
        new_def: The new scope definition
        previous_def_id: ID of the previous definition passage

    Returns:
        The new version number
    """
    # Create new definition passage
    def_passage = await create_passage(
        session,
        content=new_def.model_dump_json(),
        passage_type=SCOPE_DEFINITION_TYPE,
        agent_id=scope.agent_id,
    )

    # Update head ref (this records history)
    await set_ref(session, scope.head_ref, def_passage.id, fire_hooks=False)

    # Update scope timestamp
    scope.updated_at = datetime.now(UTC)
    await session.flush()

    logger.debug("Updated scope '%s' to version %d", scope.name, new_def.version)
    return new_def.version


# =============================================================================
# Resolution
# =============================================================================


async def resolve_scope(
    session: AsyncSession,
    scope: MemoryScope,
) -> set[UUID]:
    """Resolve a scope definition to a set of passage IDs.

    Resolves both literal passage IDs and refs to their current targets.

    Args:
        session: Database session
        scope: The scope to resolve

    Returns:
        Set of passage UUIDs that are currently in the scope
    """
    def_passage = await get_ref_passage(session, scope.head_ref)
    if def_passage is None:
        return set()

    scope_def = ScopeDefinition.model_validate_json(def_passage.content)
    result: set[UUID] = set()

    # Add literal passages (verify they exist)
    for passage_id in scope_def.passages:
        passage = await session.get(Passage, passage_id)
        if passage is not None:
            result.add(passage_id)

    # Resolve refs to current passage IDs
    for ref_name in scope_def.refs:
        passage_id = await get_ref(session, ref_name)
        if passage_id is not None:
            result.add(passage_id)

    return result


async def get_current_version(
    session: AsyncSession,
    scope: MemoryScope,
) -> int:
    """Get the current version number of a scope.

    Args:
        session: Database session
        scope: The scope

    Returns:
        Current version number
    """
    scope_def, _ = await _get_current_definition(session, scope)
    return scope_def.version


# =============================================================================
# Scoped Operations
# =============================================================================


async def create_passage_in_scope(
    session: AsyncSession,
    scope: MemoryScope,
    content: str,
    passage_type: str,
    *,
    metadata: dict[str, Any] | None = None,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    embedding_openai: list[float] | None = None,
) -> tuple[Passage, int]:
    """Create a passage and add it to the scope atomically.

    Args:
        session: Database session
        scope: The scope to add the passage to
        content: Passage content
        passage_type: Passage type
        metadata: Optional metadata
        period_start: Optional period start
        period_end: Optional period end
        embedding_openai: Optional pre-computed embedding

    Returns:
        Tuple of (created Passage, new scope version)
    """
    # Create the passage
    passage = await create_passage(
        session,
        content=content,
        passage_type=passage_type,
        metadata=metadata,
        period_start=period_start,
        period_end=period_end,
        embedding_openai=embedding_openai,
        agent_id=scope.agent_id,
    )

    # Get current definition
    current_def, def_passage = await _get_current_definition(session, scope)

    # Create new definition with passage added
    new_passages = list(current_def.passages)
    if passage.id not in new_passages:
        new_passages.append(passage.id)

    new_def = ScopeDefinition(
        refs=current_def.refs,
        passages=new_passages,
        version=current_def.version + 1,
        created_from=def_passage.id,
    )

    # Update scope
    new_version = await _update_scope_definition(session, scope, new_def, def_passage.id)

    logger.info(
        "Created passage %s in scope '%s', version now %d",
        passage.id,
        scope.name,
        new_version,
    )
    return passage, new_version


async def add_passages_to_scope(
    session: AsyncSession,
    scope: MemoryScope,
    passage_ids: list[UUID],
) -> tuple[int, int]:
    """Add existing passages to a scope.

    Args:
        session: Database session
        scope: The scope to add to
        passage_ids: Passage IDs to add

    Returns:
        Tuple of (new version, count of passages actually added)
    """
    if not passage_ids:
        current_def, _ = await _get_current_definition(session, scope)
        return current_def.version, 0

    # Get current definition
    current_def, def_passage = await _get_current_definition(session, scope)

    # Add passages that don't already exist (and verify they exist in DB)
    existing_set = set(current_def.passages)
    added_count = 0
    new_passages = list(current_def.passages)

    for pid in passage_ids:
        if pid not in existing_set:
            # Verify passage exists
            passage = await session.get(Passage, pid)
            if passage is not None:
                new_passages.append(pid)
                existing_set.add(pid)
                added_count += 1

    if added_count == 0:
        return current_def.version, 0

    new_def = ScopeDefinition(
        refs=current_def.refs,
        passages=new_passages,
        version=current_def.version + 1,
        created_from=def_passage.id,
    )

    new_version = await _update_scope_definition(session, scope, new_def, def_passage.id)

    logger.info(
        "Added %d passages to scope '%s', version now %d",
        added_count,
        scope.name,
        new_version,
    )
    return new_version, added_count


async def add_refs_to_scope(
    session: AsyncSession,
    scope: MemoryScope,
    ref_names: list[str],
) -> tuple[int, int]:
    """Add refs to a scope.

    Refs are resolved at search time, so we don't verify they exist here.

    Args:
        session: Database session
        scope: The scope to add to
        ref_names: Ref names to add

    Returns:
        Tuple of (new version, count of refs actually added)
    """
    if not ref_names:
        current_def, _ = await _get_current_definition(session, scope)
        return current_def.version, 0

    # Get current definition
    current_def, def_passage = await _get_current_definition(session, scope)

    # Add refs that don't already exist
    existing_set = set(current_def.refs)
    added_count = 0
    new_refs = list(current_def.refs)

    for ref_name in ref_names:
        if ref_name not in existing_set:
            new_refs.append(ref_name)
            existing_set.add(ref_name)
            added_count += 1

    if added_count == 0:
        return current_def.version, 0

    new_def = ScopeDefinition(
        refs=new_refs,
        passages=current_def.passages,
        version=current_def.version + 1,
        created_from=def_passage.id,
    )

    new_version = await _update_scope_definition(session, scope, new_def, def_passage.id)

    logger.info(
        "Added %d refs to scope '%s', version now %d",
        added_count,
        scope.name,
        new_version,
    )
    return new_version, added_count


async def remove_from_scope(
    session: AsyncSession,
    scope: MemoryScope,
    *,
    passage_ids: list[UUID] | None = None,
    refs: list[str] | None = None,
) -> tuple[int, int]:
    """Remove passages and/or refs from a scope.

    Args:
        session: Database session
        scope: The scope to remove from
        passage_ids: Optional list of passage IDs to remove
        refs: Optional list of ref names to remove

    Returns:
        Tuple of (new version, total count removed)
    """
    passage_ids = passage_ids or []
    refs = refs or []

    if not passage_ids and not refs:
        current_def, _ = await _get_current_definition(session, scope)
        return current_def.version, 0

    # Get current definition
    current_def, def_passage = await _get_current_definition(session, scope)

    # Remove passages
    passage_set_to_remove = set(passage_ids)
    new_passages = [p for p in current_def.passages if p not in passage_set_to_remove]
    passages_removed = len(current_def.passages) - len(new_passages)

    # Remove refs
    ref_set_to_remove = set(refs)
    new_refs = [r for r in current_def.refs if r not in ref_set_to_remove]
    refs_removed = len(current_def.refs) - len(new_refs)

    total_removed = passages_removed + refs_removed

    if total_removed == 0:
        return current_def.version, 0

    new_def = ScopeDefinition(
        refs=new_refs,
        passages=new_passages,
        version=current_def.version + 1,
        created_from=def_passage.id,
    )

    new_version = await _update_scope_definition(session, scope, new_def, def_passage.id)

    logger.info(
        "Removed %d items from scope '%s', version now %d",
        total_removed,
        scope.name,
        new_version,
    )
    return new_version, total_removed


# =============================================================================
# History & Revert
# =============================================================================


async def get_scope_history(
    session: AsyncSession,
    scope: MemoryScope,
    *,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Get the history of scope changes.

    Args:
        session: Database session
        scope: The scope to get history for
        limit: Maximum number of entries to return

    Returns:
        List of history entries with version, changed_at, passage_id
    """
    # Get ref history
    history_entries = await get_ref_history(session, scope.head_ref, limit=limit)

    result: list[dict[str, Any]] = []
    for entry in history_entries:
        # Parse the definition to get version
        def_passage = await session.get(Passage, entry["passage_id"])
        if def_passage is not None:
            scope_def = ScopeDefinition.model_validate_json(def_passage.content)
            result.append(
                {
                    "version": scope_def.version,
                    "changed_at": entry["changed_at"],
                    "passage_id": entry["passage_id"],
                }
            )

    return result


async def revert_scope(
    session: AsyncSession,
    scope: MemoryScope,
    to_version: int,
) -> tuple[int, int]:
    """Revert a scope to a previous version.

    This creates a new version that contains the same definition as the target version.

    Args:
        session: Database session
        scope: The scope to revert
        to_version: The version number to revert to

    Returns:
        Tuple of (new version number, version reverted from)

    Raises:
        ValueError: If the target version is not found in history
    """
    # Get current version
    current_def, current_def_passage = await _get_current_definition(session, scope)
    current_version = current_def.version

    if to_version >= current_version:
        raise ValueError(f"Cannot revert to version {to_version} (current is {current_version})")

    # Get history and find target version
    history = await get_scope_history(session, scope, limit=1000)

    target_entry = None
    for entry in history:
        if entry["version"] == to_version:
            target_entry = entry
            break

    if target_entry is None:
        raise ValueError(f"Version {to_version} not found in scope history")

    # Get the target definition
    target_passage = await session.get(Passage, target_entry["passage_id"])
    if target_passage is None:
        raise ValueError(f"Definition passage for version {to_version} not found")

    target_def = ScopeDefinition.model_validate_json(target_passage.content)

    # Create new definition with same content but new version
    new_def = ScopeDefinition(
        refs=target_def.refs,
        passages=target_def.passages,
        version=current_version + 1,
        created_from=current_def_passage.id,
    )

    new_version = await _update_scope_definition(session, scope, new_def, current_def_passage.id)

    logger.info(
        "Reverted scope '%s' from version %d to version %d (new version %d)",
        scope.name,
        current_version,
        to_version,
        new_version,
    )
    return new_version, current_version
