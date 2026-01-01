"""Agent definitions for Kairix platform.

Each agent definition specifies the configuration needed to provision
an agent via the Letta API.
"""

from dataclasses import dataclass, field

from kairix_agent.provisioning.blocks import (
    DEFAULT_BLOCKS,
    BlockDefinition,
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

    # All blocks attached to this agent
    blocks: list[BlockDefinition] = field(default_factory=list)

    # Tool names to attach
    tools: list[str] = field(default_factory=list)

    # Whether to include Letta's base tools (core_memory_*, etc.)
    # Set to False for agents that should only have explicitly listed tools
    include_base_tools: bool = True


def create_conversational_agent(
    name: str,
    system_prompt: str,
) -> AgentSpec:
    """Create a conversational agent specification.

    Args:
        name: The agent's name (e.g., "Corindel").
        system_prompt: The system prompt loaded from database.

    Returns:
        AgentSpec configured for conversational use with all default blocks.
    """
    return AgentSpec(
        name=name,
        description="Primary conversational agent for user interaction",
        system_prompt=system_prompt,
        blocks=list(DEFAULT_BLOCKS),  # All default blocks
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
