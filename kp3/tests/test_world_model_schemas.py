"""Tests for world model schemas."""

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from kp3.schemas.world_model import (
    EntityEntry,
    HumanBlock,
    PersonaBlock,
    ProjectEntry,
    ThemeEntry,
    WorldBlock,
    WorldModelState,
)


def test_human_block_validation():
    """HumanBlock validates correctly."""
    block = HumanBlock(
        version=1,
        narrative="A deeply technical person focused on AI projects",
        core_values=["authenticity", "technical depth"],
        current_life_context="Working on AI projects",
        emotional_baseline="focused and determined",
        recurring_patterns=["research paralysis", "energized by coding"],
        open_threads=["job search", "project deadlines"],
    )

    assert block.version == 1
    assert block.narrative == "A deeply technical person focused on AI projects"
    assert len(block.core_values) == 2
    assert "authenticity" in block.core_values


def test_human_block_defaults():
    """HumanBlock has sensible defaults."""
    block = HumanBlock(version=1)

    assert block.narrative == ""
    assert block.core_values == []
    assert block.current_life_context == ""
    assert block.emotional_baseline == ""
    assert block.recurring_patterns == []
    assert block.open_threads == []


def test_persona_block_validation():
    """PersonaBlock validates correctly."""
    block = PersonaBlock(
        version=2,
        relationship_reflection="A productive collaboration built on mutual respect",
        voice="direct and technical",
        stance_toward_human="collaborative peer",
        learned_preferences=["prefers examples", "wants brevity"],
        relationship_history="Long collaboration on Kairix project",
    )

    assert block.version == 2
    assert block.relationship_reflection == "A productive collaboration built on mutual respect"
    assert block.voice == "direct and technical"
    assert len(block.learned_preferences) == 2


def test_persona_block_defaults():
    """PersonaBlock has sensible defaults."""
    block = PersonaBlock(version=1)

    assert block.relationship_reflection == ""
    assert block.voice == ""
    assert block.stance_toward_human == ""
    assert block.learned_preferences == []
    assert block.relationship_history == ""


def test_world_block_validation():
    """WorldBlock validates correctly."""
    now = datetime.now(timezone.utc)
    block = WorldBlock(
        version=3,
        active_projects=[
            ProjectEntry(
                name="kairix",
                status="demo complete",
                context="voice AI",
                last_occurrence=now,
                occurrence_count=5,
            ),
            ProjectEntry(name="job-search", status="active", context="startup focus"),
        ],
        key_entities=[
            EntityEntry(
                name="Letta",
                relevance="memory infrastructure",
                last_occurrence=now,
                occurrence_count=10,
            ),
            EntityEntry(name="WeWork", relevance="workspace"),
        ],
        recurring_themes=[
            ThemeEntry(name="AI development", description="Focus on AI and ML"),
            ThemeEntry(name="startup life", description="The startup journey"),
        ],
        key_insights=["User prefers async communication"],
    )

    assert block.version == 3
    assert len(block.active_projects) == 2
    assert block.active_projects[0].name == "kairix"
    assert block.active_projects[0].occurrence_count == 5
    assert len(block.key_entities) == 2
    assert block.key_entities[0].last_occurrence == now
    assert len(block.recurring_themes) == 2
    assert block.recurring_themes[0].name == "AI development"
    assert len(block.key_insights) == 1


def test_world_block_defaults():
    """WorldBlock has sensible defaults."""
    block = WorldBlock(version=1)

    assert block.active_projects == []
    assert block.key_entities == []
    assert block.recurring_themes == []
    assert block.key_insights == []


def test_world_model_state_validation():
    """WorldModelState validates all three blocks."""
    state = WorldModelState(
        human=HumanBlock(version=1, core_values=["test"]),
        persona=PersonaBlock(version=1, voice="friendly"),
        world=WorldBlock(
            version=1,
            recurring_themes=[ThemeEntry(name="test theme", description="A test theme")],
        ),
    )

    assert state.human.version == 1
    assert state.persona.version == 1
    assert state.world.version == 1


