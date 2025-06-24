from typing import List

from kairix_core.cognition import Perceptor
from kairix_core.types.cognition import Stimulus, Perception


class SemanticGraphPerceptor(Perceptor):


    async def perceive(self, stimulus: Stimulus) -> List[Perception]:
        pass
