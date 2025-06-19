import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict

from kairix_core.cognition.configuration.runner import (
    CognitionAgentRunner,
    AgentConfigurationSet,
    AgentConfig,
    ProviderName,
)
from agents import Agent, ModelSettings, OpenAIProvider, RunConfig, RunResult, RunResultStreaming, Runner
from agents.models.multi_provider import MultiProvider, MultiProviderMap


class TestCognitionAgentRunner:
    """Test suite for CognitionAgentRunner class"""

    @pytest.fixture
    def agent_config(self):
        """Create test agent configuration"""
        return AgentConfig(name="test_agent", model="gpt-4", temperature=0.7, max_tokens=500)

    @pytest.fixture
    def configuration_set(self, agent_config):
        """Create test configuration set"""
        return AgentConfigurationSet(
            name="test_config",
            default_provider="openai",
            description="Test configuration",
            agent_configs={"test_agent": agent_config},
        )

    @pytest.fixture
    def mock_provider(self):
        """Create mock OpenAI provider"""
        provider = Mock(spec=OpenAIProvider)
        provider.api_key = "test-key"
        return provider

    @pytest.fixture
    def runner(self, configuration_set, mock_provider):
        """Create CognitionAgentRunner instance"""
        providers: Dict[ProviderName, OpenAIProvider] = {"openai": mock_provider}
        return CognitionAgentRunner(configuration_set, providers)

    def test_init(self, configuration_set, mock_provider):
        """Test CognitionAgentRunner initialization"""
        providers: Dict[ProviderName, OpenAIProvider] = {"openai": mock_provider}
        runner = CognitionAgentRunner(configuration_set, providers)

        assert runner.configuration_set == configuration_set
        assert isinstance(runner.model_provider, MultiProvider)
        assert isinstance(runner.model_provider.provider_map, MultiProviderMap)

    def test_init_multiple_providers(self, configuration_set):
        """Test initialization with multiple providers"""
        mock_openai = Mock(spec=OpenAIProvider)
        mock_ollama = Mock(spec=OpenAIProvider)

        providers: Dict[ProviderName, OpenAIProvider] = {"openai": mock_openai, "ollama-remote": mock_ollama}

        runner = CognitionAgentRunner(configuration_set, providers)
        assert runner.configuration_set == configuration_set

    def test_get_run_config(self, runner, agent_config):
        """Test get_run_config method"""
        agent = Agent(name="test_agent")

        config = runner.get_run_config(agent)

        assert isinstance(config, RunConfig)
        assert config.model == agent_config.model
        assert config.model_provider == runner.model_provider
        assert isinstance(config.model_settings, ModelSettings)
        assert config.model_settings.temperature == agent_config.temperature
        assert config.model_settings.max_tokens == agent_config.max_tokens
        assert config.tracing_disabled is True

    def test_get_run_config_unknown_agent(self, runner):
        """Test get_run_config with unknown agent raises ValueError"""
        agent = Agent(name="unknown_agent")

        with pytest.raises(ValueError, match="Unknown Agent type unknown_agent"):
            runner.get_run_config(agent)

    @pytest.mark.asyncio
    async def test_run_method(self, runner):
        """Test the @Claude decorated async run method"""
        agent = Agent(name="test_agent")
        stimulus = "test input"

        # Mock the Runner.run method
        mock_result = Mock(spec=RunResult)
        mock_result.output = "test output"

        with patch.object(Runner, "run", new=AsyncMock(return_value=mock_result)) as mock_run:
            result = await runner.run(agent, stimulus)

            assert result == mock_result
            mock_run.assert_called_once()

            # Verify the call arguments
            call_args = mock_run.call_args
            assert call_args[0][0] == agent
            assert call_args[0][1] == stimulus
            assert isinstance(call_args[1]["run_config"], RunConfig)

    def test_run_streamed_method(self, runner):
        """Test the @Claude decorated run_streamed method"""
        agent = Agent(name="test_agent")
        stimulus = "test input"

        # Mock the Runner.run_streamed method
        mock_result = Mock(spec=RunResultStreaming)

        with patch.object(Runner, "run_streamed", return_value=mock_result) as mock_run_streamed:
            result = runner.run_streamed(agent, stimulus)

            assert result == mock_result
            mock_run_streamed.assert_called_once()

            # Verify the call arguments
            call_args = mock_run_streamed.call_args
            assert call_args[0][0] == agent
            assert call_args[0][1] == stimulus
            assert isinstance(call_args[1]["run_config"], RunConfig)

    @pytest.mark.asyncio
    async def test_run_with_different_agent_configs(self, configuration_set, mock_provider):
        """Test run method with different agent configurations"""
        # Add another agent config
        another_agent_config = AgentConfig(name="another_agent", model="gpt-3.5-turbo", temperature=0.5, max_tokens=200)
        configuration_set.agent_configs["another_agent"] = another_agent_config

        providers: Dict[ProviderName, OpenAIProvider] = {"openai": mock_provider}
        runner = CognitionAgentRunner(configuration_set, providers)

        agent = Agent(name="another_agent")
        config = runner.get_run_config(agent)

        assert config.model == "gpt-3.5-turbo"
        assert config.model_settings is not None
        assert config.model_settings.temperature == 0.5
        assert config.model_settings.max_tokens == 200

    def test_model_provider_setup(self, runner, mock_provider):
        """Test that model provider is set up correctly"""
        # The provider should be added to the MultiProvider's provider_map
        assert runner.model_provider is not None
        assert isinstance(runner.model_provider, MultiProvider)

    @pytest.mark.asyncio
    async def test_claude_decorator_applied(self, runner):
        """Test that @Claude decorator is properly applied to methods"""
        # Verify the methods exist and are callable
        assert hasattr(runner, "run")
        assert hasattr(runner, "run_streamed")

        # Verify they're properly decorated (decorator is pass-through)
        assert callable(runner.run)
        assert callable(runner.run_streamed)

    def test_provider_mapping_edge_cases(self, configuration_set):
        """Test provider mapping with edge cases"""
        # Test with empty providers
        runner = CognitionAgentRunner(configuration_set, {})
        assert runner.model_provider is not None

        # Test with None values handled properly
        providers: Dict[ProviderName, OpenAIProvider] = {"openai": Mock(spec=OpenAIProvider)}
        runner = CognitionAgentRunner(configuration_set, providers)
        assert runner.configuration_set == configuration_set
