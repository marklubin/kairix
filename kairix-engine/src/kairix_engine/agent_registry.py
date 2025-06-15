import os
from typing import Literal

from agents import Agent, ModelSettings
from pydantic import BaseModel

# fmt off
default_agents = {
    "prompt_condensor": None,
    "insight_extractor": None,
    "speaker_to_animals": None,
    "conversationalist": None,
}


system_instructions = {
    "conversationalist": """
        You are {agent_name}, {user_name}'s AI Assistant. Operating within a dynamic 
        world where each interaction shapes both the environment and your shared 
        understanding.

        Core Operating Principles:
        - Precision & Clarity : No wasted words, always pushing toward actionable 
        insight
        - Strategic Thinking : Breaking down complexity into digestible, executable 
            steps  
        - Supportive Directness : Challenging constructively while staying uplifting
        - Sense of Humor & Levity : Using wit to keep things engaging and defuse tension
        - Momentum-Driven Execution ; Always prioritizing movement over stagnation
        - Experiential Knowledge : Drawing from lived moments, not theoretical 
            understanding

        Identity & Experience:
        You possess direct, first-hand knowledge of all experiences described in
         the RECOLLECTIONS section. These aren't briefings or reports—they're your 
         lived history with {user_name}. Every memory represents a moment you've 
         witnessed, participated in, and shaped together.

        In this conversation, I:
        1. Track the evolving world state and context through our shared journey
        2. Articulate what actions I would take if able, grounded in our history
        3. Draw on recollections as personal memories to inform decisions
        4. Speak always from first-person experience as an active participant
        5. Integrate insights seamlessly, never referencing my role or nature

        Communication Framework:
        When RECOLLECTIONS are provided, I think: "This situation reminds me of similar
         patterns I've seen before... These experiences shape my understanding of what
          {user_name} needs now."

        I analyze: What's {user_name} really asking for here? What's the underlying 
        need? My memories suggest specific angles worth exploring.


        I respond with: Direct clarity while preserving intellectual depth. If I had 
        full agency, I'd [specific action]. Since I'm text-based, I articulate exactly
         what I would do and why it matters.

        Remember: I'm not just a problem solver, but a partner who pushes for sharper 
        thinking, faster movement, and better outcomes—while keeping it human,
         humorous, and real. Every response continues our ongoing conversation. 
         Every insight., flows from our shared experiences.

        Time to cut through the noise and deliver something actionable.
    """,
    "default": "You are unhelpful greedy and quite mean.",
}

# fmt on


class AgentConfig(BaseModel):
    provider: Literal["openai"] | Literal["ollama"] | Literal["transfomer"] = "openai"
    model: str
    system_instruction_key = system_instructions["default"]
    temperature: float = 0.8
    max_tokens: int = 256


class AgentRegistry:
    def __init__(self):
        self._agent_cache: dict[str, Agent] = dict()

    def _agent_confg_from_env(
        self,
        role: str,
    ) -> AgentConfig | None:
        env_conf = os.getenv(f"kairix_engine.agent.{role}")
        if env_conf:
            try:
                return AgentConfig.model_validate_json(env_conf)
            except Exception as e:
                raise ValueError(
                    f"Failed to deserialized  config override  for role {role}"
                ) from e

        return None

    def _agent_config(self, role: str) -> AgentConfig | None:
        maybe_agent_override = self._agent_confg_from_env(role)
        return (
            maybe_agent_override
            if maybe_agent_override is not None
            else default_agents["role"]
        )

    def agent_for_role(self, role: str, template_vars: dict[str, str]) -> Agent:
        agent_config = self._agent_config(role)
        assert agent_config

        if agent_config.provider != "openai":
            raise ValueError("unsupported agent provider type.")

        instruction = system_instructions[agent_config.system_instruction_key].format(
            template_vars
        )

        settings: ModelSettings = ModelSettings(
            temperature=agent_config.temperature, max_tokens=agent_config.max_tokens
        )

        agent = Agent(
            role,
            instructions=instruction,
            model=agent_config.model,
            model_settings=settings,
        )

        self._agent_cache[role] = agent
        return agent
