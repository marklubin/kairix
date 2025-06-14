from cognition_engine.types import Stimulus, StimulusType, Perception, Action, StimulusBus


def test_stimulus_creation():
    stimulus = Stimulus(
        content={"text": "Hello"},
        type=StimulusType.USER_MESSAGE
    )
    assert stimulus.content["text"] == "Hello"
    assert stimulus.type == StimulusType.USER_MESSAGE


def test_perception_creation():
    perception = Perception(
        content={"key": "value"},
        source="test_source",
        confidence=0.9
    )
    assert perception.source == "test_source"
    assert perception.confidence == 0.9


def test_action_creation():
    action = Action(
        type="test_action",
        parameters={"param": "value"},
        priority=5
    )
    assert action.type == "test_action"
    assert action.priority == 5


def test_stimulus_bus():
    bus = StimulusBus()
    received = []
    
    def listener(stim):
        received.append(stim)
    
    bus.subscribe(listener)
    
    stimulus = Stimulus(
        content={"test": "data"},
        type=StimulusType.TIME_TICK
    )
    bus.emit(stimulus)
    
    assert len(received) == 1
    assert received[0] == stimulus