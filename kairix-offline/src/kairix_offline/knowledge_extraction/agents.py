from agents import Agent, ModelSettings

from kairix_offline.knowledge_extraction.prompts import (
    world_facts_prompt,
    user_profile_prompt,
    assistant_cognitive_prompt,
)
from kairix_offline.knowledge_extraction.types import Extraction

world_facts_extractor = Agent(
    "world_facts_extractor",
    instructions=world_facts_prompt,
    output_type=Extraction,
    model="gpt-4o-mini",
    model_settings=ModelSettings(temperature=0.3, max_tokens=8000),
)


user_profile_extractor = Agent(
    "user_profile_extractor",
    instructions=user_profile_prompt,
    output_type=Extraction,
    model="gpt-4o-mini",
    model_settings=ModelSettings(temperature=0.5, max_tokens=8000),
)


assistant_cognitive_extractor = Agent(
    "assistant_cognitive_extractor",
    instructions=assistant_cognitive_prompt,
    output_type=Extraction,
    model="gpt-4o-mini",
    model_settings=ModelSettings(temperature=0.7, max_tokens=8000),
)
