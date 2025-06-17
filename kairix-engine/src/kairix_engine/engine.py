import logging

from agents import OpenAIProvider, set_default_openai_api
from cognition_engine.configuration.runner import (
    AgentConfig,
    AgentConfigurationSet,
    CognitionAgentRunner,
    ProviderName,
    model_for_provider,
)
from cognition_engine.perceptor.environmental_context import (
    EnvironmentalContextPerceptor,
)
from cognition_engine.perceptor.summary_insight import SummaryInsightPerceptor
from cognition_engine.stores.summary_store import SummaryStore
from cognition_engine.utils import Claude

from kairix_engine.basic_chat import Chat

logger = logging.getLogger(__name__)

# Use chat completions API instead of responses API for compatibility
set_default_openai_api("chat_completions")


available_provider_mappings: dict[ProviderName, OpenAIProvider] = {
    "ollama-remote": OpenAIProvider(base_url="https://ollama.kairix.net/v1"),
    "ollama-local": OpenAIProvider(base_url="http://localhost:11434/v1"),
}


system_configuration_environments = {
    "openai": AgentConfigurationSet(
        name="openai-default",
        default_provider="openai",
        description="Default openai api backed configuration.",
        agent_configs={
            "conversationalist": AgentConfig(name="conversationalist", model="gpt-4.1"),
            "query_generator": AgentConfig(
                name="query_generator", model="gpt-4.1-nano"
            ),
            "insight_extractor": AgentConfig(
                name="insight_extractor", model="gpt-4.1-nano"
            ),
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
                    "llama3.2:1b",  # Fast and accurate model
                ),
                temperature=0.3,  # Lower temperature for more focused responses
                max_tokens=500,
            ),
            "query_generator": AgentConfig(
                name="query_generator",
                model=model_for_provider(
                    "ollama-local",
                    "llama3.2:1b",  # Fast and accurate model
                ),
                temperature=0.1,  # Very low for structured output
                max_tokens=256,
            ),
            "insight_extractor": AgentConfig(
                name="insight_extractor",
                model=model_for_provider(
                    "ollama-local",
                    "llama3.2:1b",  # Fast and accurate model
                ),
                temperature=0.3,
                max_tokens=256,
            ),
        },
    ),
    "ollama-remote": AgentConfigurationSet(
        name="ollama-remote",
        default_provider="ollama-remote",
        description="Cayucos ollama.",
        agent_configs={
            "conversationalist": AgentConfig(
                name="conversationalist",
                model=model_for_provider("ollama-remote", "q3r:latest"),
            ),
            "query_generator": AgentConfig(
                name="query_generator",
                model=model_for_provider("ollama-remote", "q3r:latest"),
            ),
            "insight_extractor": AgentConfig(
                name="insight_extractor",
                model=model_for_provider("ollama-remote", "q3r:latest"),
            ),
        },
    ),
}


class KairixEngine:
    @staticmethod
    @Claude
    def get_chat_for_environment() -> Chat:
        import os

        config_set_key = os.getenv("KAIRIX_AGENT_CONFIG_SET")
        neo4j_url = os.getenv("NEO4J_URL")
        n_summaries_str = os.getenv("KAIRIX_N_SUMMARIES_PER_MESSAGE")
        n_summaries = int(n_summaries_str) if n_summaries_str else None
        user_name = os.getenv("KAIRIX_USER_NAME")
        persona_name = os.getenv("KAIRIX_PERSONA_NAME")

        if not config_set_key:
            raise ValueError("No agent config set.")

        if not neo4j_url:
            raise ValueError("Missing Neo4j config.")

        if not n_summaries:
            raise ValueError("Failed to specify number of summaries,")

        if not user_name:
            raise ValueError("Failed to set user name.")

        if not persona_name:
            raise ValueError("Failed to set persona name.")

        if config_set_key not in system_configuration_environments:
            raise ValueError(f"Unknown environment configuration: {config_set_key}")

        logger.info(f"Using agent configuration config set key, {config_set_key}.")
        config_set = system_configuration_environments[config_set_key]
        runner = CognitionAgentRunner(config_set, available_provider_mappings)

        store = SummaryStore(store_url=neo4j_url)
        perceptor = SummaryInsightPerceptor(
            runner,
            memory_provider=lambda query, k: [
                content for content, score in store.search(query, k)
            ],
            k_memories=n_summaries,
        )

        # Create environmental context perceptor
        environmental_perceptor = EnvironmentalContextPerceptor(
            cache_duration_seconds=300  # 5 minute cache
        )

        return Chat(
            user_name=user_name,
            agent_name=persona_name,
            runner=runner,
            perceptor=perceptor,
            history_perceptor=history_perceptor,
            environmental_perceptor=environmental_perceptor,
        )
