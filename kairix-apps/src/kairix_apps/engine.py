import kairix_core.prompt.agent_prompts as prompts
from agents import Agent
from kairix_core.cognition.perceptor.conversation_history import (
    ConversationHistoryPerceptor,
)
from kairix_core.cognition.perceptor.environmental_context import (
    EnvironmentalContextPerceptor,
)
from kairix_core.cognition.perceptor.incremental_reflection import (
    IncrementalSummarizationPerceptor,
)
from kairix_core.cognition.perceptor.summary_insight import SummaryInsightPerceptor
from kairix_core.cognition.persona import ConversationalPersona
from kairix_core.prompt import system_instructions
from kairix_core.runtime.agent import AgentRuntime
from kairix_core.runtime.logging import LoggingRuntime
from kairix_core.runtime.neo4j import Neo4jRuntime
from kairix_core.util.utils import get_or_raise
from sentence_transformers import SentenceTransformer

logger = LoggingRuntime().logger

agent_runtime = AgentRuntime()
neo4j_runtime = Neo4jRuntime()


class KairixEngine:
    @staticmethod
    def conversational_persona_for_environment() -> ConversationalPersona:
        import os

        os.system("clear")

        config_set_key = os.getenv("KAIRIX_AGENT_CONFIGURATION_SET_KEY")
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

        embedding_model = get_or_raise("KAIRIX_EMBEDDER_MODEL")
        embedding_device = get_or_raise("KAIRIX_EMBEDDER_DEVICE")
        embedding_transformer = SentenceTransformer(
            embedding_model, device=embedding_device
        )

        insight = SummaryInsightPerceptor(
            agent_runtime,
            embedded_sumary_store=neo4j_runtime.embedded_memory_shard_store,
            k_memories=n_summaries,
        )

        environmental_content = EnvironmentalContextPerceptor(
            cache_duration_seconds=300
        )

        conversation_history = ConversationHistoryPerceptor(
            agent_id=persona_name,
            window_size=20
        )

        incremental_summary = IncrementalSummarizationPerceptor(
            runtime=agent_runtime,
            summarization_interval=20,
            agent=Agent(
                name="incremental_summarizer",
                instructions=system_instructions.self_reflective_summary_minimal,
            ),
            embedder=embedding_transformer,
        )

        agent = Agent(
            name="conversationalist",
            instructions=prompts.conversationalist_instruction_template_v1(
                agent_name=persona_name, user_name=user_name
            ),
        )

        logger.info("Spawning Persona...")
        return ConversationalPersona(
            persona_name=persona_name,
            user_name=user_name,
            runtime=agent_runtime,
            perceptors=[
                insight,
                environmental_content,
                conversation_history,
                incremental_summary,
            ],
            actuating_agent=agent,
            reflection_perceptors=[conversation_history, incremental_summary],
        )
