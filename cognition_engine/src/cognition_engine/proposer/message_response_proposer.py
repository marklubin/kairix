from cognition_engine import Proposer, Perception, Stimulus, StimulusType, Action


class MessageResponseAction(Action):
    def __init__(self, stimulus: Stimulus, perceptions: list[Perception]):
        super().__init__(
            type="message_response",
            parameters={
                "stimulus": stimulus,
                "perceptions": perceptions
            }
        )


class MessageResponseProposer(Proposer):
    async def consider(self, stimulus: Stimulus, perceptions: list[Perception]):
        if stimulus.type == StimulusType.user_message:
            return MessageResponseAction(stimulus, perceptions)

        return None