"""Persona module for Kairix cognitive system.

Personas orchestrate perceptors to create coherent responses to stimuli.
They represent the agent's personality and behavioral patterns.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator

from .conversational import ConversationalPersona
from kairix_core.types.cognition import Stimulus


class Persona(ABC):
    """Abstract base class for agent personas.
    
    A Persona defines how an agent responds to stimuli by orchestrating
    multiple perceptors and generating coherent responses.
    """
    
    @abstractmethod
    async def react(self, stimulus: Stimulus) -> AsyncIterator[str]:
        """Generate a response to a stimulus.
        
        Args:
            stimulus: The input stimulus to respond to
            
        Yields:
            Response tokens as they are generated (for streaming)
        """
        pass


__all__ = ["ConversationalPersona", "Persona"]
