from abc import ABC, abstractmethod
from typing import List
from ..types import Stimulus, Perception, Action


class Proposer(ABC):
    """
    Abstract base class for action proposers.

    A Proposer considers the current stimulus and perceptions to generate
    a list of proposed actions. The proposer may use any strategy to
    determine which actions to propose.
    """

    @abstractmethod
    async def consider(
        self, stimulus: Stimulus, perceptions: List[Perception]
    ) -> List[Action]:
        """
        Consider the stimulus and perceptions to propose actions.

        Args:
            stimulus: The current stimulus being processed
            perceptions: List of perceptions generated from the stimulus

        Returns:
            List of proposed actions
        """
        pass
