"""Memory block definitions for Kairix agents.

All blocks are provisioned for every conversational agent.
"""

from dataclasses import dataclass


@dataclass
class BlockDefinition:
    """Definition of a memory block to be provisioned."""

    label: str
    description: str
    initial_value: str = ""
    limit: int = 5000
    read_only: bool = False


# All default blocks provisioned for every conversational agent
DEFAULT_BLOCKS: list[BlockDefinition] = [
    BlockDefinition(
        label="persona",
        description="Core identity, tone, and behavioral guidelines for the entity.",
        initial_value="""Name: [Agent name - update this field]

This block defines your core identity and personality. Update it to include:
- Your name and any titles
- Your communication style and tone
- Your core purpose and values
- Any behavioral guidelines or protocols

The agent should maintain this identity across all interactions and update it as the relationship with the user evolves.""",
    ),
    BlockDefinition(
        label="human",
        description="Information about the human (user) the agent is interacting with.",
        initial_value="""This is my section of core memory devoted to information about the human.
I don't yet know anything about them.
What's their name? Where are they from? What do they do? Who are they?
I should update this memory over time as I interact with the human and learn more about them.""",
    ),
    BlockDefinition(
        label="world",
        description="Durable world context: active projects, key entities, recurring themes, and insights. This block is managed by KP3 and updated via world model extraction. Contains structured information about the user's persistent context that informs conversations.",
        initial_value="No world context loaded yet.",
        limit=20000,  # Larger limit for structured world data
    ),
    BlockDefinition(
        label="focus",
        description="Reminds you of your current focus and keeps you oriented to the task at hand.",
        initial_value="No current focus set.",
    ),
    BlockDefinition(
        label="last_session_summary",
        description="Summary of the most recent conversation session, providing continuity context.",
        initial_value="No previous session recorded yet.",
    ),
    BlockDefinition(
        label="background_insights",
        description="Background context and insights retrieved to support the current conversation. This block is automatically updated by the BackgroundInsights agent when conversation topics shift. Use this information to provide more informed, contextually relevant responses. When the content seems stale or irrelevant to the current topic, the BackgroundInsights agent will refresh it.",
        initial_value="No background insights loaded yet.",
        limit=5000,
    ),
]


def get_block_by_label(label: str) -> BlockDefinition:
    """Look up a BlockDefinition by its label.

    Args:
        label: The block label (e.g., "persona", "focus").

    Returns:
        The BlockDefinition.

    Raises:
        KeyError: If no block with that label exists.
    """
    for block in DEFAULT_BLOCKS:
        if block.label == label:
            return block
    msg = f"Unknown block label: {label}"
    raise KeyError(msg)
