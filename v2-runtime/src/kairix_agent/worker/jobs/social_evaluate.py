"""Social evaluation job.

Uses BlockManagerAgent to evaluate a social interaction and decide
whether to engage (and how).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from letta_client import AsyncLetta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from kairix_agent.config import Config
from kairix_agent.llm.block_manager import BlockManagerAgent
from kairix_agent.llm.configs import SOCIAL_EVALUATE_CONFIG
from kairix_agent.social.models import SocialChannel, SocialInteraction, SocialTrigger
from kairix_agent.worker.metrics import instrument_job

# Database session factory
_engine = create_async_engine(Config.DATABASE_URL.value, echo=False)
_async_session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

if TYPE_CHECKING:
    from saq.types import Context

logger = logging.getLogger(__name__)

# Job name constant
SOCIAL_EVALUATE_JOB = "social_evaluate"
SOCIAL_DRAFT_JOB = "social_draft"


async def _build_evaluation_context(
    db: AsyncSession,
    interaction: SocialInteraction,
    channel: SocialChannel,
    trigger: SocialTrigger | None,
) -> dict[str, Any]:
    """Build context for evaluation prompt.

    Args:
        db: Database session.
        interaction: The interaction to evaluate.
        channel: The social channel.
        trigger: The trigger that fired (if any).

    Returns:
        Context dict for the evaluation prompt.
    """
    # Build thread context if this is a reply
    thread_context = ""
    if interaction.parent_post_id:
        # In a real implementation, we'd fetch the parent post
        thread_context = f"This is a reply to post: {interaction.parent_post_id}"
        if interaction.thread_root_id and interaction.thread_root_id != interaction.parent_post_id:
            thread_context += f"\nThread root: {interaction.thread_root_id}"

    # Trigger context
    trigger_context = ""
    if trigger:
        trigger_context = f"Triggered by: {trigger.trigger_type}"
        if trigger.config:
            trigger_context += f" (config: {trigger.config})"

    return {
        "post_content": interaction.content_text or "",
        "author_handle": interaction.external_author or "unknown",
        "author_did": interaction.external_author_did or "",
        "interaction_type": interaction.interaction_type,
        "thread_context": thread_context,
        "trigger_context": trigger_context,
        "engagement_level": channel.engagement_level,
        "trust_level": channel.trust_level,
        "channel_type": channel.channel_type,
        "extra_data": interaction.extra_data,
    }


@instrument_job("social_evaluate")
async def social_evaluate(
    ctx: Context,
    *,
    agent_id: str,
    channel_id: str,
    interaction_id: str,
    trigger_id: str | None = None,
    is_mention: bool = False,
) -> dict[str, object]:
    """Evaluate a social interaction for engagement.

    This job uses BlockManagerAgent with the SOCIAL_EVALUATE_CONFIG
    to decide whether and how to engage with a post.

    Args:
        ctx: SAQ job context.
        agent_id: Agent ID.
        channel_id: Social channel ID.
        interaction_id: Interaction to evaluate.
        trigger_id: Optional trigger that initiated this evaluation.
        is_mention: Whether this is a direct mention.

    Returns:
        Evaluation result with decision and reasoning.
    """
    from saq.queue import Queue

    queue: Queue = ctx["queue"]

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

        # Load trigger if specified
        trigger = None
        if trigger_id:
            result = await db.execute(
                select(SocialTrigger).where(SocialTrigger.id == trigger_id)
            )
            trigger = result.scalar_one_or_none()

        # Build evaluation context
        context = await _build_evaluation_context(db, interaction, channel, trigger)

        # Run BlockManagerAgent for evaluation
        logger.info(
            "Evaluating interaction %s for agent %s (is_mention=%s)",
            interaction_id,
            agent_id,
            is_mention,
        )

        # Create Letta client
        letta_client = AsyncLetta(base_url=Config.LETTA_BASE_URL.value)

        # Build input text for the agent
        input_text = f"""Post from @{context["author_handle"]}:
{context["post_content"]}

{context["thread_context"]}
{context["trigger_context"]}"""

        block_agent = BlockManagerAgent(SOCIAL_EVALUATE_CONFIG)
        response_text = await block_agent.run(
            input_text=input_text,
            agent_id=agent_id,
            letta_client=letta_client,
            template_vars={
                "post_content": context["post_content"],
                "author_handle": context["author_handle"],
                "interaction_type": context["interaction_type"],
                "thread_context": context["thread_context"],
                "trigger_context": context["trigger_context"],
                "engagement_level": context["engagement_level"],
                "is_mention": str(is_mention),
            },
        )

        # Parse evaluation decision
        should_engage = _parse_engagement_decision(response_text)

        logger.info(
            "Evaluation complete for %s: should_engage=%s",
            interaction_id,
            should_engage,
        )

        # If we should engage, enqueue draft job
        if should_engage:
            await queue.enqueue(
                SOCIAL_DRAFT_JOB,
                agent_id=agent_id,
                channel_id=channel_id,
                interaction_id=interaction_id,
                is_mention=is_mention,
                evaluation_reasoning=response_text,
            )
            logger.info("Enqueued draft job for interaction %s", interaction_id)

        return {
            "status": "ok",
            "interaction_id": interaction_id,
            "should_engage": should_engage,
            "reasoning": response_text,
            "draft_enqueued": should_engage,
        }


def _parse_engagement_decision(response: str) -> bool:
    """Parse the engagement decision from evaluation response.

    The evaluation response should contain clear indicators like:
    - "ENGAGE: yes" or "ENGAGE: no"
    - "should_engage: true/false"
    - Or similar patterns

    Args:
        response: Raw response from evaluation.

    Returns:
        True if agent should engage, False otherwise.
    """
    response_lower = response.lower()

    # Look for explicit engage signals
    if "engage: yes" in response_lower:
        return True
    if "should_engage: true" in response_lower:
        return True
    if "engage: no" in response_lower:
        return False
    if "should_engage: false" in response_lower:
        return False

    # Look for recommendation keywords
    positive_signals = ["recommend engaging", "worth responding", "should respond", "engage with this"]
    negative_signals = ["skip this", "don't engage", "not worth", "ignore this", "pass on this"]

    for signal in positive_signals:
        if signal in response_lower:
            return True

    for signal in negative_signals:
        if signal in response_lower:
            return False

    # Default to engaging for mentions, not engaging otherwise
    # (conservative default)
    return False
