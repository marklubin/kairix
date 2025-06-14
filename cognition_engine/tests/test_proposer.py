from cognition_engine.types import Stimulus, StimulusType, Perception

from examples.proposers import PerceptionSpeakingProposer


def test_proposer_consider():
    proposer = PerceptionSpeakingProposer()
    
    stimulus = Stimulus(
        content={"text": "Hello"},
        type=StimulusType.USER_MESSAGE
    )
    
    perceptions = [
        Perception(
            content={"message": "Hello"},
            source="user_input_perceptor",
            confidence=0.8
        )
    ]
    
    actions = proposer.consider(stimulus, perceptions)
    
    assert len(actions) == 1
    assert actions[0].type == "say"
    assert "I perceived" in actions[0].parameters["text"]


def test_proposer_no_perceptions():
    proposer = PerceptionSpeakingProposer()
    
    stimulus = Stimulus(
        content={},
        type=StimulusType.TIME_TICK
    )
    
    actions = proposer.consider(stimulus, [])
    
    assert len(actions) == 0
