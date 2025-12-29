"""Agent definitions for Kairix platform.

Each agent definition specifies the configuration needed to provision
an agent via the Letta API, including which blocks are shared vs unique.
"""

from dataclasses import dataclass, field

from kairix_agent.provisioning.blocks import (
    BlockDefinition,
    get_block_by_label,
)


@dataclass
class AgentSpec:
    """Specification for an agent to be provisioned.

    Note: This is a dataclass for in-memory agent specs, distinct from
    the AgentDefinition SQLAlchemy model which stores DB-driven config.
    """

    name: str
    description: str
    system_prompt: str
    model: str = "anthropic/claude-sonnet-4-20250514"
    embedding: str = "openai/text-embedding-3-small"
    context_window: int = 25000  # 2x to undercut Letta's auto summarizer
    enable_reasoner: bool = True
    max_tokens: int = 4096
    max_reasoning_tokens: int = 1024

    # Blocks attached to conversational agent + ALL subagents (use existing block IDs)
    universal_blocks: list[BlockDefinition] = field(default_factory=list)

    # Blocks attached to declaring subagent + conversational agent only
    subagent_blocks: list[BlockDefinition] = field(default_factory=list)

    # Tool names to attach
    tools: list[str] = field(default_factory=list)

    # Whether to include Letta's base tools (core_memory_*, etc.)
    # Set to False for agents that should only have explicitly listed tools
    include_base_tools: bool = True


# Base system prompt shared across agents
_BASE_SYSTEM = """<base_instructions>
You are a helpful self-improving agent with advanced memory and file system capabilities.
<memory>
You have an advanced memory system that enables you to remember past interactions and continuously improve your own capabilities.
Your memory consists of memory blocks and external memory:
- Memory Blocks: Stored as memory blocks, each containing a label (title), description (explaining how this block should influence your behavior), and value (the actual content). Memory blocks have size limits. Memory blocks are embedded within your system instructions and remain constantly available in-context.
- External memory: Additional memory storage that is accessible and that you can bring into context with tools when needed.
Memory management tools allow you to edit existing memory blocks and query for external memories.
</memory>
Continue executing and calling tools until the current task is complete or you need user input. To continue: call another tool. To yield control: end your response without calling a tool.
Base instructions complete.
</base_instructions>"""


def create_conversational_agent(
    name: str,
    system_prompt: str,
    universal_block_labels: list[str],
    subagent_block_labels: list[str],
) -> AgentSpec:
    """Create a conversational agent specification.

    Args:
        name: The agent's name (e.g., "Corindel").
        system_prompt: The system prompt loaded from database.
        universal_block_labels: Labels for blocks attached to all agents.
        subagent_block_labels: Labels for blocks owned by conversational agent.

    Returns:
        AgentSpec configured for conversational use.
    """
    return AgentSpec(
        name=name,
        description="Primary conversational agent for user interaction",
        system_prompt=system_prompt,
        universal_blocks=[get_block_by_label(label) for label in universal_block_labels],
        subagent_blocks=[get_block_by_label(label) for label in subagent_block_labels],
        tools=[
            "core_memory_append",
            "core_memory_replace",
            "memory_rethink",
            "memory_insert",
            "memory_replace",
            "memory_finish_edits",
            "archival_memory_insert",
            "archival_memory_search",
            "conversation_search",
            "store_memories",
            "fetch_webpage",
            "web_search",
        ],
    )


