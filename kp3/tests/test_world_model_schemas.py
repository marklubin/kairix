"""Tests for world model schemas."""

import json

import pytest
from pydantic import ValidationError

from kp3.schemas.world_model import (
    EntityEntry,
    HumanBlock,
    PersonaBlock,
    ProjectEntry,
    WorldBlock,
    WorldModelState,
)


def test_human_block_validation():
    """HumanBlock validates correctly."""
    block = HumanBlock(
        version=1,
        core_values=["authenticity", "technical depth"],
        current_life_context="Working on AI projects",
        emotional_baseline="focused and determined",
        recurring_patterns=["research paralysis", "energized by coding"],
        open_threads=["job search", "project deadlines"],
    )

    assert block.version == 1
    assert len(block.core_values) == 2
    assert "authenticity" in block.core_values


def test_human_block_defaults():
    """HumanBlock has sensible defaults."""
    block = HumanBlock(version=1)

    assert block.core_values == []
    assert block.current_life_context == ""
    assert block.emotional_baseline == ""
    assert block.recurring_patterns == []
    assert block.open_threads == []


def test_persona_block_validation():
    """PersonaBlock validates correctly."""
    block = PersonaBlock(
        version=2,
        voice="direct and technical",
        stance_toward_human="collaborative peer",
        learned_preferences=["prefers examples", "wants brevity"],
        relationship_history="Long collaboration on Kairix project",
    )

    assert block.version == 2
    assert block.voice == "direct and technical"
    assert len(block.learned_preferences) == 2


def test_persona_block_defaults():
    """PersonaBlock has sensible defaults."""
    block = PersonaBlock(version=1)

    assert block.voice == ""
    assert block.stance_toward_human == ""
    assert block.learned_preferences == []
    assert block.relationship_history == ""


def test_world_block_validation():
    """WorldBlock validates correctly."""
    block = WorldBlock(
        version=3,
        active_projects=[
            ProjectEntry(name="kairix", status="demo complete", context="voice AI"),
            ProjectEntry(name="job-search", status="active", context="startup focus"),
        ],
        key_entities=[
            EntityEntry(name="Letta", relevance="memory infrastructure"),
            EntityEntry(name="WeWork", relevance="workspace"),
        ],
        environmental_context="December 2025, SF",
    )

    assert block.version == 3
    assert len(block.active_projects) == 2
    assert block.active_projects[0].name == "kairix"
    assert len(block.key_entities) == 2


def test_world_block_defaults():
    """WorldBlock has sensible defaults."""
    block = WorldBlock(version=1)

    assert block.active_projects == []
    assert block.key_entities == []
    assert block.environmental_context == ""


def test_world_model_state_validation():
    """WorldModelState validates all three blocks."""
    state = WorldModelState(
        human=HumanBlock(version=1, core_values=["test"]),
        persona=PersonaBlock(version=1, voice="friendly"),
        world=WorldBlock(version=1, environmental_context="test env"),
    )

    assert state.human.version == 1
    assert state.persona.version == 1
    assert state.world.version == 1


def test_world_model_state_from_dict():
    """WorldModelState can be created from dict."""
    data = {
        "human": {"version": 5, "core_values": ["a", "b"]},
        "persona": {"version": 5, "voice": "casual"},
        "world": {"version": 5, "environmental_context": "home"},
    }

    state = WorldModelState.model_validate(data)

    assert state.human.version == 5
    assert state.persona.voice == "casual"
    assert state.world.environmental_context == "home"


def test_world_model_state_roundtrip():
    """WorldModelState can be serialized and deserialized."""
    original = WorldModelState(
        human=HumanBlock(
            version=10,
            core_values=["value1", "value2"],
            current_life_context="context",
            emotional_baseline="stable",
            recurring_patterns=["pattern1"],
            open_threads=["thread1", "thread2"],
        ),
        persona=PersonaBlock(
            version=10,
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
            environmental_context="env",
        ),
    )

    # Serialize to JSON
    json_str = original.model_dump_json()
    data = json.loads(json_str)

    # Deserialize back
    restored = WorldModelState.model_validate(data)

    assert restored.human.version == 10
    assert restored.human.core_values == ["value1", "value2"]
    assert restored.persona.voice == "direct"
    assert restored.world.active_projects[0].name == "p1"


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
    """EntityEntry validates all fields."""
    entry = EntityEntry(name="test-entity", relevance="important")

    assert entry.name == "test-entity"
    assert entry.relevance == "important"
