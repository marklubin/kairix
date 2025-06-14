import pytest
from cognition_engine.types import Stimulus, StimulusType, Perception

from examples.proposers import PerceptionSpeakingProposer


@pytest.mark.asyncio
async def test_proposer_consider():
    proposer = PerceptionSpeakingProposer()

    stimulus = Stimulus(content="Hello", type=StimulusType.user_message)

    perceptions = [
        Perception(
            content="Hello", source="user_input_perceptor", confidence=0.8
        )
    ]

    actions = await proposer.consider(stimulus, perceptions)

    assert len(actions) == 1
    assert actions[0].type == "say"
    assert "I perceived" in actions[0].parameters["text"]


@pytest.mark.asyncio
async def test_proposer_no_perceptions():
    proposer = PerceptionSpeakingProposer()

    stimulus = Stimulus(content="", type=StimulusType.time_tick)

    actions = await proposer.consider(stimulus, [])

    assert len(actions) == 0
