from agents import OpenAIProvider

from kairix_core.configuration.types import ProviderName, AgentConfigurationSet, AgentConfig
from kairix_core.configuration.utils import model_for_provider

provider_mappings: dict[ProviderName, OpenAIProvider] = {
    "ollama-remote": OpenAIProvider(base_url="https://ollama.kairix.net/v1"),
    "ollama-local": OpenAIProvider(base_url="http://localhost:11434/v1"),
}


configuration_sets = {
    "openai": AgentConfigurationSet(
        name="openai-default",
        default_provider="openai",
        description="Default openai api backed configuration.",
        agent_configs={
            "conversationalist": AgentConfig(
                name="conversationalist",
                model="gpt-4.1"
            ),
            "query_generator": AgentConfig(
                name="query_generator",
                model="gpt-4.1-nano"
            ),
            "insight_extractor": AgentConfig(
                name="insight_extractor",
                model="gpt-4.1-nano"
            ),
            "default": AgentConfig(
                name="default",
                model="gpt-4.1-nano",
                temperature=1.0,
                max_tokens=16000
            )
        },
    ),
    "ollama-local": AgentConfigurationSet(
        name="ollama-local",
        default_provider="ollama-local",
        description="Macbook ollama.",
        agent_configs={
            "conversationalist": AgentConfig(
                name="conversationalist",
                model=model_for_provider(
                    "ollama-local",
                    "phi3.5:3.8b-mini-instruct-q4_0",  # Fast and accurate model
                ),
                temperature=0.8,  # Lower temperature for more focused responses
                max_tokens=250,
            ),
            "query_generator": AgentConfig(
                name="query_generator",
                model=model_for_provider(
                    "ollama-local",
                    "phi3.5:3.8b-mini-instruct-q4_0",  # Fast and accurate model
                ),
                temperature=0.3,  # Very low for structured output
                max_tokens=50,
            ),
            "insight_extractor": AgentConfig(
                name="insight_extractor",
                model=model_for_provider(
                    "ollama-local",
                    "phi3.5:3.8b-mini-instruct-q4_0",  # Fast and accurate model
                ),
                temperature=0.3,
                max_tokens=100,
            ),
            "default": AgentConfig(
                name="default",
                model=model_for_provider(
                    "ollama-local",
                    "phi3.5:3.8b-mini-instruct-q4_0",  # Fast and accurate model
                ),
            )
        },
    ),
    "ollama-remote": AgentConfigurationSet(
        name="ollama-remote",
        default_provider="ollama-remote",
        description="Cayucos ollama.",
        agent_configs={
            "conversationalist": AgentConfig(
                name="conversationalist",
                model=model_for_provider(
                    "ollama-remote",
                    "qwen3:4b"
                ),
            ),
            "query_generator": AgentConfig(
                name="query_generator",
                model=model_for_provider(
                    "ollama-remote",
                    "qwen3:4b"
                ),
            ),
            "insight_extractor": AgentConfig(
                name="insight_extractor",
                model=model_for_provider(
                    "ollama-remote",
                    "qwen3:4b"
                ),
            ),
            "default": AgentConfig(
                name="default",
                model=model_for_provider(
                    "ollama-remote",
                    "qwen3:4b"
                ),
            )
        },
    ),
}
