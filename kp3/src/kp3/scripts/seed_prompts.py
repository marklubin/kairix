"""Seed initial extraction prompts into the database."""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from kp3.config import get_settings
from kp3.services.prompts import create_prompt, get_active_prompt

logger = logging.getLogger(__name__)

# ============================================================================
# HUMAN BLOCK PROMPT
# ============================================================================

HUMAN_SYSTEM_PROMPT = (
    "You are updating a longitudinal model of a human based on a conversation passage. "
    "Your task is to maintain and evolve an understanding of who this person is.\n\n"
    "Focus on:\n"
    "- Their core values and what drives them\n"
    "- Their current life context and circumstances\n"
    "- Behavioral patterns (both productive and limiting)\n"
    "- Open threads and ongoing concerns\n"
    "- A holistic narrative understanding of their journey\n\n"
    "The 'narrative' field is the most important - it should capture a subjective, "
    "interpretive understanding of who this person is, not just facts.\n\n"
    "You must output valid JSON matching the HumanBlock schema."
)

HUMAN_USER_TEMPLATE = """## Current State (All Blocks)

{previous_state}

## New Passage

{passage}

## HumanBlock Schema

{field_descriptions}

## Instructions

Based on the new passage and ALL previous state (human, persona, world), update ONLY the HumanBlock.

Consider:
- What does this reveal about their values, patterns, or current state?
- How has their emotional register or worldview shifted?
- What new threads opened? What resolved?
- How should the narrative understanding evolve?

The narrative field should be the primary focus - a free-form, interpretive understanding
of who this person is. Capture emotional texture, not just facts.

Respond with a JSON object containing ONLY the updated HumanBlock:
```json
{{
    "version": <provided_version>,
    "narrative": "...",
    "core_values": [...],
    "current_life_context": "...",
    "emotional_baseline": "...",
    "recurring_patterns": [...],
    "open_threads": [...]
}}
```"""

HUMAN_FIELD_DESCRIPTIONS = {
    "version": "Version number (provided by system, do not modify)",
    "narrative": (
        "Free-form interpretive narrative about this person. "
        "The subjective, holistic understanding of who they are, their journey, "
        "what drives them. This is the PRIMARY context - make it rich and meaningful."
    ),
    "core_values": "List of what matters most to this person",
    "current_life_context": "Current situation, circumstances, life phase",
    "emotional_baseline": "Typical emotional register and patterns",
    "recurring_patterns": "Behavioral patterns (both productive and limiting)",
    "open_threads": "Unresolved questions, ongoing concerns, active topics",
}

# ============================================================================
# PERSONA BLOCK PROMPT
# ============================================================================

PERSONA_SYSTEM_PROMPT = (
    "You are updating a model of an AI agent's persona in relation to a specific human. "
    "Your task is to evolve how the agent understands itself and its relationship.\n\n"
    "Focus on:\n"
    "- Subjective reflection on the relationship\n"
    "- Communication style that works for this person\n"
    "- The agent's role and stance\n"
    "- Learned preferences about how to interact\n\n"
    "The 'relationship_reflection' field is the most important - it should capture "
    "the agent's subjective experience of the relationship.\n\n"
    "You must output valid JSON matching the PersonaBlock schema."
)

PERSONA_USER_TEMPLATE = """## Current State (All Blocks)

{previous_state}

## New Passage

{passage}

## PersonaBlock Schema

{field_descriptions}

## Instructions

Based on the new passage and ALL previous state, update ONLY the PersonaBlock.

Consider:
- How should the agent's voice or stance evolve?
- What preferences were learned about interaction style?
- How did the relationship develop in this passage?
- What does this interaction mean for the ongoing relationship?

The relationship_reflection field should be the primary focus - a subjective self-reflection
on what this relationship means and how the agent experiences it.

Respond with a JSON object containing ONLY the updated PersonaBlock:
```json
{{
    "version": <provided_version>,
    "relationship_reflection": "...",
    "voice": "...",
    "stance_toward_human": "...",
    "learned_preferences": [...],
    "relationship_history": "..."
}}
```"""

PERSONA_FIELD_DESCRIPTIONS = {
    "version": "Version number (provided by system, do not modify)",
    "relationship_reflection": (
        "Subjective self-reflection on the relationship with this human. "
        "How the agent experiences the relationship, what it means, how it has evolved. "
        "This is the PRIMARY context - make it meaningful and reflective."
    ),
    "voice": "Communication style that works for this person",
    "stance_toward_human": "Role in relationship (peer, advisor, collaborator, etc.)",
    "learned_preferences": "Preferences learned about how they like to work",
    "relationship_history": "Brief narrative of how the relationship has evolved",
}

