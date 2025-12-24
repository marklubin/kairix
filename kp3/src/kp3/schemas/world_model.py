"""World model schemas for structured state extraction."""

from pydantic import BaseModel, Field


def _empty_list_str() -> list[str]:
    return []


def _empty_list_projects() -> "list[ProjectEntry]":
    return []


def _empty_list_entities() -> "list[EntityEntry]":
    return []


class ProjectEntry(BaseModel):
    """An active project in the world model."""

    name: str = Field(description="Project name or identifier")
    status: str = Field(description="Current status (e.g., 'active', 'completed', 'blocked')")
    context: str = Field(description="Brief context about the project")


class EntityEntry(BaseModel):
    """A key entity (person, tool, place) in the world model."""

    name: str = Field(description="Entity name")
    relevance: str = Field(description="Why this entity is relevant to interactions")


class HumanBlock(BaseModel):
    """The agent's model of the user.

    Tracks values, patterns, current state, and ongoing concerns.
    """

    version: int = Field(description="Monotonically increasing version number")
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

    Tracks voice, stance, learned preferences, and relationship history.
    """

    version: int = Field(description="Monotonically increasing version number")
    voice: str = Field(
        default="", description="Communication style that works for this person"
    )
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
    """Shared environmental context.

    Tracks active projects, key entities, and situational context.
    """

    version: int = Field(description="Monotonically increasing version number")
    active_projects: list[ProjectEntry] = Field(
        default_factory=_empty_list_projects, description="Currently active projects with status"
    )
    key_entities: list[EntityEntry] = Field(
        default_factory=_empty_list_entities,
        description="People, tools, places relevant to interactions",
    )
    environmental_context: str = Field(
        default="", description="Time, location, life phase, situational context"
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