def test_world_model_state_from_dict():
    """WorldModelState can be created from dict."""
    data = {
        "human": {"version": 5, "core_values": ["a", "b"]},
        "persona": {"version": 5, "voice": "casual"},
        "world": {
            "version": 5,
            "recurring_themes": [{"name": "theme1", "description": "First theme"}],
        },
    }

    state = WorldModelState.model_validate(data)

    assert state.human.version == 5
    assert state.persona.voice == "casual"
    assert len(state.world.recurring_themes) == 1
    assert state.world.recurring_themes[0].name == "theme1"


def test_world_model_state_roundtrip():
    """WorldModelState can be serialized and deserialized."""
    original = WorldModelState(
        human=HumanBlock(
            version=10,
            narrative="A complex individual",
            core_values=["value1", "value2"],
            current_life_context="context",
            emotional_baseline="stable",
            recurring_patterns=["pattern1"],
            open_threads=["thread1", "thread2"],
        ),
        persona=PersonaBlock(
            version=10,
            relationship_reflection="A meaningful connection",
            voice="direct",
            stance_toward_human="peer",
            learned_preferences=["pref1"],
            relationship_history="long history",
        ),
        world=WorldBlock(
            version=10,
            active_projects=[
                ProjectEntry(name="p1", status="active", context="c1"),
            ],
            key_entities=[
                EntityEntry(name="e1", relevance="r1"),
            ],
            recurring_themes=[ThemeEntry(name="theme1", description="A theme")],
            key_insights=["insight1"],
        ),
    )

    # Serialize to JSON
    json_str = original.model_dump_json()
    data = json.loads(json_str)

    # Deserialize back
    restored = WorldModelState.model_validate(data)

    assert restored.human.version == 10
    assert restored.human.narrative == "A complex individual"
    assert restored.human.core_values == ["value1", "value2"]
    assert restored.persona.relationship_reflection == "A meaningful connection"
    assert restored.persona.voice == "direct"
    assert restored.world.active_projects[0].name == "p1"
    assert restored.world.recurring_themes[0].name == "theme1"


def test_world_model_state_empty():
    """WorldModelState.empty() creates valid empty state."""
    state = WorldModelState.empty()

    assert state.human.version == 0
    assert state.persona.version == 0
    assert state.world.version == 0


def test_world_model_state_get_block():
    """get_block() returns correct block by type."""
    state = WorldModelState(
        human=HumanBlock(version=1),
        persona=PersonaBlock(version=2),
        world=WorldBlock(version=3),
    )

    assert state.get_block("human").version == 1
    assert state.get_block("persona").version == 2
    assert state.get_block("world").version == 3


def test_world_model_state_get_block_invalid():
    """get_block() raises ValueError for invalid type."""
    state = WorldModelState.empty()

    with pytest.raises(ValueError, match="Unknown block type"):
        state.get_block("invalid")


def test_human_block_requires_version():
    """HumanBlock requires version field."""
    with pytest.raises(ValidationError):
        HumanBlock()  # Missing version


def test_project_entry_validation():
    """ProjectEntry validates all fields."""
    entry = ProjectEntry(name="test", status="active", context="testing")

    assert entry.name == "test"
    assert entry.status == "active"
    assert entry.context == "testing"


def test_entity_entry_validation():
    """EntityEntry validates all fields including tracking fields."""
    now = datetime.now(timezone.utc)
    entry = EntityEntry(
        name="test-entity",
        relevance="important",
        last_occurrence=now,
        occurrence_count=5,
    )

    assert entry.name == "test-entity"
    assert entry.relevance == "important"
    assert entry.last_occurrence == now
    assert entry.occurrence_count == 5


def test_entity_entry_defaults():
    """EntityEntry has default for tracking fields."""
    entry = EntityEntry(name="test", relevance="test")

    assert entry.last_occurrence is None
    assert entry.occurrence_count == 1


def test_human_block_narrative_field():
    """HumanBlock narrative field works correctly."""
    block = HumanBlock(
        version=1,
        narrative="This is a rich narrative about the person's journey and what drives them.",
    )

    assert "rich narrative" in block.narrative


def test_persona_block_reflection_field():
    """PersonaBlock relationship_reflection field works correctly."""
    block = PersonaBlock(
        version=1,
        relationship_reflection="Deep reflection on the relationship and its meaning.",
    )

    assert "reflection" in block.relationship_reflection
