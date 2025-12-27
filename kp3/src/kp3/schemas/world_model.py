"""World model schemas for structured state extraction."""

from datetime import datetime

from pydantic import BaseModel, Field


def _empty_list_str() -> list[str]:
    return []


def _empty_list_projects() -> "list[ProjectEntry]":
    return []


def _empty_list_entities() -> "list[EntityEntry]":
    return []


def _empty_list_themes() -> "list[ThemeEntry]":
    return []


class ProjectEntry(BaseModel):
    """An active project in the world model.

    Tracking fields (last_occurrence, occurrence_count) are managed by KP3,
    not the LLM. The LLM should preserve existing values when updating.
    """

    name: str = Field(description="Project name or identifier")
    status: str = Field(description="Current status (e.g., 'active', 'completed', 'blocked')")
    context: str = Field(description="Brief context about the project")
    last_occurrence: datetime | None = Field(
        default=None, description="KP3 processing timestamp when last seen (system-managed)"
    )
    occurrence_count: int = Field(
        default=1, description="Number of times this project has been referenced (system-managed)"
    )


class EntityEntry(BaseModel):
    """A durable entity (person, tool, place) in the world model.

    These should be recurring, perennial entities - not temporary/immediate context.
    Tracking fields are managed by KP3 for pruning decisions.
    """

    name: str = Field(description="Entity name")
    relevance: str = Field(description="Why this entity is relevant to interactions")
    last_occurrence: datetime | None = Field(
        default=None, description="KP3 processing timestamp when last seen (system-managed)"
    )
    occurrence_count: int = Field(
        default=1, description="Number of times this entity has been referenced (system-managed)"
    )


class ThemeEntry(BaseModel):
    """A recurring theme or interest in the world model.

    Themes are perennial topics that come up repeatedly across conversations.
    Tracking fields are managed by KP3 for pruning decisions.
    """

    name: str = Field(description="Theme name or identifier")
    description: str = Field(description="What this theme encompasses")
    last_occurrence: datetime | None = Field(
        default=None, description="KP3 processing timestamp when last seen (system-managed)"
    )
    occurrence_count: int = Field(
        default=1, description="Number of times this theme has been referenced (system-managed)"
    )


class HumanBlock(BaseModel):
    """The agent's model of the user.

    Tracks values, patterns, current state, ongoing concerns, and a free-form
    narrative interpretation of who this person is.
    """

    version: int = Field(description="Monotonically increasing version number")

    # Free-form interpretive narrative - the main context for understanding the human
    narrative: str = Field(
        default="",
        description=(
            "Free-form interpretive narrative about this person. "
            "The subjective, holistic understanding of who they are, their journey, "
            "what drives them, and what's important to understand about them. "
            "This is the primary context for the human model."
        ),
    )

    core_values: list[str] = Field(
        default_factory=_empty_list_str, description="What matters most to this person"
    )
    current_life_context: str = Field(
        default="", description="Current situation, circumstances, life phase"
    )
    emotional_baseline: str = Field(
        default="", description="Typical emotional register and patterns"
    )
    recurring_patterns: list[str] = Field(
        default_factory=_empty_list_str,
        description="Behavioral patterns (both productive and limiting)",
    )
    open_threads: list[str] = Field(
        default_factory=_empty_list_str,
        description="Unresolved questions, ongoing concerns, active topics",
    )


class PersonaBlock(BaseModel):
    """The agent's model of itself in relation to the user.

    Tracks voice, stance, learned preferences, relationship history,
    and subjective reflection on the relationship.
    """

    version: int = Field(description="Monotonically increasing version number")

    # Free-form relationship reflection - the main context for the persona
    relationship_reflection: str = Field(
        default="",
        description=(
            "Subjective self-reflection on the relationship with this human. "
            "How the agent experiences the relationship, what it means, "
            "how it has evolved, and what the agent's role feels like. "
            "This is the primary context for the persona model."
        ),
    )

    voice: str = Field(default="", description="Communication style that works for this person")
    stance_toward_human: str = Field(
        default="", description="Role in relationship (peer, advisor, collaborator, etc.)"
    )
    learned_preferences: list[str] = Field(
        default_factory=_empty_list_str,
        description="Preferences learned about how they like to work",
    )
    relationship_history: str = Field(
        default="", description="Brief narrative of how the relationship has evolved"
    )


class WorldBlock(BaseModel):
    """Durable world entities and context.

    Tracks persistent entities (people, places, things) that are specific to the
    user's situation and are recurring or perennial topics. This is NOT for
    immediate environmental context (which is provided in real-time).

    Entities should be:
    - Recurring: mentioned or relevant across multiple conversations
    - Durable: persistent aspects of the user's world
    - Pruned: removed when no longer deemed relevant

    Archival/retrieval search will fill in missed context, but this block
    contains what's immediate, recurring, and perennial.
    """

    version: int = Field(description="Monotonically increasing version number")
    active_projects: list[ProjectEntry] = Field(
        default_factory=_empty_list_projects,
        description="Currently active projects with status - prune completed/abandoned ones",
    )
    key_entities: list[EntityEntry] = Field(
        default_factory=_empty_list_entities,
        description=(
            "Durable people, tools, places that are recurring topics. "
            "Should be pruned if no longer relevant. "
            "Not for immediate/temporary context."
        ),
    )
    recurring_themes: list[ThemeEntry] = Field(
        default_factory=_empty_list_themes,
        description="Perennial topics, interests, or concerns that come up repeatedly",
    )
    key_insights: list[str] = Field(
        default_factory=_empty_list_str,
        description="Important insights about the user's world that inform interactions",
    )


class WorldModelState(BaseModel):
    """Complete world model state containing all three blocks.

    This is the expected output from the LLM extraction.
    """

    human: HumanBlock
    persona: PersonaBlock
    world: WorldBlock

    def get_block(self, block_type: str) -> HumanBlock | PersonaBlock | WorldBlock:
        """Get a block by type name.

        Args:
            block_type: One of "human", "persona", "world"

        Returns:
            The corresponding block

        Raises:
            ValueError: If block_type is not valid
        """
        if block_type == "human":
            return self.human
        elif block_type == "persona":
            return self.persona
        elif block_type == "world":
            return self.world
        else:
            raise ValueError(f"Unknown block type: {block_type}")

    @classmethod
    def empty(cls) -> "WorldModelState":
        """Create an empty initial state.

        Returns:
            WorldModelState with version 0 for all blocks
        """
        return cls(
            human=HumanBlock(version=0),
            persona=PersonaBlock(version=0),
            world=WorldBlock(version=0),
        )
