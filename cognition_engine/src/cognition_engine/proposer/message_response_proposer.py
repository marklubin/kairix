from cognition_engine import Proposer, Perception, Stimulus, StimulusType, Action


class MessageResponseAction(Action):
    pass


class MessageResponseProposer(Proposer):
    async def consider(self, stimulus: Stimulus, perceptions: list[Perception]):
        if stimulus.type == StimulusType.user_message:
            return MessageResponseAction(stimulus, perceptions)

        return None
