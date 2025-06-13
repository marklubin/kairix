from src.persona import Persona
from src.types import Stimulus, StimulusType, StimulusBus
from src.scheduler import InlineExecutionScheduler


def test_persona_react():
    bus = StimulusBus()
    scheduler = InlineExecutionScheduler(bus)
    persona = Persona(scheduler=scheduler)
    
    stimulus = Stimulus(
        content={"text": "Hello persona"},
        type=StimulusType.USER_MESSAGE
    )
    
    # Should not raise any exceptions
    persona.react(stimulus)


def test_persona_without_scheduler():
    persona = Persona()
    
    stimulus = Stimulus(
        content={"text": "Test"},
        type=StimulusType.USER_MESSAGE
    )
    
    # Should handle gracefully without scheduler
    persona.react(stimulus)