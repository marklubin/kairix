from examples.perceptors import UserMessagePerceptor
from src.types import Stimulus, StimulusType


def test_perceptor_perceive():
    perceptor = UserMessagePerceptor()
    
    stimulus = Stimulus(
        content={"text": "Hello world"},
        type=StimulusType.USER_MESSAGE
    )
    
    perceptions = perceptor.perceive(stimulus)
    
    assert len(perceptions) > 0
    assert perceptions[0].source == "user_input_perceptor"
    assert perceptions[0].confidence == 0.8


def test_perceptor_with_empty_stimulus():
    perceptor = UserMessagePerceptor()
    
    stimulus = Stimulus(
        content={},
        type=StimulusType.TIME_TICK
    )
    
    perceptions = perceptor.perceive(stimulus)
    
    # Should return empty list for non-user messages
    assert len(perceptions) == 0