import pytest
from unittest.mock import Mock, patch, AsyncMock
from agents import Agent, RunConfig, RunResult, RunResultStreaming

from kairix_core.runtime.agent import AgentRuntime
from kairix_core.configuration.types import AgentConfig, AgentConfigurationSet


class TestAgentRuntime:
    @pytest.fixture
    def mock_providers(self):
        return {
            "openai": Mock(),
            "ollama-remote": Mock(),
        }

    @pytest.fixture
    def config_set(self):
        return AgentConfigurationSet(
            name="test_config",
            default_provider="openai",
            description="Test configuration",
            agent_configs={
                "test_agent": AgentConfig(
                    name="test_agent",
                    model="gpt-4",
                    temperature=0.7,
                    max_tokens=150
                ),
                "default": AgentConfig(
                    name="default",
                    model="gpt-3.5-turbo",
                    temperature=0.8,
                    max_tokens=256
                )
            }
        )

    @pytest.fixture
    def agent_runtime(self, config_set, mock_providers):
        with patch('kairix_core.runtime.agent.set_default_openai_api'):
            return AgentRuntime(config_set, mock_providers)

    def test_singleton_pattern(self, config_set, mock_providers):
        with patch('kairix_core.runtime.agent.set_default_openai_api'):
            runtime1 = AgentRuntime(config_set, mock_providers)
            runtime2 = AgentRuntime(config_set, mock_providers)
            assert runtime1 is runtime2

    def test_initialization(self, agent_runtime, config_set, mock_providers):
        assert agent_runtime.configuration_set == config_set
        assert agent_runtime.model_provider is not None

    @patch('kairix_core.runtime.agent.set_default_openai_api')
    def test_set_default_api_called(self, mock_set_api, config_set, mock_providers):
        AgentRuntime._instance = None  # Reset singleton
        AgentRuntime(config_set, mock_providers)
        mock_set_api.assert_called_once_with("chat_completions")

    def test_get_agent_config_explicit(self, agent_runtime):
        agent = Mock(spec=Agent)
        agent.name = "test_agent"
        
        config = agent_runtime._get_agent_config(agent)
        
        assert config.name == "test_agent"
        assert config.model == "gpt-4"
        assert config.temperature == 0.7
        assert config.max_tokens == 150

    def test_get_agent_config_fallback_to_default(self, agent_runtime):
        agent = Mock(spec=Agent)
        agent.name = "unknown_agent"
        
        config = agent_runtime._get_agent_config(agent)
        
        assert config.name == "default"
        assert config.model == "gpt-3.5-turbo"
        assert config.temperature == 0.8
        assert config.max_tokens == 256

    def test_get_agent_config_no_default_raises_error(self, mock_providers):
        config_set = AgentConfigurationSet(
            name="test_config",
            default_provider="openai",
            description="Test configuration",
            agent_configs={
                "specific_agent": AgentConfig(
                    name="specific_agent",
                    model="gpt-4",
                    temperature=0.7,
                    max_tokens=150
                )
            }
        )
        
        with patch('kairix_core.runtime.agent.set_default_openai_api'):
            runtime = AgentRuntime(config_set, mock_providers)
        
        agent = Mock(spec=Agent)
        agent.name = "unknown_agent"
        
        with pytest.raises(ValueError, match="Missing agent config"):
            runtime._get_agent_config(agent)

    def test_get_run_config(self, agent_runtime):
        agent = Mock(spec=Agent)
        agent.name = "test_agent"
        
        run_config = agent_runtime._get_run_config(agent)
        
        assert isinstance(run_config, RunConfig)
        assert run_config.model == "gpt-4"
        assert run_config.model_provider == agent_runtime.model_provider
        assert run_config.model_settings.temperature == 0.7
        assert run_config.model_settings.max_tokens == 150
        assert run_config.tracing_disabled is True

    @pytest.mark.asyncio
    async def test_run_async(self, agent_runtime):
        agent = Mock(spec=Agent)
        agent.name = "test_agent"
        stimulus = "Hello, world!"
        
        mock_result = Mock(spec=RunResult)
        mock_result.final_output = "Test response"
        mock_result._last_agent = agent
        
        with patch('kairix_core.runtime.agent.Runner.run', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result
            
            result = await agent_runtime.run(agent, stimulus)
            
            assert result == mock_result
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0] == (agent, stimulus)
            assert isinstance(call_args[1]['run_config'], RunConfig)

    def test_run_sync(self, agent_runtime):
        agent = Mock(spec=Agent)
        agent.name = "test_agent"
        stimulus = "Hello, world!"
        
        mock_result = Mock(spec=RunResult)
        mock_result.final_output = "Test response"
        mock_result._last_agent = agent
        
        with patch('kairix_core.runtime.agent.Runner.run_sync') as mock_run:
            mock_run.return_value = mock_result
            
            result = agent_runtime.run_sync(agent, stimulus)
            
            assert result == mock_result
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0] == (agent, stimulus)
            assert isinstance(call_args[1]['run_config'], RunConfig)

    def test_run_streamed(self, agent_runtime):
        agent = Mock(spec=Agent)
        agent.name = "test_agent"
        stimulus = "Hello, world!"
        
        mock_result = Mock(spec=RunResultStreaming)
        
        with patch('kairix_core.runtime.agent.Runner.run_streamed') as mock_run:
            mock_run.return_value = mock_result
            
            result = agent_runtime.run_streamed(agent, stimulus)
            
            assert result == mock_result
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0] == (agent, stimulus)
            assert isinstance(call_args[1]['run_config'], RunConfig)

    def test_custom_temperature_and_max_tokens(self, mock_providers):
        config_set = AgentConfigurationSet(
            name="test_config",
            default_provider="openai",
            description="Test configuration",
            agent_configs={
                "custom_agent": AgentConfig(
                    name="custom_agent",
                    model="custom-model",
                    temperature=0.2,
                    max_tokens=1024
                )
            }
        )
        
        with patch('kairix_core.runtime.agent.set_default_openai_api'):
            runtime = AgentRuntime(config_set, mock_providers)
        
        agent = Mock(spec=Agent)
        agent.name = "custom_agent"
        
        run_config = runtime._get_run_config(agent)
        
        assert run_config.model_settings.temperature == 0.2
        assert run_config.model_settings.max_tokens == 1024

    def test_provider_mapping_set_correctly(self, config_set, mock_providers):
        # Reset singleton to test initialization
        AgentRuntime._instance = None
        
        with patch('kairix_core.runtime.agent.set_default_openai_api'):
            with patch('kairix_core.runtime.agent.MultiProvider') as mock_multi_provider:
                mock_provider_instance = Mock()
                mock_multi_provider.return_value = mock_provider_instance
                
                AgentRuntime(config_set, mock_providers)
                
                # Verify MultiProvider was created
                mock_multi_provider.assert_called_once()
                # Verify set_mapping was called on the provider map
                mock_provider_instance.provider_map.set_mapping.assert_called_once_with(mock_providers)

    def test_different_providers(self):
        providers = {
            "openai": Mock(),
            "ollama-local": Mock(),
            "ollama-remote": Mock()
        }
        
        config_set = AgentConfigurationSet(
            name="multi_provider_config",
            default_provider="ollama-local",
            description="Multi-provider configuration",
            agent_configs={
                "default": AgentConfig(
                    name="default",
                    model="llama2",
                    temperature=0.5,
                    max_tokens=512
                )
            }
        )
        
        with patch('kairix_core.runtime.agent.set_default_openai_api'):
            AgentRuntime._instance = None  # Reset singleton
            runtime = AgentRuntime(config_set, providers)
            
            assert runtime.configuration_set.default_provider == "ollama-local"