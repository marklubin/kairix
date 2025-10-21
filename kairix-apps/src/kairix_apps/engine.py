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
from kairix_core.cognition.persona import ConversationalPersona, notebook
from kairix_core.cognition.stores.sqlite_embedded_data import create_memory_shard_store
from kairix_core.embedding.nomic import NomicEmbedding
from kairix_core.prompt import system_instructions
from kairix_core.runtime.agent import AgentRuntime
from kairix_core.runtime.logging import LoggingRuntime
from kairix_core.runtime.storage import StorageRuntime
from kairix_core.util.utils import get_or_raise

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
        n_summaries = int(n_summaries_str) if n_summaries_str else 5
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

        embedding_transformer = NomicEmbedding()


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

        # Include MCP servers from config file for tool access
        mcp_servers_list = agent_runtime.mcp_servers
        logger.info(f"Configured {len(mcp_servers_list)} MCP server(s) for conversational agent")

        # Load system prompt from database
        from kairix_apps.prompt_manager import SystemPromptManager
        prompt_manager = SystemPromptManager()
        selected_prompt = prompt_manager.get_selected_prompt()

        if selected_prompt:
            # Use the selected prompt from database
            prompt_template = selected_prompt.content
            logger.info(f"Using system prompt: {selected_prompt.name} ({selected_prompt.prompt_id})")
        else:
            # Fallback to default v2 prompt if none selected
            prompt_template = prompts.conversationalist_instruction_template_v2(
                agent_name="{agent_name}", user_name="{user_name}"
            )
            logger.warning("No system prompt selected, using default v2")

        # Format the prompt with actual names
        instructions = prompt_template.format(agent_name=persona_name, user_name=user_name)

        # Append tools reference documentation
        from pathlib import Path
        tools_ref_path = Path(__file__).parent / "docs" / "AGENT_TOOLS_REFERENCE.md"
        if tools_ref_path.exists():
            tools_reference = tools_ref_path.read_text()
            instructions = f"{instructions}\n\n---\n\n{tools_reference}"
            logger.info("Appended tools reference to system prompt")
        else:
            logger.warning(f"Tools reference not found at {tools_ref_path}")

        # Append Agent Unconditional Context (if it exists)
        unconditional_context = notebook.load_unconditional_context_for_system_prompt()
        if unconditional_context:
            instructions = f"{instructions}\n\n---\n\n# YOUR UNCONDITIONAL CONTEXT\n\n{unconditional_context}"
            logger.info(f"Appended unconditional context to system prompt ({len(unconditional_context)} chars)")
        else:
            logger.info("No unconditional context found, skipping")

        conversational_agent: K_Agent = Agent(
            name="conversationalist",
            instructions=instructions,
            mcp_servers=mcp_servers_list,
            tools=[
                notebook.get_note,
                notebook.list_titles,
                notebook.save,
                notebook.get_note_content,
                notebook.maybe_note,
                notebook.search_by_tag,
                notebook.get_unconditional_context,
                notebook.update_unconditional_context,
                notebook.append_unconditional_context
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
