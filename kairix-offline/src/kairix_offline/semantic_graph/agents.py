from agents import Agent, ModelSettings

import kairix_offline.semantic_graph.prompts as prompts
from kairix_offline.semantic_graph.types import Extract

world_facts_extractor = Agent(
    "world_facts_extractor",
    instructions=prompts.world_facts_prompt,
    output_type=Extract,
    model_settings=ModelSettings(max_tokens=16000),
)


user_profile_extractor = Agent(
    "user_profile_extractor",
    instructions=prompts.user_profile_prompt,
    output_type=Extract,
    model_settings=ModelSettings(max_tokens=16000),
)


assistant_cognitive_extractor = Agent(
    "assistant_cognitive_extractor",
    instructions=prompts.assistant_extraction,
    output_type=Extract,
    model_settings=ModelSettings(max_tokens=16000),
)
