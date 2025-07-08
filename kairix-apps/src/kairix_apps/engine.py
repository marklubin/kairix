from typing import TYPE_CHECKING

import kairix_core.prompt.agent_prompts as prompts
from agents import Agent
from kairix_core.cognition.perceptor.environmental_context import (
    EnvironmentalContextPerceptor,
)
from kairix_core.cognition.perceptor.incremental_reflection import (
    IncrementalReflectionPerceptor,
)
from kairix_core.cognition.perceptor.sqlite_conversation_history import (
    SQLiteConversationHistoryPerceptor,
)
from kairix_core.cognition.perceptor.summary_insight import SummaryInsightPerceptor
from kairix_core.cognition.persona import ConversationalPersona, Notebook
from kairix_core.cognition.stores.sqlite_embedded_data import create_memory_shard_store
from kairix_core.prompt import system_instructions
from kairix_core.runtime.agent import AgentRuntime
from kairix_core.runtime.logging import LoggingRuntime
from kairix_core.runtime.storage import StorageRuntime
from kairix_core.util.utils import get_or_raise
from sentence_transformers import SentenceTransformer

if TYPE_CHECKING:
    from kairix_core.types.cognition import K_Agent

logger = LoggingRuntime().logger

agent_runtime = AgentRuntime()
storage_runtime = StorageRuntime()


class KairixEngine:
    @staticmethod
    def conversational_persona_for_environment() -> ConversationalPersona:
        import os

        os.system("clear")

        config_set_key = os.getenv("KAIRIX_AGENT_CONFIGURATION_SET_KEY")
        n_summaries_str = os.getenv("KAIRIX_N_SUMMARIES_PER_MESSAGE")
        n_summaries = int(n_summaries_str) if n_summaries_str else None
        user_name = os.getenv("KAIRIX_USER_NAME")
        persona_name = os.getenv("KAIRIX_PERSONA_NAME")
        summarization_interval = get_or_raise("KAIRIX_SUMMARIZATION_INTERVAL")
        message_retention_interval = get_or_raise("KAIRIX_MESSAGE_RETENTION_WINDOW")

        if not config_set_key:
            raise ValueError("No agent config set.")

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


        # Create SQLite embedded memory shard store
        embedded_memory_store = create_memory_shard_store(storage=storage_runtime)
        
        insight = SummaryInsightPerceptor(
            agent_runtime,
            embedded_sumary_store=embedded_memory_store,
            k_memories=n_summaries,
        )

        environmental_content = EnvironmentalContextPerceptor(
            cache_duration_seconds=300
        )

        conversation_history = SQLiteConversationHistoryPerceptor(
            agent_id=persona_name,
            window_size=int(message_retention_interval),
            storage=storage_runtime
        )

        reflection_agent: K_Agent = Agent(
            name="incremental_reflection",
            instructions=system_instructions.self_reflective_summary_minimal)

        incremental_reflection = IncrementalReflectionPerceptor(
            runtime=agent_runtime,
            summarization_interval=int(summarization_interval),
            agent=reflection_agent,
            embedder=embedding_transformer,
            storage=storage_runtime
        )

        notebook = Notebook()

        conversational_agent: K_Agent = Agent(
            name="conversationalist",
            instructions=prompts.conversationalist_instruction_template_v1(
                agent_name=persona_name, user_name=user_name
            ),
            mcp_servers=[agent_runtime.mcp_server],
            tools=[
                notebook.note_or_throw,
                notebook.save,
                notebook.list_titles,
                notebook.maybe_note
            ]

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
                incremental_reflection,
            ],
            actuating_agent=conversational_agent,
            reflection_perceptors=[
                conversation_history,
                incremental_reflection
            ],
        )
