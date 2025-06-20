from typing import Literal

from agents import (
    Agent,
    ModelSettings,
    OpenAIProvider,
    RunConfig,
    Runner,
    RunResult,
    RunResultStreaming,
)
from agents.models.multi_provider import MultiProvider, MultiProviderMap
from pydantic import BaseModel

from kairix_core.util.environment import get_or_raise

tokens = int(get_or_raise("KAIRIX_SUMMARIZER_MAX_TOKENS"))
temp = float(get_or_raise("KAIRIX_SUMMARIZER_TEMPERATURE"))

ProviderName = Literal["openai" , "ollama-remote" , "ollama-local"]

class AgentConfig(BaseModel):
    name: str
    model: str
    temperature: float = temp
    max_tokens: int = tokens


class AgentConfigurationSet(BaseModel):
    name: str
    default_provider: ProviderName
    description: str
    agent_configs: dict[str, AgentConfig]


def model_for_provider(provider_name: ProviderName, model: str)->str:
    if provider_name == "openai":
        return model
    return f"{provider_name}/{model}"



class CognitionAgentRunner:
    def __init__(self, configuration_set: AgentConfigurationSet,
                 available_provider_mappings: dict[ProviderName, OpenAIProvider]):

        self.configuration_set = configuration_set
        self.model_provider = MultiProvider(provider_map=MultiProviderMap())
        self.model_provider.provider_map.set_mapping(available_provider_mappings) # type: ignore


    def get_run_config(self, agent: Agent)->RunConfig:
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

    async def run(self, agent: Agent, stimulus: str) -> RunResult:
        return await Runner.run(agent, stimulus, run_config=self.get_run_config(agent))

    def run_sync(self, agent: Agent, stimulus: str) -> RunResult:
        return Runner.run_sync(agent, stimulus, run_config=self.get_run_config(agent))

    def run_streamed(self, agent: Agent, stimulus: str) -> RunResultStreaming:
        return Runner.run_streamed(agent, stimulus, run_config=self.get_run_config(agent))
