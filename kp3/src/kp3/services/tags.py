"""Tag management service for passages."""

import re
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.db.models import Passage, PassageTag, Tag
from kp3.processors.embedding import generate_embedding


def canonicalize_tag_name(name: str) -> str:
    """Canonicalize a tag name for deduplication.

    - Lowercase
    - Whitespace normalized (single spaces, trimmed)
    """
    normalized = re.sub(r"\s+", " ", name.strip().lower())
    return normalized


async def get_or_create_tag(
    session: AsyncSession,
    name: str,
    agent_id: str,
    description: str | None = None,
) -> Tag:
    """Get an existing tag or create a new one.

    Args:
        session: Database session
        name: Tag display name
        agent_id: Agent ID for scoping
        description: Optional tag description

    Returns:
        The existing or newly created tag
    """
    canonical_key = canonicalize_tag_name(name)

    # Check if tag exists
    result = await session.execute(
        select(Tag).where(Tag.agent_id == agent_id, Tag.canonical_key == canonical_key)
    )
    existing = result.scalar_one_or_none()

    if existing:
        return existing

    # Generate embedding for the tag name and description
    embed_text = name if description is None else f"{name}: {description}"
    embedding = await generate_embedding(embed_text)

    tag = Tag(
        agent_id=agent_id,
        canonical_key=canonical_key,
        name=name,
        description=description,
        embedding_openai=embedding,
    )
    session.add(tag)
    await session.flush()
    return tag


