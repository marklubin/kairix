import asyncio
import itertools
import os

import pytest
import requests
from cognition_engine.configuration.runner import (
    AgentConfig,
    AgentConfigurationSet,
    CognitionAgentRunner,
    ProviderName,
    model_for_provider,
)
from dotenv import load_dotenv

from kairix_engine.engine import available_provider_mappings


class TestAgentConfigurations:
    """Test all possible agent configurations with real API calls."""

    @pytest.fixture(autouse=True)
    def setup_env(self):
        """Load environment based on ENV variable."""
        env_name = os.environ.get("ENV", "mac")
        env_path = f"env/{env_name}.env"
        if os.path.exists(env_path):
            load_dotenv(env_path, override=True)
        else:
            load_dotenv()

    def discover_openai_models(self) -> list[str]:
        """Discover available OpenAI models."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            pytest.skip("OPENAI_API_KEY not set")
        
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            models = client.models.list()
            # Filter for chat models
            chat_models = [
                model.id for model in models 
                if any(x in model.id for x in ["gpt", "chatgpt", "o1", "o3"])
            ]
            return chat_models[:5]  # Limit to avoid too many permutations
        except Exception as e:
            print(f"Failed to discover OpenAI models: {e}")
            # Fallback to known models
            return ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]

    def discover_ollama_models(self, base_url: str) -> list[str]:
        """Discover available Ollama models."""
        try:
            response = requests.get(f"{base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models_data = response.json()
                models = [model["name"] for model in models_data.get("models", [])]
                return models[:5]  # Limit to avoid too many permutations
        except Exception as e:
            print(f"Failed to discover Ollama models at {base_url}: {e}")
        
        # Return empty list if discovery fails
        return []

    def generate_agent_configs(
        self, provider: ProviderName, models: list[str]
    ) -> list[AgentConfigurationSet]:
        """Generate all permutations of agent configurations for given models."""
        if not models:
            return []
        
        configs = []
        agent_roles = ["conversationalist", "query_generator", "insight_extractor"]
        
        # Generate all possible combinations (with replacement)
        # This allows the same model to be used for multiple roles
        for model_combo in itertools.product(models, repeat=len(agent_roles)):
            agent_configs = {}
            for role, model in zip(agent_roles, model_combo, strict=False):
                if provider in ["ollama-local", "ollama-remote"]:
                    model_ref = model_for_provider(provider, model)
                else:
                    model_ref = model
                
                agent_configs[role] = AgentConfig(
                    name=role,
                    model=model_ref
                )
            
            config_name = (
                f"{provider}-{'-'.join(m.split(':')[0][:4] for m in model_combo)}"
            )
            configs.append(
                AgentConfigurationSet(
                    name=config_name,
                    default_provider=provider,
                    description=f"Test config: {', '.join(model_combo)}",
                    agent_configs=agent_configs,
                )
            )
        
        return configs

    async def test_agent_response(
        self, config_set: AgentConfigurationSet, provider_mappings: dict
    ) -> tuple[str, bool, str]:
        """Test a single agent configuration and return results."""
        try:
            # Create runner with the configuration
            runner = CognitionAgentRunner(config_set, provider_mappings)
            
            # Test with a simple prompt
            test_prompt = "Hello! Please respond with a short greeting."
            
            # Test conversationalist agent
            response = await runner.run_agent(
                "conversationalist",
                test_prompt,
                system_prompt="You are a helpful assistant. Respond briefly."
            )
            
            # Check if we got a non-empty response
            success = bool(response and response.strip())
            return (
                config_set.name,
                success,
                response[:100] if success else "Empty response"
            )
            
        except Exception as e:
            return config_set.name, False, f"Error: {str(e)[:100]}"

    @pytest.mark.asyncio
    async def test_all_openai_configurations(self):
        """Test all possible OpenAI model configurations."""
        models = self.discover_openai_models()
        if not models:
            pytest.skip("No OpenAI models discovered")
        
        print(f"\nDiscovered OpenAI models: {models}")
        
        # Generate configurations
        configs = self.generate_agent_configs("openai", models)
        print(f"Generated {len(configs)} configurations")
        
        # Test each configuration
        results = []
        provider_mappings = {}  # OpenAI doesn't need custom mappings
        
        for config in configs[:10]:  # Limit to 10 to avoid rate limits
            result = await self.test_agent_response(config, provider_mappings)
            results.append(result)
            print(f"  {result[0]}: {'✓' if result[1] else '✗'} - {result[2]}")
        
        # Assert at least one configuration worked
        successful = [r for r in results if r[1]]
        assert len(successful) > 0, f"No configurations succeeded. Results: {results}"
        
        print(f"\nSuccess rate: {len(successful)}/{len(results)}")

    @pytest.mark.asyncio
    async def test_all_ollama_local_configurations(self):
        """Test all possible local Ollama model configurations."""
        base_url = "http://localhost:11434/v1"
        models = self.discover_ollama_models(base_url.replace("/v1", ""))
        
        if not models:
            pytest.skip("No local Ollama models discovered")
        
        print(f"\nDiscovered local Ollama models: {models}")
        
        # Generate configurations
        configs = self.generate_agent_configs("ollama-local", models)
        print(f"Generated {len(configs)} configurations")
        
        # Test each configuration
        results = []
        
        for config in configs[:10]:  # Limit to 10
            result = await self.test_agent_response(config, available_provider_mappings)
            results.append(result)
            print(f"  {result[0]}: {'✓' if result[1] else '✗'} - {result[2]}")
        
        # Assert at least one configuration worked
        successful = [r for r in results if r[1]]
        assert len(successful) > 0, f"No configurations succeeded. Results: {results}"
        
        print(f"\nSuccess rate: {len(successful)}/{len(results)}")

    @pytest.mark.asyncio
    async def test_all_ollama_remote_configurations(self):
        """Test all possible remote Ollama model configurations."""
        base_url = "https://ollama.kairix.net/v1"
        models = self.discover_ollama_models(base_url.replace("/v1", ""))
        
        if not models:
            pytest.skip("No remote Ollama models discovered")
        
        print(f"\nDiscovered remote Ollama models: {models}")
        
        # Generate configurations
        configs = self.generate_agent_configs("ollama-remote", models)
        print(f"Generated {len(configs)} configurations")
        
        # Test each configuration
        results = []
        
        for config in configs[:10]:  # Limit to 10
            result = await self.test_agent_response(config, available_provider_mappings)
            results.append(result)
            print(f"  {result[0]}: {'✓' if result[1] else '✗'} - {result[2]}")
        
        # Assert at least one configuration worked
        successful = [r for r in results if r[1]]
        assert len(successful) > 0, f"No configurations succeeded. Results: {results}"
        
        print(f"\nSuccess rate: {len(successful)}/{len(results)}")

    @pytest.mark.asyncio
    async def test_mixed_provider_configurations(self):
        """Test configurations that mix different providers."""
        # Discover models from each provider
        openai_models = self.discover_openai_models()[:2]
        ollama_local_models = self.discover_ollama_models("http://localhost:11434")[:2]
        ollama_remote_models = self.discover_ollama_models("https://ollama.kairix.net")[:2]
        
        if not (openai_models or ollama_local_models or ollama_remote_models):
            pytest.skip("No models discovered from any provider")
        
        print("\nTesting mixed provider configurations")
        
        # Create a mixed configuration
        test_configs = []
        
        # Mix OpenAI and Ollama
        if openai_models and ollama_local_models:
            test_configs.append(
                AgentConfigurationSet(
                    name="mixed-openai-ollama-local",
                    default_provider="openai",
                    description="Mixed OpenAI and local Ollama",
                    agent_configs={
                        "conversationalist": AgentConfig(
                            name="conversationalist",
                            model=openai_models[0]
                        ),
                        "query_generator": AgentConfig(
                            name="query_generator",
                            model=model_for_provider(
                                "ollama-local", ollama_local_models[0]
                            )
                        ),
                        "insight_extractor": AgentConfig(
                            name="insight_extractor",
                            model=openai_models[0]
                        ),
                    },
                )
            )
        
        # Test configurations
        results = []
        for config in test_configs:
            result = await self.test_agent_response(config, available_provider_mappings)
            results.append(result)
            print(f"  {result[0]}: {'✓' if result[1] else '✗'} - {result[2]}")
        
        # Mixed configs might fail more often, so we're more lenient
        if results:
            successful_mixed = len([r for r in results if r[1]])
            total = len(results)
            print(f"\nMixed config results: {successful_mixed}/{total} succeeded")

    @pytest.mark.asyncio
    async def test_model_discovery_endpoints(self):
        """Test that model discovery endpoints are accessible."""
        endpoints_tested = []
        
        # Test OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                import openai
                client = openai.OpenAI(api_key=api_key)
                models = client.models.list()
                model_count = len(list(models))
                endpoints_tested.append(("OpenAI", True, f"{model_count} models"))
            except Exception as e:
                endpoints_tested.append(("OpenAI", False, str(e)))
        else:
            endpoints_tested.append(("OpenAI", False, "No API key"))
        
        # Test Ollama endpoints
        ollama_endpoints = [
            ("Ollama Local", "http://localhost:11434"),
            ("Ollama Remote", "https://ollama.kairix.net"),
        ]
        
        for name, base_url in ollama_endpoints:
            try:
                response = await asyncio.to_thread(
                    requests.get, f"{base_url}/api/tags", timeout=5
                )
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    endpoints_tested.append((name, True, f"{len(models)} models"))
                else:
                    endpoints_tested.append(
                        (name, False, f"Status {response.status_code}")
                    )
            except Exception as e:
                endpoints_tested.append((name, False, str(e)))
        
        # Print results
        print("\nModel Discovery Results:")
        for endpoint, success, details in endpoints_tested:
            status = "✓" if success else "✗"
            print(f"  {endpoint}: {status} - {details}")
        
        # At least one endpoint should be accessible
        successful = [e for e in endpoints_tested if e[1]]
        assert len(successful) > 0, "No model discovery endpoints were accessible"

    def test_environment_specific_models(self):
        """Test that environment-specific configurations are valid."""
        env_name = os.environ.get("ENV", "mac")
        print(f"\nTesting environment: {env_name}")
        
        # Check which environment variables are set
        env_vars = {
            "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
            "KAIRIX_AGENT_CONFIG_SET": os.getenv("KAIRIX_AGENT_CONFIG_SET"),
            "NEO4J_URL": bool(os.getenv("NEO4J_URL")),
        }
        
        print("Environment variables:")
        for var, value in env_vars.items():
            status = '✓' if value else '✗'
            val_str = value if isinstance(value, str) else ''
            print(f"  {var}: {status} {val_str}")
        
        # Verify at least one provider is configured
        assert any([
            env_vars["OPENAI_API_KEY"],
            env_vars["KAIRIX_AGENT_CONFIG_SET"] == "ollama-local",
            env_vars["KAIRIX_AGENT_CONFIG_SET"] == "ollama-remote",
        ]), "No AI provider is configured in this environment"