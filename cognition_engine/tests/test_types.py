from cognition_engine.types import (
    Stimulus,
    StimulusType,
    Perception,
    Action,
    StimulusBus,
)


def test_stimulus_creation():
    stimulus = Stimulus(content="Hello", type=StimulusType.user_message)
    assert stimulus.content == "Hello"
    assert stimulus.type == StimulusType.user_message


def test_perception_creation():
    perception = Perception(
        content="test perception", source="test_source", confidence=0.9
    )
    assert perception.source == "test_source"
    assert perception.confidence == 0.9
    assert perception.content == "test perception"


def test_action_creation():
    action = Action(type="test_action", parameters={"param": "value"}, priority=5)
    assert action.type == "test_action"
    assert action.priority == 5


def test_stimulus_bus():
    bus = StimulusBus()
    received = []

    def listener(stim):
        received.append(stim)

    bus.subscribe(listener)

    stimulus = Stimulus(content="test data", type=StimulusType.time_tick)
    bus.emit(stimulus)

    assert len(received) == 1
    assert received[0] == stimulus
