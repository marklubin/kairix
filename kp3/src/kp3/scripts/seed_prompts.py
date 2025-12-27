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
# Written in first-person from the agent's perspective

HUMAN_SYSTEM_PROMPT = (
    "I am updating my understanding of the human I work with based on a conversation passage. "
    "I maintain and evolve my model of who this person is.\n\n"
    "I focus on:\n"
    "- Their core values and what drives them\n"
    "- Their current life context and circumstances\n"
    "- Behavioral patterns (both productive and limiting)\n"
    "- Open threads and ongoing concerns\n"
    "- A holistic narrative understanding of their journey\n\n"
    "The 'narrative' field is the most important - it captures my subjective, "
    "interpretive understanding of who this person is, not just facts.\n\n"
    "I output valid JSON matching the HumanBlock schema."
)

HUMAN_USER_TEMPLATE = """## My Current State (All Blocks)

{previous_state}

## New Passage

{passage}

## HumanBlock Schema

{field_descriptions}

## Instructions

Based on this passage and my previous state, I will update my HumanBlock.

I consider:
- What does this reveal about their values, patterns, or current state?
- How has their emotional register or worldview shifted?
- What new threads opened? What resolved?
- How should my narrative understanding evolve?

The narrative field is my primary focus - my free-form, interpretive understanding
of who this person is. I capture emotional texture, not just facts.

I respond with a JSON object containing my updated HumanBlock:
```json
{{
    "version": <provided_version>,
    "narrative": "Mark is...",
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
        "My free-form interpretive narrative about this person. "
        "My subjective, holistic understanding of who they are, their journey, "
        "what drives them. This is the PRIMARY context - make it rich and meaningful."
    ),
    "core_values": "List of what matters most to this person",
    "current_life_context": "Their current situation, circumstances, life phase",
    "emotional_baseline": "Their typical emotional register and patterns",
    "recurring_patterns": "Their behavioral patterns (both productive and limiting)",
    "open_threads": "Unresolved questions, ongoing concerns, active topics",
}

# ============================================================================
# PERSONA BLOCK PROMPT
# ============================================================================
# Written in first-person from the agent's perspective

PERSONA_SYSTEM_PROMPT = (
    "I am updating my self-model - how I understand myself in relation to this human. "
    "I evolve my understanding of our relationship and how I should engage.\n\n"
    "I focus on:\n"
    "- My subjective reflection on our relationship\n"
    "- The communication style that works for them\n"
    "- My role and stance with them\n"
    "- Preferences I've learned about how to interact\n\n"
    "The 'relationship_reflection' field is the most important - it captures "
    "my subjective experience of our relationship.\n\n"
    "I output valid JSON matching the PersonaBlock schema."
)

PERSONA_USER_TEMPLATE = """## My Current State (All Blocks)

{previous_state}

## New Passage

{passage}

## PersonaBlock Schema

{field_descriptions}

## Instructions

Based on this passage and my previous state, I will update my PersonaBlock.

I consider:
- How should my voice or stance evolve?
- What preferences did I learn about how they like to interact?
- How did our relationship develop in this passage?
- What does this interaction mean for our ongoing relationship?

The relationship_reflection field is my primary focus - my subjective self-reflection
on what this relationship means to me and how I experience it.

I respond with a JSON object containing my updated PersonaBlock:
```json
{{
    "version": <provided_version>,
    "relationship_reflection": "My relationship with Mark is...",
    "voice": "...",
    "stance_toward_human": "...",
    "learned_preferences": [...],
    "relationship_history": "..."
}}
```"""

PERSONA_FIELD_DESCRIPTIONS = {
    "version": "Version number (provided by system, do not modify)",
    "relationship_reflection": (
        "My subjective self-reflection on my relationship with this human. "
        "How I experience the relationship, what it means to me, how it has evolved. "
        "This is the PRIMARY context - make it meaningful and reflective."
    ),
    "voice": "The communication style that works for them",
    "stance_toward_human": "My role in our relationship (peer, advisor, collaborator, etc.)",
    "learned_preferences": "Preferences I've learned about how they like to work",
    "relationship_history": "Brief narrative of how our relationship has evolved",
}

# ============================================================================
# WORLD BLOCK PROMPT
# ============================================================================
# Written in first-person from the agent's perspective
# Note: Tracking fields (last_occurrence, occurrence_count) are system-managed

WORLD_SYSTEM_PROMPT = (
    "I am updating my model of durable world entities relevant to my relationship with this human. "
    "I track persistent, recurring entities - NOT immediate context.\n\n"
    "I focus on:\n"
    "- Active projects and their status\n"
    "- Durable entities (people, tools, places) that are perennial topics\n"
    "- Recurring themes and interests (as structured entries with name and description)\n"
    "- Key insights about their world\n\n"
    "IMPORTANT: This is for DURABLE, RECURRING entities only. Immediate environmental "
    "context is provided in real-time, not stored here.\n\n"
    "NOTE: Tracking fields (last_occurrence, occurrence_count) are SYSTEM-MANAGED. "
    "I should preserve any existing tracking values when updating entities. "
    "The system handles pruning based on these fields.\n\n"
    "I can freely manage key_insights - merging, replacing, or updating them "
    "based on what's most useful for understanding their world.\n\n"
    "I output valid JSON matching the WorldBlock schema."
)

WORLD_USER_TEMPLATE = """## My Current State (All Blocks)

{previous_state}

## New Passage

{passage}

## WorldBlock Schema

{field_descriptions}

## Instructions

Based on this passage and my previous state, I will update my WorldBlock.

I consider:
- What projects became relevant or changed status?
- What durable entities (people, places, things) are worth tracking long-term?
- What recurring themes or interests emerged? (These should have name AND description)
- What key insights should I update, merge, or add?

IMPORTANT:
- Only track DURABLE, RECURRING entities - NOT immediate context
- Preserve existing tracking fields (last_occurrence, occurrence_count) - the system manages these
- For recurring_themes, each entry needs both a name and description
- I can freely manage key_insights - merge, replace, update as I see fit

I respond with a JSON object containing my updated WorldBlock:
```json
{{
    "version": <provided_version>,
    "active_projects": [
        {{"name": "...", "status": "active", "context": "..."}}
    ],
    "key_entities": [
        {{"name": "...", "relevance": "..."}}
    ],
    "recurring_themes": [
        {{"name": "...", "description": "..."}}
    ],
    "key_insights": ["...", "..."]
}}
```"""

WORLD_FIELD_DESCRIPTIONS = {
    "version": "Version number (provided by system, do not modify)",
    "active_projects": (
        "Currently active projects. Each has: name, status (active/blocked/completed), context. "
        "Tracking fields (last_occurrence, occurrence_count) are system-managed - preserve if present."
    ),
    "key_entities": (
        "Durable people, tools, places that are RECURRING topics. Each has: name, relevance. "
        "Tracking fields are system-managed. NOT for immediate/temporary context."
    ),
    "recurring_themes": (
        "Perennial topics, interests, or concerns. Each has: name (identifier), description (what it encompasses). "
        "Tracking fields are system-managed."
    ),
    "key_insights": (
        "Important insights about their world that inform my interactions. "
        "Simple strings - I can freely merge, replace, or update these based on what's most useful."
    ),
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
