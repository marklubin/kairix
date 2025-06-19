from kairix_core.types.cognition import (
    Stimulus,
    StimulusType,
    Perception,
)


def test_stimulus_creation():
    stimulus = Stimulus(content="Hello", type=StimulusType.user_message)
    assert stimulus.content == "Hello"
    assert stimulus.type == StimulusType.user_message


def test_perception_creation():
    perception = Perception(content="test perception", source="test_source", confidence=0.9)
    assert perception.source == "test_source"
    assert perception.confidence == 0.9
    assert perception.content == "test perception"