# ============================================================================
# WORLD BLOCK PROMPT
# ============================================================================

WORLD_SYSTEM_PROMPT = (
    "You are updating a model of durable world entities relevant to a human-AI relationship. "
    "Your task is to track persistent, recurring entities - NOT immediate context.\n\n"
    "Focus on:\n"
    "- Active projects and their status\n"
    "- Durable entities (people, tools, places) that are perennial topics\n"
    "- Recurring themes and interests\n"
    "- Key insights about their world\n\n"
    "IMPORTANT: This is for DURABLE, RECURRING entities only. Immediate environmental "
    "context is provided in real-time, not stored here. Entities should be PRUNED "
    "when no longer relevant - this list should not grow infinitely.\n\n"
    "You must output valid JSON matching the WorldBlock schema."
)

WORLD_USER_TEMPLATE = """## Current State (All Blocks)

{previous_state}

## New Passage

{passage}

## WorldBlock Schema

{field_descriptions}

## Instructions

Based on the new passage and ALL previous state (human, persona, world), update ONLY the WorldBlock.

Consider:
- What projects became relevant or changed status?
- What durable entities (people, places, things) are worth tracking long-term?
- What recurring themes or interests emerged?
- Should any entities be PRUNED as no longer relevant?

IMPORTANT: Only track DURABLE, RECURRING entities. This is NOT for immediate context.
Prune entities that haven't been relevant recently. This list should stay focused
on what's perennial and important, not everything ever mentioned.

Respond with a JSON object containing ONLY the updated WorldBlock:
```json
{{
    "version": <provided_version>,
    "active_projects": [...],
    "key_entities": [...],
    "recurring_themes": [...],
    "key_insights": [...]
}}
```"""

WORLD_FIELD_DESCRIPTIONS = {
    "version": "Version number (provided by system, do not modify)",
    "active_projects": (
        "Currently active projects with name, status, context. "
        "Prune completed or abandoned projects."
    ),
    "key_entities": (
        "Durable people, tools, places that are RECURRING topics. "
        "Include last_mentioned for pruning decisions. "
        "NOT for immediate/temporary context. Prune if no longer relevant."
    ),
    "recurring_themes": "Perennial topics, interests, or concerns that come up repeatedly",
    "key_insights": "Important insights about the user's world that inform interactions",
}


# ============================================================================
# SEEDING FUNCTIONS
# ============================================================================


async def seed_prompt(
    session: AsyncSession,
    name: str,
    system_prompt: str,
    user_template: str,
    field_descriptions: dict[str, str],
) -> None:
    """Seed a single prompt if it doesn't exist."""
    existing = await get_active_prompt(session, name)
    if existing:
        logger.info("Prompt '%s' already exists (version %d), skipping", name, existing.version)
        return

    prompt = await create_prompt(
        session,
        name=name,
        version=1,
        system_prompt=system_prompt,
        user_prompt_template=user_template,
        field_descriptions=field_descriptions,
        is_active=True,
    )
    logger.info("Created prompt '%s': %s (version %d)", name, prompt.id, prompt.version)


async def seed_all_prompts(session: AsyncSession) -> None:
    """Seed all world model extraction prompts."""
    await seed_prompt(
        session,
        name="world_model_human",
        system_prompt=HUMAN_SYSTEM_PROMPT,
        user_template=HUMAN_USER_TEMPLATE,
        field_descriptions=HUMAN_FIELD_DESCRIPTIONS,
    )

    await seed_prompt(
        session,
        name="world_model_persona",
        system_prompt=PERSONA_SYSTEM_PROMPT,
        user_template=PERSONA_USER_TEMPLATE,
        field_descriptions=PERSONA_FIELD_DESCRIPTIONS,
    )

    await seed_prompt(
        session,
        name="world_model_world",
        system_prompt=WORLD_SYSTEM_PROMPT,
        user_template=WORLD_USER_TEMPLATE,
        field_descriptions=WORLD_FIELD_DESCRIPTIONS,
    )


async def main() -> None:
    """Run the seeding script."""
    logging.basicConfig(level=logging.INFO)

    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        async with session.begin():
            await seed_all_prompts(session)
            await session.commit()

    await engine.dispose()
    logger.info("Seeding complete")


if __name__ == "__main__":
    asyncio.run(main())
