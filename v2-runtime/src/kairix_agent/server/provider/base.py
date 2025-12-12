"""Abstract LLM provider interface."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class LLMProvider(ABC):
    """Abstract base for LLM streaming providers."""

    @abstractmethod
    async def stream_response(self, user_message: str) -> AsyncIterator[str]:
        """Stream response chunks from the LLM.

        Args:
            user_message: The user's input text

        Yields:
            Text chunks as they arrive from the provider
        """
        yield ""  # Makes this an async generator that yields str
