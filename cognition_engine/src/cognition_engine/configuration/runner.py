from typing import Literal

from agents import Agent, ModelSettings, OpenAIProvider, RunConfig, RunResult, RunResultStreaming, Runner
from agents.models.multi_provider import MultiProvider, MultiProviderMap
from pydantic import BaseModel
from ..utils import Claude

ProviderName = Literal["openai" , "ollama-remote" , "ollama-local"]

class AgentConfig(BaseModel):
    name: str
    model: str
    temperature: float = 0.8
    max_tokens: int = 256


class AgentConfigurationSet(BaseModel):
    name: str
    default_provider: ProviderName
    description: str
    agent_configs: dict[str, AgentConfig]


def model_for_provider(provider_name: ProviderName, model: str):
    if provider_name == "openai":
        return model
    return f"{provider_name}/{model}"



class CognitionAgentRunner:
    def __init__(self, configuration_set: AgentConfigurationSet,
                 available_provider_mappings: dict[ProviderName, OpenAIProvider]):

        self.configuration_set = configuration_set
        self.model_provider = MultiProvider(provider_map=MultiProviderMap())
        self.model_provider.provider_map.set_mapping(available_provider_mappings)


    def get_run_config(self, agent: Agent, stimulus: str)->RunConfig:
        if agent.name not in self.configuration_set.agent_configs:
            raise ValueError(f"Unknown Agent type {agent.name}, not supported.")

        agent_config: AgentConfig = self.configuration_set.agent_configs[agent.name]

        model_settings: ModelSettings = ModelSettings(
            temperature=agent_config.temperature, max_tokens=agent_config.max_tokens
        )

        return RunConfig(
            model=agent_config.model,
            model_provider=self.model_provider,
            model_settings=model_settings,
            tracing_disabled=True,
        )

    @Claude
    async def run(self, agent: Agent, stimulus: str) -> RunResult:
        return await Runner.run(agent, stimulus, run_config=self.get_run_config(agent, stimulus))


    @Claude
    def run_streamed(self, agent: Agent, stimulus: str) -> RunResultStreaming:
        return Runner.run_streamed(agent, stimulus, run_config=self.get_run_config(agent, stimulus))
