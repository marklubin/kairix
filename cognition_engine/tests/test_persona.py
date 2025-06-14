import pytest
from cognition_engine.persona import Persona
from cognition_engine.types import Stimulus, StimulusType, StimulusBus

from examples.perceptors import UserMessagePerceptor
from examples.proposers import PerceptionSpeakingProposer
from examples.schedulers import InlineExecutionScheduler


@pytest.mark.asyncio
async def test_persona_react():
    bus = StimulusBus()
    scheduler = InlineExecutionScheduler(bus)
    persona = Persona(
        perceptors=[UserMessagePerceptor()],
        proposers=[PerceptionSpeakingProposer()],
        schedulers=[scheduler],
    )

    stimulus = Stimulus(
        content="Hello persona", type=StimulusType.user_message
    )

    # Should not raise any exceptions
    await persona.react(stimulus)


@pytest.mark.asyncio
async def test_persona_without_scheduler():
    persona = Persona(
        perceptors=[UserMessagePerceptor()],
        proposers=[PerceptionSpeakingProposer()],
        schedulers=[],  # No schedulers
    )

    stimulus = Stimulus(content="Test", type=StimulusType.user_message)

    # Should raise RuntimeError when no scheduler accepts actions
    with pytest.raises(RuntimeError) as exc_info:
        await persona.react(stimulus)
    assert "No scheduler accepted actions" in str(exc_info.value)
