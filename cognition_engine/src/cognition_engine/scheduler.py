from abc import ABC, abstractmethod
from typing import List
from .types import Action


class Scheduler(ABC):
    """
    Abstract base class for action schedulers.
    
    A Scheduler is responsible for scheduling and executing actions.
    It returns True if it accepts and schedules the action, False otherwise.
    """
    
    @abstractmethod
    def schedule(self, actions: List[Action]) -> bool:
        """
        Attempt to schedule the given actions.
        
        Args:
            actions: List of actions to schedule
            
        Returns:
            True if the scheduler accepted and scheduled the actions, False otherwise
        """
        pass