"""Social draft job.

Uses BlockManagerAgent to draft a response to a social interaction.
Creates an approval queue item for user review.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from letta_client import AsyncLetta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from kairix_agent.config import Config
from kairix_agent.events import EventType, publish_event
from kairix_agent.llm.block_manager import BlockManagerAgent
from kairix_agent.llm.configs import SOCIAL_DRAFT_CONFIG
from kairix_agent.social import approval_service
from kairix_agent.social.models import ActionType, SocialChannel, SocialInteraction, TrustLevel
from kairix_agent.worker.metrics import instrument_job

# Database session factory
_engine = create_async_engine(Config.DATABASE_URL.value, echo=False)
_async_session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

if TYPE_CHECKING:
    from saq.types import Context

logger = logging.getLogger(__name__)

# Job name constant
SOCIAL_DRAFT_JOB = "social_draft"


@instrument_job("social_draft")
async def social_draft(
    ctx: Context,
    *,
    agent_id: str,
    channel_id: str,
    interaction_id: str,
    is_mention: bool = False,
    evaluation_reasoning: str = "",
) -> dict[str, object]:
    """Draft a response to a social interaction.

    Uses BlockManagerAgent with SOCIAL_DRAFT_CONFIG to generate
    a response. The draft is placed in the approval queue if
    the channel is in learning mode, otherwise it can be auto-sent.

    Args:
        ctx: SAQ job context.
        agent_id: Agent ID.
        channel_id: Social channel ID.
        interaction_id: Interaction to respond to.
        is_mention: Whether this is a direct mention.
        evaluation_reasoning: Reasoning from evaluation step.

    Returns:
        Draft result with content and approval queue item ID.
    """
    async with _async_session() as db:
        # Load interaction
        result = await db.execute(
            select(SocialInteraction).where(SocialInteraction.id == interaction_id)
        )
        interaction = result.scalar_one_or_none()
        if not interaction:
            logger.warning("Interaction not found: %s", interaction_id)
            return {"status": "not_found", "interaction_id": interaction_id}

        # Load channel
        result = await db.execute(
            select(SocialChannel).where(SocialChannel.id == channel_id)
        )
        channel = result.scalar_one_or_none()
        if not channel:
            logger.warning("Channel not found: %s", channel_id)
            return {"status": "channel_not_found", "channel_id": channel_id}

        # Build context for drafting
        # In a full implementation, we'd search KP3 for entity models here
        entity_model = await _search_entity_model(agent_id, interaction.external_author_did)

        # Run BlockManagerAgent for drafting
        logger.info(
            "Drafting response for interaction %s (agent=%s, is_mention=%s)",
            interaction_id,
            agent_id,
            is_mention,
        )

        # Create Letta client
        letta_client = AsyncLetta(base_url=Config.LETTA_BASE_URL.value)

        # Build input text for the agent
        input_text = f"""Post from @{interaction.external_author or "unknown"}:
{interaction.content_text or ""}

Entity model: {entity_model if entity_model else "No prior interactions with this entity."}
Evaluation reasoning: {evaluation_reasoning}"""

        block_agent = BlockManagerAgent(SOCIAL_DRAFT_CONFIG)
        draft_content = await block_agent.run(
            input_text=input_text,
            agent_id=agent_id,
            letta_client=letta_client,
            template_vars={
                "post_content": interaction.content_text or "",
                "author_handle": interaction.external_author or "unknown",
                "is_mention": str(is_mention),
                "is_reply": str(interaction.parent_post_id is not None),
                "entity_model": entity_model,
                "evaluation_reasoning": evaluation_reasoning,
                "engagement_level": channel.engagement_level,
            },
        )

        if not draft_content.strip():
            logger.warning("Empty draft generated for interaction %s", interaction_id)
            return {
                "status": "empty_draft",
                "interaction_id": interaction_id,
            }

        # Clean up draft (remove any meta-text the LLM might add)
        draft_content = _clean_draft(draft_content)

        logger.info(
            "Draft generated for %s: %d chars",
            interaction_id,
            len(draft_content),
        )

        # Determine if approval is needed based on trust level
        trust_level = TrustLevel(channel.trust_level)
        needs_approval = trust_level == TrustLevel.LEARNING

        # Create approval queue item
        approval_item = await approval_service.create_approval_item(
            agent_id=agent_id,
            channel_type=channel.channel_type,
            action_type=ActionType.REPLY,
            interaction_id=interaction_id,
            draft_content=draft_content,
            target_entity=interaction.external_author,
            context_summary=_build_context_summary(interaction, evaluation_reasoning),
            confidence_score=0.7,  # Could be extracted from evaluation
            entity_model_used=entity_model,
        )

        # Publish event for UI
        await publish_event(
            agent_id=agent_id,
            event_type=EventType.SOCIAL_DRAFT_CREATED,
            payload={
                "approval_item_id": approval_item.id,
                "channel_type": channel.channel_type,
                "action_type": ActionType.REPLY.value,
                "target_entity": interaction.external_author,
                "draft_preview": draft_content[:280],
                "needs_approval": needs_approval,
            },
        )

        return {
            "status": "ok",
            "interaction_id": interaction_id,
            "approval_item_id": approval_item.id,
            "draft_length": len(draft_content),
            "needs_approval": needs_approval,
        }


async def _search_entity_model(
    agent_id: str,
    entity_did: str | None,
) -> str:
    """Search KP3 for entity model.

    Args:
        agent_id: Agent ID.
        entity_did: External entity DID.

    Returns:
        Entity model text if found, empty string otherwise.
    """
    if not entity_did:
        return ""

    # TODO: Implement KP3 search for entity model
    # This would call handle_search_kp3 with query for entity model
    # For now, return empty string
    return ""


def _build_context_summary(
    interaction: SocialInteraction,
    evaluation_reasoning: str,
) -> str:
    """Build a context summary for the approval item.

    Args:
        interaction: The source interaction.
        evaluation_reasoning: Reasoning from evaluation.

    Returns:
        Context summary string.
    """
    parts = []

    if interaction.interaction_type:
        parts.append(f"Type: {interaction.interaction_type}")

    if interaction.external_author:
        parts.append(f"From: {interaction.external_author}")

    if interaction.parent_post_id:
        parts.append("Reply to existing thread")

    if evaluation_reasoning:
        parts.append(f"Reason: {evaluation_reasoning[:200]}")

    return "\n".join(parts)


def _clean_draft(draft: str) -> str:
    """Clean up draft content.

    Remove any meta-text or instructions the LLM might have added.

    Args:
        draft: Raw draft content.

    Returns:
        Cleaned draft content.
    """
    # Remove common LLM artifacts
    lines = draft.strip().split("\n")
    cleaned_lines = []

    for line in lines:
        line_lower = line.lower().strip()
        # Skip meta-lines
        if line_lower.startswith("here's my draft"):
            continue
        if line_lower.startswith("draft:"):
            continue
        if line_lower.startswith("response:"):
            continue
        if line_lower.startswith("reply:"):
            continue
        # Skip empty lines at start
        if not cleaned_lines and not line.strip():
            continue
        cleaned_lines.append(line)

    # Remove trailing empty lines
    while cleaned_lines and not cleaned_lines[-1].strip():
        cleaned_lines.pop()

    return "\n".join(cleaned_lines)
