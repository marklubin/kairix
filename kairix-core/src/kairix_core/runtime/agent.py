
from agents import (
    Agent,
    ModelSettings,
    OpenAIProvider,
    RunConfig,
    Runner,
    RunResult,
    RunResultStreaming, set_default_openai_api,
)
from agents.models.multi_provider import MultiProvider, MultiProviderMap

from kairix_core.configuration.agent import provider_mappings, configuration_sets
from kairix_core.configuration.types import AgentConfigurationSet, ProviderName, AgentConfig
from kairix_core.runtime.logging import LoggingRuntime
from kairix_core.util.environment import get_or_raise

logger = LoggingRuntime().logger

environment_configuration_set = configuration_sets[get_or_raise("KAIRIX_AGENT_CONFIGURATION_SET_KEY")]

class AgentRuntime:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self,
                 configuration_set: AgentConfigurationSet=environment_configuration_set,
                 available_provider_mappings: dict[ProviderName,OpenAIProvider]= provider_mappings
                 ):
        # Use chat completions API instead of responses API for compatibility
        set_default_openai_api("chat_completions")
        self.configuration_set = configuration_set
        self.model_provider = MultiProvider(provider_map=MultiProviderMap())
        self.model_provider.provider_map.set_mapping(available_provider_mappings) # type: ignore

    def _get_agent_config(self, agent: Agent)-> AgentConfig:
        if agent.name in self.configuration_set.agent_configs:
            logger.info("Found explicit config for agent.")
            return self.configuration_set.agent_configs[agent.name]

        if "default" in self.configuration_set.agent_configs:
            logger.warning(f"No explicit config for {agent.name}, falling back to default.")
            return self.configuration_set.agent_configs["default"]


        logger.error(f"Unable to run agent {agent.name}, no config provided.")
        raise ValueError("Missing agent config.")

    def _get_run_config(self, agent: Agent)->RunConfig:
        agent_config: AgentConfig = self._get_agent_config(agent)

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
        return await Runner.run(agent, stimulus, run_config=self._get_run_config(agent))

    def run_sync(self, agent: Agent, stimulus: str) -> RunResult:
        return Runner.run_sync(agent, stimulus, run_config=self._get_run_config(agent))

    def run_streamed(self, agent: Agent, stimulus: str) -> RunResultStreaming:
        return Runner.run_streamed(agent, stimulus, run_config=self._get_run_config(agent))
