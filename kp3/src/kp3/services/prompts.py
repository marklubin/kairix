"""Prompts service for managing extraction prompts."""

from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.db.models import ExtractionPrompt


async def get_active_prompt(session: AsyncSession, name: str) -> ExtractionPrompt | None:
    """Get the active prompt for a given name.

    Args:
        session: Database session
        name: Prompt name (e.g., "world_model")

    Returns:
        The active ExtractionPrompt if one exists, None otherwise
    """
    stmt = select(ExtractionPrompt).where(
        ExtractionPrompt.name == name,
        ExtractionPrompt.is_active == True,  # noqa: E712
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_prompt(session: AsyncSession, prompt_id: UUID) -> ExtractionPrompt | None:
    """Get a prompt by ID.

    Args:
        session: Database session
        prompt_id: UUID of the prompt

    Returns:
        ExtractionPrompt if found, None otherwise
    """
    return await session.get(ExtractionPrompt, prompt_id)


async def get_prompt_by_version(
    session: AsyncSession, name: str, version: int
) -> ExtractionPrompt | None:
    """Get a specific version of a prompt.

    Args:
        session: Database session
        name: Prompt name
        version: Version number

    Returns:
        ExtractionPrompt if found, None otherwise
    """
    stmt = select(ExtractionPrompt).where(
        ExtractionPrompt.name == name,
        ExtractionPrompt.version == version,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_prompt(
    session: AsyncSession,
    name: str,
    version: int,
    system_prompt: str,
    user_prompt_template: str,
    field_descriptions: dict[str, Any],
    *,
    is_active: bool = False,
) -> ExtractionPrompt:
    """Create a new prompt version.

    Args:
        session: Database session
        name: Prompt name (e.g., "world_model")
        version: Version number (must be unique for this name)
        system_prompt: System prompt text
        user_prompt_template: User prompt template with placeholders
        field_descriptions: JSON describing each field in the schema
        is_active: Whether this should be the active version

    Returns:
        The created ExtractionPrompt
    """
    prompt = ExtractionPrompt(
        name=name,
        version=version,
        system_prompt=system_prompt,
        user_prompt_template=user_prompt_template,
        field_descriptions=field_descriptions,
        is_active=is_active,
    )

    session.add(prompt)
    await session.flush()

    # If setting as active, deactivate other versions
    if is_active:
        await _deactivate_others(session, name, prompt.id)

    return prompt


async def set_active_prompt(session: AsyncSession, prompt_id: UUID) -> ExtractionPrompt | None:
    """Set a prompt as the active version for its name.

    Args:
        session: Database session
        prompt_id: UUID of the prompt to activate

    Returns:
        The activated prompt if found, None otherwise
    """
    prompt = await session.get(ExtractionPrompt, prompt_id)
    if not prompt:
        return None

    # Deactivate all other versions of this prompt name
    await _deactivate_others(session, prompt.name, prompt_id)

    # Activate this one
    prompt.is_active = True
    await session.flush()

    return prompt


async def _deactivate_others(session: AsyncSession, name: str, except_id: UUID) -> None:
    """Deactivate all prompts with the given name except the specified one."""
    stmt = (
        update(ExtractionPrompt)
        .where(
            ExtractionPrompt.name == name,
            ExtractionPrompt.id != except_id,
            ExtractionPrompt.is_active == True,  # noqa: E712
        )
        .values(is_active=False)
    )
    await session.execute(stmt)


async def list_prompts(
    session: AsyncSession,
    *,
    name: str | None = None,
    limit: int = 100,
) -> list[ExtractionPrompt]:
    """List prompts with optional filters.

    Args:
        session: Database session
        name: Optional name to filter by
        limit: Maximum number of prompts to return

    Returns:
        List of ExtractionPrompt objects
    """
    stmt = select(ExtractionPrompt)

    if name:
        stmt = stmt.where(ExtractionPrompt.name == name)

    stmt = stmt.order_by(ExtractionPrompt.name, ExtractionPrompt.version.desc()).limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_latest_version(session: AsyncSession, name: str) -> int:
    """Get the latest version number for a prompt name.

    Args:
        session: Database session
        name: Prompt name

    Returns:
        The highest version number, or 0 if no prompts exist
    """
    stmt = (
        select(ExtractionPrompt.version)
        .where(ExtractionPrompt.name == name)
        .order_by(ExtractionPrompt.version.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    version = result.scalar_one_or_none()
    return version if version is not None else 0


async def create_next_version(
    session: AsyncSession,
    name: str,
    system_prompt: str,
    user_prompt_template: str,
    field_descriptions: dict[str, Any],
    *,
    is_active: bool = False,
) -> ExtractionPrompt:
    """Create the next version of a prompt, auto-incrementing version number.

    Args:
        session: Database session
        name: Prompt name
        system_prompt: System prompt text
        user_prompt_template: User prompt template with placeholders
        field_descriptions: JSON describing each field
        is_active: Whether this should be the active version

    Returns:
        The created ExtractionPrompt
    """
    latest = await get_latest_version(session, name)
    return await create_prompt(
        session,
        name=name,
        version=latest + 1,
        system_prompt=system_prompt,
        user_prompt_template=user_prompt_template,
        field_descriptions=field_descriptions,
        is_active=is_active,
    )
