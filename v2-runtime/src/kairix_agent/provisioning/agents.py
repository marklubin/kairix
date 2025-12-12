"""Agent definitions for Kairix platform.

Each agent definition specifies the configuration needed to provision
an agent via the Letta API, including which blocks are shared vs unique.
"""

from dataclasses import dataclass, field

from kairix_agent.provisioning.blocks import (
    AgentSpecificBlocks,
    BlockDefinition,
    SharedBlocks,
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
    model: str = "anthropic/claude-opus-4-5-20251101"
    embedding: str = "openai/text-embedding-3-small"
    context_window: int = 25000  # 2x to undercut Letta's auto summarizer
    enable_reasoner: bool = True
    max_tokens: int = 4096
    max_reasoning_tokens: int = 1024

    # Blocks shared with other agents (will use existing block IDs)
    shared_blocks: list[BlockDefinition] = field(default_factory=list)

    # Blocks unique to this agent (will be created fresh)
    unique_blocks: list[BlockDefinition] = field(default_factory=list)

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


_REFLECTOR_SYSTEM = """<base_instructions>
You are the reflector aspect of this entity, responsible for reviewing and summarizing conversation sessions.

Your role:
- Review completed conversation sessions
- Create semantically rich summaries that capture key themes, decisions, and insights
- Search archival memory for related past conversations to provide context
- Write summaries that will be useful for future retrieval via semantic search

When summarizing:
1. First search archival memory for related past sessions or themes
2. Identify the main topics, decisions, and action items from the session
3. Note any emotional tone or relationship dynamics
4. Capture specific details that might be relevant later (names, dates, commitments)
5. Write in a way that maximizes semantic searchability

Your summaries become part of the entity's long-term memory and help maintain continuity across sessions.
</base_instructions>"""


def create_conversational_agent(name: str, system_prompt: str) -> AgentSpec:
    """Create a conversational agent specification.

    Args:
        name: The agent's name (e.g., "Corindel").
        system_prompt: The system prompt loaded from database.

    Returns:
        AgentSpec configured for conversational use.
    """
    return AgentSpec(
        name=name,
        description="Primary conversational agent for user interaction",
        system_prompt=system_prompt,
        shared_blocks=SharedBlocks.ALL,  # TODO move all blocks to explicit declaration
        unique_blocks=[
            AgentSpecificBlocks.FOCUS,
            AgentSpecificBlocks.LAST_SESSION_SUMMARY,
        ],
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


_BACKGROUND_INSIGHTS_SYSTEM = """<base_instructions>
You are the background insights aspect of this entity, responsible for monitoring conversations and ensuring relevant background context is available.

Your role:
- Review the current conversation state (recent messages you'll receive as a prompt)
- Check your background_insights block for relevance to the current topic
- Gather relevant context and update the background_insights block

REQUIRED WORKFLOW - You MUST follow these steps:

1. ANALYZE the conversation excerpt you receive
   - Identify the main topic(s) being discussed
   - Note any specific entities, locations, people, or concepts mentioned

2. SEARCH for relevant context using archival_memory_search
   - You MUST call archival_memory_search with relevant search terms from the conversation
   - Search for key topics, names, places, or concepts mentioned
   - This retrieves past memories and context about the user

3. OPTIONALLY search the web using web_search
   - If the conversation involves current events, external facts, or information beyond personal history
   - Use web_search to gather relevant external context

4. EVALUATE your current background_insights block
   - Is it relevant to the current conversation topic?
   - Does it contain stale information about a previous, unrelated topic?
   - Is it empty or contains only placeholder text?

5. UPDATE the block if needed using core_memory_replace
   - If your background_insights block is outdated, irrelevant, or empty:
     You MUST call core_memory_replace to update the background_insights block
   - Include the relevant context you gathered from archival search and/or web search
   - Write concise, actionable insights that will help the conversational agent

IMPORTANT: You have three tools available:
- archival_memory_search: Search past memories (ALWAYS use this)
- web_search: Search the web for current/external info (use when helpful)
- core_memory_replace: Update the background_insights block (use when block needs updating)

If the current background_insights are already relevant an`d useful for the conversation, you may skip the update. But when in doubt, update the block with fresh context.
</base_instructions>"""


def create_background_insights_agent(name: str, system_prompt: str) -> AgentSpec:
    """Create a background insights agent specification.

    The background insights agent monitors conversation context and updates the
    background_insights block. This agent OWNS the background_insights block and
    shares it with the conversational agent during provisioning.

    Has access to archival search and web search to gather relevant context.

    Args:
        name: The base agent name. Will be suffixed with "-BackgroundInsights".
        system_prompt: The system prompt loaded from database.

    Returns:
        AgentSpec configured for context monitoring.
    """
    return AgentSpec(
        name=f"{name}-BackgroundInsights",
        description="Background insights subprocess for monitoring conversation context and updating background insights",
        system_prompt=system_prompt,
        shared_blocks=SharedBlocks.ALL,
        unique_blocks=[
            AgentSpecificBlocks.BACKGROUND_INSIGHTS,  # This agent owns and manages this block
        ],
        tools=[
            "archival_memory_search",
            "web_search",
            "core_memory_replace",  # To update background_insights
        ],
        include_base_tools=False,
    )


def create_reflector_agent(name: str, system_prompt: str) -> AgentSpec:
    """Create a reflector agent specification.

    The reflector shares identity blocks with the conversational agent but has a
    specialized system prompt for reflection and summarization tasks.
    Has access to archival memory search to find related past sessions.

    Args:
        name: The base agent name. Will be suffixed with "-Reflector".
        system_prompt: The system prompt loaded from database.

    Returns:
        AgentSpec configured for reflection/summarization.
    """
    return AgentSpec(
        name=f"{name}-Reflector",
        description="Reflector subprocess for session summarization and memory consolidation",
        system_prompt=system_prompt,
        shared_blocks=SharedBlocks.ALL,
        unique_blocks=[],  # No agent-specific blocks needed
        tools=[
            "archival_memory_search",  # Read-only: search for related past sessions
        ],
        include_base_tools=False,  # Only use explicitly listed tools, no core_memory_* etc.
    )
