from abc import ABC, abstractmethod
from typing import Optional, Any
from ..types import Action


class Executor(ABC):
    """
    Abstract base class for action executors.

    An Executor is responsible for attempting to execute actions and returning
    the result of the execution attempt. Executors should handle errors gracefully
    and return None if execution fails.
    """

    @abstractmethod
    async def attempt(self, action: Action) -> Optional[Any]:
        """
        Attempt to execute the given action.

        Args:
            action: The action to execute

        Returns:
            Result of the execution if successful, None if failed
        """
        pass