async def create_tag(
    session: AsyncSession,
    name: str,
    agent_id: str,
    description: str | None = None,
) -> Tag:
    """Create a new tag.

    Args:
        session: Database session
        name: Tag display name
        agent_id: Agent ID for scoping
        description: Optional tag description

    Returns:
        The newly created tag

    Raises:
        ValueError: If tag with same canonical name already exists
    """
    canonical_key = canonicalize_tag_name(name)

    # Check if tag exists
    result = await session.execute(
        select(Tag).where(Tag.agent_id == agent_id, Tag.canonical_key == canonical_key)
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise ValueError(f"Tag with name '{name}' already exists (canonical: {canonical_key})")

    # Generate embedding for the tag name and description
    embed_text = name if description is None else f"{name}: {description}"
    embedding = await generate_embedding(embed_text)

    tag = Tag(
        agent_id=agent_id,
        canonical_key=canonical_key,
        name=name,
        description=description,
        embedding_openai=embedding,
    )
    session.add(tag)
    await session.flush()
    return tag


async def get_tag(
    session: AsyncSession,
    tag_id: UUID,
    agent_id: str,
) -> Tag | None:
    """Get a tag by ID.

    Args:
        session: Database session
        tag_id: Tag UUID
        agent_id: Agent ID for scoping

    Returns:
        Tag if found, None otherwise
    """
    result = await session.execute(select(Tag).where(Tag.id == tag_id, Tag.agent_id == agent_id))
    return result.scalar_one_or_none()


async def get_tag_by_name(
    session: AsyncSession,
    name: str,
    agent_id: str,
) -> Tag | None:
    """Get a tag by name (canonical match).

    Args:
        session: Database session
        name: Tag name to search for
        agent_id: Agent ID for scoping

    Returns:
        Tag if found, None otherwise
    """
    canonical_key = canonicalize_tag_name(name)
    result = await session.execute(
        select(Tag).where(Tag.agent_id == agent_id, Tag.canonical_key == canonical_key)
    )
    return result.scalar_one_or_none()


async def list_tags(
    session: AsyncSession,
    agent_id: str,
    *,
    limit: int = 100,
    offset: int = 0,
    order_by: str = "name",
) -> list[Tag]:
    """List tags for an agent.

    Args:
        session: Database session
        agent_id: Agent ID for scoping
        limit: Maximum number of results
        offset: Offset for pagination
        order_by: Order by field (name, created_at, passage_count)

    Returns:
        List of tags
    """
    # Primary and secondary sort columns for stable ordering
    order_columns = {
        "name": (Tag.name, Tag.id),
        "created_at": (Tag.created_at.desc(), Tag.id.desc()),
        "passage_count": (Tag.passage_count.desc(), Tag.id),
    }.get(order_by, (Tag.name, Tag.id))

    stmt = (
        select(Tag)
        .where(Tag.agent_id == agent_id)
        .order_by(*order_columns)
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_tag(
    session: AsyncSession,
    tag_id: UUID,
    agent_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
) -> Tag | None:
    """Update a tag's name and/or description.

    Regenerates the embedding if name or description changes.

    Args:
        session: Database session
        tag_id: Tag UUID
        agent_id: Agent ID for scoping
        name: New name (optional)
        description: New description (optional)

    Returns:
        Updated tag if found, None otherwise
    """
    tag = await get_tag(session, tag_id, agent_id)
    if not tag:
        return None

    if name is not None:
        tag.canonical_key = canonicalize_tag_name(name)
        tag.name = name

    if description is not None:
        tag.description = description

    # Regenerate embedding if name or description changed
    if name is not None or description is not None:
        embed_text = tag.name if tag.description is None else f"{tag.name}: {tag.description}"
        tag.embedding_openai = await generate_embedding(embed_text)

    await session.flush()
    return tag


async def delete_tag(
    session: AsyncSession,
    tag_id: UUID,
    agent_id: str,
) -> bool:
    """Delete a tag.

    This will cascade delete all passage_tags entries.

    Args:
        session: Database session
        tag_id: Tag UUID
        agent_id: Agent ID for scoping

    Returns:
        True if tag was deleted, False if not found
    """
    stmt = delete(Tag).where(Tag.id == tag_id, Tag.agent_id == agent_id).returning(Tag.id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def attach_tag_to_passage(
    session: AsyncSession,
    passage_id: UUID,
    tag_id: UUID,
    agent_id: str,
) -> bool:
    """Attach a tag to a passage.

    Args:
        session: Database session
        passage_id: Passage UUID
        tag_id: Tag UUID
        agent_id: Agent ID for scoping

    Returns:
        True if attached, False if already attached or invalid IDs
    """
    # Verify passage and tag exist and belong to agent
    passage_result = await session.execute(
        select(Passage).where(Passage.id == passage_id, Passage.agent_id == agent_id)
    )
    if not passage_result.scalar_one_or_none():
        return False

    tag_result = await session.execute(
        select(Tag).where(Tag.id == tag_id, Tag.agent_id == agent_id)
    )
    if not tag_result.scalar_one_or_none():
        return False

    # Check if already attached
    existing = await session.execute(
        select(PassageTag).where(PassageTag.passage_id == passage_id, PassageTag.tag_id == tag_id)
    )
    if existing.scalar_one_or_none():
        return False

    # Create link
    link = PassageTag(passage_id=passage_id, tag_id=tag_id)
    session.add(link)

    # Update passage_count
    await session.execute(
        update(Tag).where(Tag.id == tag_id).values(passage_count=Tag.passage_count + 1)
    )

    await session.flush()
    return True


async def detach_tag_from_passage(
    session: AsyncSession,
    passage_id: UUID,
    tag_id: UUID,
    agent_id: str,
) -> bool:
    """Detach a tag from a passage.

    Args:
        session: Database session
        passage_id: Passage UUID
        tag_id: Tag UUID
        agent_id: Agent ID for scoping

    Returns:
        True if detached, False if not found
    """
    # Verify tag belongs to agent
    tag_result = await session.execute(
        select(Tag).where(Tag.id == tag_id, Tag.agent_id == agent_id)
    )
    if not tag_result.scalar_one_or_none():
        return False

    stmt = (
        delete(PassageTag)
        .where(PassageTag.passage_id == passage_id, PassageTag.tag_id == tag_id)
        .returning(PassageTag.tag_id)
    )
    result = await session.execute(stmt)
    deleted_tag_id = result.scalar_one_or_none()

    if deleted_tag_id is not None:
        # Update passage_count
        await session.execute(
            update(Tag).where(Tag.id == tag_id).values(passage_count=Tag.passage_count - 1)
        )
        await session.flush()
        return True

    return False


async def get_passage_tags(
    session: AsyncSession,
    passage_id: UUID,
    agent_id: str,
) -> list[Tag]:
    """Get all tags attached to a passage.

    Args:
        session: Database session
        passage_id: Passage UUID
        agent_id: Agent ID for scoping

    Returns:
        List of tags
    """
    result = await session.execute(
        select(Tag)
        .join(PassageTag, PassageTag.tag_id == Tag.id)
        .where(PassageTag.passage_id == passage_id, Tag.agent_id == agent_id)
        .order_by(Tag.name)
    )
    return list(result.scalars().all())


async def get_passages_by_tag(
    session: AsyncSession,
    tag_id: UUID,
    agent_id: str,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[Passage]:
    """Get all passages with a specific tag.

    Args:
        session: Database session
        tag_id: Tag UUID
        agent_id: Agent ID for scoping
        limit: Maximum number of results
        offset: Offset for pagination

    Returns:
        List of passages
    """
    result = await session.execute(
        select(Passage)
        .join(PassageTag, PassageTag.passage_id == Passage.id)
        .where(PassageTag.tag_id == tag_id, Passage.agent_id == agent_id)
        .order_by(Passage.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def attach_tags_to_passage(
    session: AsyncSession,
    passage_id: UUID,
    tag_ids: list[UUID],
    agent_id: str,
) -> int:
    """Attach multiple tags to a passage.

    Args:
        session: Database session
        passage_id: Passage UUID
        tag_ids: List of tag UUIDs to attach
        agent_id: Agent ID for scoping

    Returns:
        Number of tags attached
    """
    count = 0
    for tag_id in tag_ids:
        if await attach_tag_to_passage(session, passage_id, tag_id, agent_id):
            count += 1
    return count


async def detach_tags_from_passage(
    session: AsyncSession,
    passage_id: UUID,
    tag_ids: list[UUID],
    agent_id: str,
) -> int:
    """Detach multiple tags from a passage.

    Args:
        session: Database session
        passage_id: Passage UUID
        tag_ids: List of tag UUIDs to detach
        agent_id: Agent ID for scoping

    Returns:
        Number of tags detached
    """
    count = 0
    for tag_id in tag_ids:
        if await detach_tag_from_passage(session, passage_id, tag_id, agent_id):
            count += 1
    return count


async def count_tags(
    session: AsyncSession,
    agent_id: str,
) -> int:
    """Count total tags for an agent.

    Args:
        session: Database session
        agent_id: Agent ID for scoping

    Returns:
        Total number of tags
    """
    result = await session.execute(
        select(func.count()).select_from(Tag).where(Tag.agent_id == agent_id)
    )
    return result.scalar_one()
