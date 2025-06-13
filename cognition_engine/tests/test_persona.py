import pytest
from src.persona import Persona
from src.types import Stimulus, StimulusType, StimulusBus
from examples.schedulers import InlineExecutionScheduler
from examples.perceptors import UserMessagePerceptor
from examples.proposers import PerceptionSpeakingProposer


def test_persona_react():
    bus = StimulusBus()
    scheduler = InlineExecutionScheduler(bus)
    persona = Persona(
        perceptors=[UserMessagePerceptor()],
        proposers=[PerceptionSpeakingProposer()],
        schedulers=[scheduler]
    )
    
    stimulus = Stimulus(
        content={"text": "Hello persona"},
        type=StimulusType.USER_MESSAGE
    )
    
    # Should not raise any exceptions
    persona.react(stimulus)


def test_persona_without_scheduler():
    persona = Persona(
        perceptors=[UserMessagePerceptor()],
        proposers=[PerceptionSpeakingProposer()],
        schedulers=[]  # No schedulers
    )
    
    stimulus = Stimulus(
        content={"text": "Test"},
        type=StimulusType.USER_MESSAGE
    )
    
    # Should raise RuntimeError when no scheduler accepts actions
    with pytest.raises(RuntimeError) as exc_info:
        persona.react(stimulus)
    assert "No scheduler accepted actions" in str(exc_info.value)