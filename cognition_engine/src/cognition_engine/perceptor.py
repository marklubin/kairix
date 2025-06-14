from abc import ABC, abstractmethod
from typing import List
from .types import Stimulus, Perception


class Perceptor(ABC):
    """
    Abstract base class for perceptors.
    
    A Perceptor processes stimuli and produces perceptions. It may use internal
    sources and sinks for information storage and retrieval, but these are
    implementation details not exposed in the interface.
    """
    
    @abstractmethod
    def perceive(self, stimulus: Stimulus) -> List[Perception]:
        """
        Process a stimulus and generate perceptions.
        
        Args:
            stimulus: The stimulus to process
            
        Returns:
            List of perceptions generated from the stimulus
        """
        pass