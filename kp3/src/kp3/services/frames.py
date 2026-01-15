"""Cognitive frame service for managing agent cognitive configurations.

Frames are passages containing JSON configuration, pointed to by refs.
They define which perceptions are active, how cognition processes update them,
and whether hooks fire on updates.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.db.models import Passage, PassageRef, PassageRefHistory
from kp3.services.derivations import create_derivations
from kp3.services.passages import create_passage
from kp3.services.refs import get_ref, get_ref_passage, set_ref

logger = logging.getLogger(__name__)


async def create_frame(
    session: AsyncSession,
    *,
    name: str,
    agent_id: str,
    perceptions: list[dict[str, Any]],
    cognition_config: dict[str, Any] | None = None,
    hooks_enabled: bool = True,
) -> dict[str, Any]:
    """Create a new cognitive frame.

    A frame is stored as a passage with JSON content, pointed to by a ref.

    Args:
        session: Database session
        name: Frame name (e.g., 'production', 'experiment-1')
        agent_id: Agent ID this frame belongs to
        perceptions: List of perception configurations
        cognition_config: Optional cognition processing configuration
        hooks_enabled: Whether hooks fire on ref updates

    Returns:
        Dict with frame details including id, ref_name, etc.
    """
    ref_name = f"{agent_id}/frame/{name}"

    # Check if frame already exists
    existing = await get_ref(session, ref_name)
    if existing:
        raise ValueError(f"Frame '{name}' already exists for agent '{agent_id}'")

    # Build frame content as JSON
    frame_content = {
        "name": name,
        "agent_id": agent_id,
        "perceptions": perceptions,
        "cognition_config": cognition_config or {
            "llm_provider": "openai",
            "model": "gpt-4o",
            "processes": {},
        },
        "hooks_enabled": hooks_enabled,
    }

    # Create passage for frame
    passage = await create_passage(
        session,
        content=json.dumps(frame_content, indent=2),
        passage_type="cognitive_frame",
        agent_id=agent_id,
        metadata={"frame_name": name},
    )

    # Create ref pointing to frame passage
    await set_ref(
        session,
        ref_name,
        passage.id,
        metadata={"frame_name": name, "agent_id": agent_id},
        fire_hooks=False,  # Frame refs don't fire hooks
    )

    await session.flush()

    return {
        "id": passage.id,
        "name": name,
        "agent_id": agent_id,
        "ref_name": ref_name,
        "perceptions": perceptions,
        "cognition_config": frame_content["cognition_config"],
        "hooks_enabled": hooks_enabled,
        "created_at": passage.created_at,
    }


async def get_frame(
    session: AsyncSession,
    agent_id: str,
    name: str,
) -> dict[str, Any] | None:
    """Get a frame by agent ID and name.

    Args:
        session: Database session
        agent_id: Agent ID
        name: Frame name

    Returns:
        Frame details dict or None if not found
    """
    ref_name = f"{agent_id}/frame/{name}"
    passage = await get_ref_passage(session, ref_name)

    if not passage:
        return None

    try:
        frame_content = json.loads(passage.content)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in frame passage %s", passage.id)
        return None

    return {
        "id": passage.id,
        "name": frame_content.get("name", name),
        "agent_id": frame_content.get("agent_id", agent_id),
        "ref_name": ref_name,
        "perceptions": frame_content.get("perceptions", []),
        "cognition_config": frame_content.get("cognition_config", {}),
        "hooks_enabled": frame_content.get("hooks_enabled", True),
        "created_at": passage.created_at,
    }


async def get_frame_by_ref(
    session: AsyncSession,
    ref_name: str,
) -> dict[str, Any] | None:
    """Get a frame by its ref name.

    Args:
        session: Database session
        ref_name: Full ref name (e.g., 'test-agent/frame/production')

    Returns:
        Frame details dict or None if not found
    """
    passage = await get_ref_passage(session, ref_name)

    if not passage:
        return None

    try:
        frame_content = json.loads(passage.content)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in frame passage %s", passage.id)
        return None

    return {
        "id": passage.id,
        "name": frame_content.get("name"),
        "agent_id": frame_content.get("agent_id"),
        "ref_name": ref_name,
        "perceptions": frame_content.get("perceptions", []),
        "cognition_config": frame_content.get("cognition_config", {}),
        "hooks_enabled": frame_content.get("hooks_enabled", True),
        "created_at": passage.created_at,
    }


async def list_frames(
    session: AsyncSession,
    agent_id: str,
) -> list[dict[str, Any]]:
    """List all frames for an agent.

    Args:
        session: Database session
        agent_id: Agent ID

    Returns:
        List of frame details dicts
    """
    prefix = f"{agent_id}/frame/"

    stmt = select(PassageRef).where(PassageRef.name.like(f"{prefix}%"))
    result = await session.execute(stmt)
    refs = result.scalars().all()

    frames = []
    for ref in refs:
        passage = await session.get(Passage, ref.passage_id)
        if passage:
            try:
                frame_content = json.loads(passage.content)
                frames.append({
                    "id": passage.id,
                    "name": frame_content.get("name"),
                    "agent_id": frame_content.get("agent_id", agent_id),
                    "ref_name": ref.name,
                    "perceptions": frame_content.get("perceptions", []),
                    "cognition_config": frame_content.get("cognition_config", {}),
                    "hooks_enabled": frame_content.get("hooks_enabled", True),
                    "created_at": passage.created_at,
                })
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in frame passage %s", passage.id)

    return frames


async def fork_frame(
    session: AsyncSession,
    agent_id: str,
    source_name: str,
    new_name: str,
    *,
    hooks_enabled: bool = False,
) -> dict[str, Any]:
    """Fork a frame to create a new derived version.

    The new frame:
    - Has its own passage (derived from source)
    - Has its own refs for perceptions (copied from source)
    - Has hooks_enabled set to the provided value (default False for experiments)

    Args:
        session: Database session
        agent_id: Agent ID
        source_name: Name of frame to fork from
        new_name: Name for the new frame
        hooks_enabled: Whether hooks fire on the new frame

    Returns:
        New frame details dict
    """
    # Get source frame
    source_frame = await get_frame(session, agent_id, source_name)
    if not source_frame:
        raise ValueError(f"Source frame '{source_name}' not found for agent '{agent_id}'")

    # Check new frame doesn't exist
    new_ref_name = f"{agent_id}/frame/{new_name}"
    if await get_ref(session, new_ref_name):
        raise ValueError(f"Frame '{new_name}' already exists for agent '{agent_id}'")

    # Create new perception refs by copying source refs
    new_perceptions = []
    for perception in source_frame["perceptions"]:
        old_ref = perception["ref"]
        # Extract perception name from ref path
        parts = old_ref.split("/")
        if len(parts) >= 3:
            perception_name = parts[-1]
            new_perception_ref = f"{agent_id}/perception/{perception_name}/{new_name}"
        else:
            new_perception_ref = f"{old_ref}/{new_name}"

        # Copy the passage reference
        source_passage_id = await get_ref(session, old_ref)
        if source_passage_id:
            await set_ref(
                session,
                new_perception_ref,
                source_passage_id,
                fire_hooks=False,
            )

        new_perceptions.append({
            "name": perception["name"],
            "ref": new_perception_ref,
            "process": perception["process"],
        })

    # Build new frame content
    frame_content = {
        "name": new_name,
        "agent_id": agent_id,
        "perceptions": new_perceptions,
        "cognition_config": source_frame["cognition_config"],
        "hooks_enabled": hooks_enabled,
    }

    # Create new passage for frame
    new_passage = await create_passage(
        session,
        content=json.dumps(frame_content, indent=2),
        passage_type="cognitive_frame",
        agent_id=agent_id,
        metadata={"frame_name": new_name, "forked_from": source_name},
    )

    # Create derivation link
    await create_derivations(
        session,
        derived_passage_id=new_passage.id,
        source_passage_ids=[source_frame["id"]],
    )

    # Create ref for new frame
    await set_ref(
        session,
        new_ref_name,
        new_passage.id,
        metadata={"frame_name": new_name, "agent_id": agent_id, "forked_from": source_name},
        fire_hooks=False,
    )

    await session.flush()

    return {
        "id": new_passage.id,
        "name": new_name,
        "agent_id": agent_id,
        "ref_name": new_ref_name,
        "perceptions": new_perceptions,
        "cognition_config": frame_content["cognition_config"],
        "hooks_enabled": hooks_enabled,
        "created_at": new_passage.created_at,
        "forked_from": source_name,
    }


async def activate_frame(
    session: AsyncSession,
    agent_id: str,
    name: str,
) -> dict[str, Any]:
    """Activate a frame by setting it as the active frame for the agent.

    Sets the {agent_id}/frame/active ref to point to this frame's passage.

    Args:
        session: Database session
        agent_id: Agent ID
        name: Frame name to activate

    Returns:
        Activation details
    """
    frame = await get_frame(session, agent_id, name)
    if not frame:
        raise ValueError(f"Frame '{name}' not found for agent '{agent_id}'")

    active_ref_name = f"{agent_id}/frame/active"
    await set_ref(
        session,
        active_ref_name,
        frame["id"],
        metadata={"activated_frame": name},
        fire_hooks=False,
    )

    await session.flush()

    return {
        "frame_ref": frame["ref_name"],
        "activated_at": datetime.now(timezone.utc),
    }


async def resolve_frame(
    session: AsyncSession,
    agent_id: str,
    name: str,
) -> dict[str, Any]:
    """Resolve a frame to a frozen snapshot with pinned passage IDs.

    This produces a deterministic closure by capturing the current HEAD
    passage IDs for all perception refs in the frame.

    Args:
        session: Database session
        agent_id: Agent ID
        name: Frame name to resolve

    Returns:
        Frozen snapshot with pinned passage IDs
    """
    frame = await get_frame(session, agent_id, name)
    if not frame:
        raise ValueError(f"Frame '{name}' not found for agent '{agent_id}'")

    pinned_refs: dict[str, UUID] = {}

    for perception in frame["perceptions"]:
        ref_name = perception["ref"]
        passage_id = await get_ref(session, ref_name)
        if passage_id:
            pinned_refs[ref_name] = passage_id

    return {
        "frame_name": name,
        "agent_id": agent_id,
        "resolved_at": datetime.now(timezone.utc),
        "pinned_refs": pinned_refs,
    }


async def get_ref_version(
    session: AsyncSession,
    ref_name: str,
) -> int:
    """Get the version (history count) for a ref.

    Version is determined by counting history entries.

    Args:
        session: Database session
        ref_name: Ref name

    Returns:
        Version number (0 if ref doesn't exist, 1+ otherwise)
    """
    stmt = select(func.count()).select_from(PassageRefHistory).where(
        PassageRefHistory.ref_name == ref_name
    )
    result = await session.execute(stmt)
    count = result.scalar() or 0
    return count
