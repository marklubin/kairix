"""Memory block definitions for Kairix agents.

Blocks can be shared across agents (same block_id) or agent-specific.
Shared blocks allow multiple agents to have a unified identity and context.
"""

from dataclasses import dataclass
from typing import ClassVar


@dataclass
class BlockDefinition:
    """Definition of a memory block to be provisioned."""

    label: str
    description: str
    initial_value: str = ""
    limit: int = 5000
    read_only: bool = False


class SharedBlocks:
    """Block definitions shared across the Kairix entity (all agents).

    These blocks define the coherent identity that spans conversational,
    reflector, and future agents.
    """

    PERSONA = BlockDefinition(
        label="persona",
        description="Core identity, tone, and behavioral guidelines for the entity.",
        initial_value="""Name: [Agent name - update this field]

This block defines your core identity and personality. Update it to include:
- Your name and any titles
- Your communication style and tone
- Your core purpose and values
- Any behavioral guidelines or protocols

The agent should maintain this identity across all interactions and update it as the relationship with the user evolves.""",
    )

    HUMAN = BlockDefinition(
        label="human",
        description="Information about the human (user) the agent is interacting with.",
        initial_value="""This is my section of core memory devoted to information about the human.
I don't yet know anything about them.
What's their name? Where are they from? What do they do? Who are they?
I should update this memory over time as I interact with the human and learn more about them.""",
    )

    # All shared blocks that define the entity's identity
    ALL: ClassVar[list[BlockDefinition]] = [PERSONA, HUMAN]


class AgentSpecificBlocks:
    """Block definitions specific to individual agents (not shared)."""

    FOCUS = BlockDefinition(
        label="focus",
        description="Reminds you of your current focus and keeps you oriented to the task at hand.",
        initial_value="No current focus set.",
    )

    LAST_SESSION_SUMMARY = BlockDefinition(
        label="last_session_summary",
        description="Summary of the most recent conversation session, providing continuity context.",
        initial_value="No previous session recorded yet.",
    )

    BACKGROUND_INSIGHTS = BlockDefinition(
        label="background_insights",
        description="Background context and insights retrieved to support the current conversation. This block is automatically updated by the BackgroundInsights agent when conversation topics shift. Use this information to provide more informed, contextually relevant responses. When the content seems stale or irrelevant to the current topic, the BackgroundInsights agent will refresh it.",
        initial_value="No background insights loaded yet.",
        limit=5000,
    )
