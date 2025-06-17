from abc import ABC, abstractmethod
from typing import AsyncIterator

from .conversational import ConversationalPersona
from ..types import Stimulus


class Persona(ABC):

    @abstractmethod
    async def react(self, stimulus: Stimulus) -> AsyncIterator[str]:
        pass

__all__ = ["ConversationalPersona", "Persona"]
