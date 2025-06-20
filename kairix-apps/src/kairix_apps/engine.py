import kairix_core.prompt.agent_prompts as prompts
from agents import Agent
from kairix_core.cognition.perceptor.environmental_context import (
    EnvironmentalContextPerceptor,
)
from kairix_core.cognition.perceptor.summary_insight import SummaryInsightPerceptor
from kairix_core.cognition.persona import ConversationalPersona
from kairix_core.cognition.stores.summary_store import SummaryStore
from kairix_core.runtime.agent import AgentRuntime
from kairix_core.runtime.logging import LoggingRuntime

logger = LoggingRuntime().logger

agent_runtime = AgentRuntime()

class KairixEngine:
    @staticmethod
    def conversational_persona_for_environment() -> ConversationalPersona:
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

        store = SummaryStore(store_url=neo4j_url)
        insight = SummaryInsightPerceptor(
            agent_runtime,
            memory_provider=lambda query, k: [
                content for content, score in store.search(query, k)
            ],
            k_memories=n_summaries,
        )

        # Create environmental context perceptor
        environmental_content = EnvironmentalContextPerceptor(
            cache_duration_seconds=300
        )  # 5 minute cache

        agent = Agent(
            name="conversationalist",
            instructions=prompts.conversationalist_instruction_template_v1(
                agent_name=persona_name, user_name=user_name
            ),
        )
        return ConversationalPersona(
            persona_name=persona_name,
            user_name=user_name,
            runtime=agent_runtime,
            perceptors=[insight, environmental_content],
            actuating_agent=agent,
            reflection_perceptors=[],
        )
