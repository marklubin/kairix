"""Seed initial extraction prompts into the database."""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from kp3.config import get_settings
from kp3.services.prompts import create_prompt, get_active_prompt

logger = logging.getLogger(__name__)

# Initial world model prompt
WORLD_MODEL_SYSTEM_PROMPT = (
    "You are analyzing a conversation passage to update a longitudinal world model "
    "that tracks a human-AI relationship over time.\n\n"
    "Your task is to update three interconnected models based on the new passage:\n"
    "- HUMAN: Your evolving understanding of who this person is\n"
    "- PERSONA: Your evolving sense of yourself as their AI companion\n"
    "- WORLD: Shared context about projects, environment, situation\n\n"
    "You must output valid JSON matching the specified schema. "
    "Increment the version number for each block."
)

WORLD_MODEL_USER_TEMPLATE = """## Previous State

{previous_state}

## New Passage

{passage}

## Schema Field Descriptions

{field_descriptions}

## Instructions

Analyze this passage and produce updated versions of all three blocks. Consider:

**For HUMAN block:**
- What does this reveal about the user's values, patterns, current state?
- How has their emotional register or worldview shifted?
- What new threads opened? What resolved?

**For PERSONA block:**
- How should the agent's voice or stance evolve based on this interaction?
- What preferences were learned?
- How did the relationship develop?

**For WORLD block:**
- What projects or entities became relevant?
- How did environmental context change?

Guidelines:
- Increment version numbers from the previous state
- Preserve important information from previous state
- Note significant shifts or transitions
- Capture emotional texture, not just facts
- If something resolved, move it from open_threads

Respond with a JSON object containing all three updated blocks:
```json
{{
    "human": {{ ... }},
    "persona": {{ ... }},
    "world": {{ ... }}
}}
```"""

WORLD_MODEL_FIELD_DESCRIPTIONS = {
    "human": {
        "version": "Monotonically increasing version number",
        "core_values": "List of what matters most to this person",
        "current_life_context": "Current situation, circumstances, life phase",
        "emotional_baseline": "Typical emotional register and patterns",
        "recurring_patterns": "Behavioral patterns (both productive and limiting)",
        "open_threads": "Unresolved questions, ongoing concerns, active topics",
    },
    "persona": {
        "version": "Monotonically increasing version number",
        "voice": "Communication style that works for this person",
        "stance_toward_human": "Role in relationship (peer, advisor, collaborator, etc.)",
        "learned_preferences": "Preferences learned about how they like to work",
        "relationship_history": "Brief narrative of how the relationship has evolved",
    },
    "world": {
        "version": "Monotonically increasing version number",
        "active_projects": "List of currently active projects with name, status, context",
        "key_entities": "People, tools, places relevant to interactions with name, relevance",
        "environmental_context": "Time, location, life phase, situational context",
    },
}


async def seed_world_model_prompt(session: AsyncSession) -> None:
    """Seed the initial world model extraction prompt."""
    prompt_name = "world_model"

    # Check if already exists
    existing = await get_active_prompt(session, prompt_name)
    if existing:
        logger.info("World model prompt already exists (version %d), skipping", existing.version)
        return

    # Create initial prompt
    prompt = await create_prompt(
        session,
        name=prompt_name,
        version=1,
        system_prompt=WORLD_MODEL_SYSTEM_PROMPT,
        user_prompt_template=WORLD_MODEL_USER_TEMPLATE,
        field_descriptions=WORLD_MODEL_FIELD_DESCRIPTIONS,
        is_active=True,
    )

    logger.info("Created world model prompt: %s (version %d)", prompt.id, prompt.version)


async def main() -> None:
    """Run the seeding script."""
    logging.basicConfig(level=logging.INFO)

    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        async with session.begin():
            await seed_world_model_prompt(session)
            await session.commit()

    await engine.dispose()
    logger.info("Seeding complete")


if __name__ == "__main__":
    asyncio.run(main())
