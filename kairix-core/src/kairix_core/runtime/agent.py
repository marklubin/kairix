"""Runtime for executing AI agents with proper configuration.

This module provides a singleton runtime that manages agent configurations,
inference providers, and execution environments. It supports multiple providers
(OpenAI, Ollama, llama.cpp) and handles both sync and async execution modes.
"""

from agents import (
    Agent,
    ModelProvider,
    ModelSettings,
    RunConfig,
    Runner,
    RunResult,
    RunResultStreaming,
    set_default_openai_api,
    set_tracing_disabled,
)
from agents.mcp.server import MCPServerStdio, MCPServerStdioParams
from agents.models.multi_provider import MultiProvider, MultiProviderMap

from kairix_core.configuration.agent import configuration_sets, provider_mappings
from kairix_core.configuration.types import AgentConfig, AgentConfigurationSet, ProviderName
from kairix_core.runtime.logging import LoggingRuntime
from kairix_core.util.utils import get_or_raise

logger = LoggingRuntime().logger


# Delay environment variable access until runtime
def _get_environment_configuration_set():
    """Get configuration set from environment, with lazy evaluation."""
    return configuration_sets[get_or_raise("KAIRIX_AGENT_CONFIGURATION_SET_KEY")]


def _get_magg_path():
    return str(get_or_raise("KAIRIX_MAGG_EXECUTABLE"))


set_default_openai_api("chat_completions")
set_tracing_disabled(True)


class AgentRuntime:
    """Singleton runtime for executing AI agents.
    
    Manages agent configurations and provider mappings, ensuring consistent
    execution across the application. Uses the singleton pattern to maintain
    a single runtime instance.
    
    Attributes:
        configuration_set: The active configuration set with agent configs
        model_provider: Multi-provider instance for inference routing
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        """Ensure only one instance of AgentRuntime exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self,
                 configuration_set: AgentConfigurationSet | None = None,
                 available_provider_mappings: dict[ProviderName, ModelProvider] | None = None
                 ):
        """Initialize the agent runtime.
        
        Args:
            configuration_set: Configuration set with agent definitions
            available_provider_mappings: Mapping of provider names to implementations
        """
        # Use provided values or get from environment
        if configuration_set is None:
            configuration_set = _get_environment_configuration_set()
        if available_provider_mappings is None:
            available_provider_mappings = provider_mappings

        self.configuration_set = configuration_set
        self.model_provider = MultiProvider(provider_map=MultiProviderMap())
        if self.model_provider.provider_map is not None:
            self.model_provider.provider_map.set_mapping(available_provider_mappings)

        magg_path: str = _get_magg_path()
        mcp_params: MCPServerStdioParams = MCPServerStdioParams(
            command=magg_path,
            args=["serve"]
        )

        self.mcp_server = MCPServerStdio(params=mcp_params)

    def _get_agent_config(self, agent: Agent) -> AgentConfig:
        """Get configuration for a specific agent.
        
        Looks up agent-specific configuration, falling back to default if not found.
        
        Args:
            agent: The agent to get configuration for
            
        Returns:
            Agent configuration
            
        Raises:
            ValueError: If no configuration found for agent and no default exists
        """
        if agent.name in self.configuration_set.agent_configs:
            logger.info("Found explicit config for agent.")
            return self.configuration_set.agent_configs[agent.name]

        if "default" in self.configuration_set.agent_configs:
            logger.warning(f"No explicit config for {agent.name}, falling back to default.")
            return self.configuration_set.agent_configs["default"]

        logger.error(f"Unable to run agent {agent.name}, no config provided.")
        raise ValueError("Missing agent config.")

    def _get_run_config(self, agent: Agent) -> RunConfig:
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
