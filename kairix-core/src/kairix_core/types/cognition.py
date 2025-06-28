"""Core data types for the Kairix cognitive system.

This module defines the fundamental data structures used for cognitive processing,
including stimuli (inputs) and perceptions (processed outputs).
"""

from dataclasses import dataclass
from enum import Enum
from rich.console import Console
from rich.panel import Panel

console = Console()


class StimulusType(Enum):
    """Types of stimuli that can trigger cognitive processing.
    
    Values:
        user_message: Direct message from the user
        execution_attempt: Result of trying to execute a command
        time_tick: Periodic time-based trigger
        world_event: External event from the environment
        self_perception: Internal reflection or self-awareness trigger
    """
    user_message = "user_message"
    execution_attempt = "execution_attempt"
    time_tick = "time_tick"
    world_event = "world_event"
    self_perception = "self_perception"


@dataclass
class Stimulus:
    """Input data that triggers cognitive processing.
    
    Attributes:
        content: The actual content/payload of the stimulus
        type: The type of stimulus for routing to appropriate perceptors
    """
    content: str
    type: StimulusType

    def __rich__(self):
        """Rich console representation for debugging."""
        return Panel(
            f"Type: {self.type.value}\nContent: {self.content}",
            title="Stimulus",
            border_style="blue",
        )


@dataclass
class Perception:
    """Output from a perceptor after processing a stimulus.
    
    Perceptions are the building blocks of the agent's understanding,
    combining processed information with metadata about its source and reliability.
    
    Attributes:
        source: Name of the perceptor that generated this perception
        content: The processed information/insight
        confidence: Confidence score (0.0-1.0) in the perception's accuracy
    """
    source: str
    content: str
    confidence: float = 1.0

    def __str__(self):
        """String representation for logging."""
        return f"""
        --------------------------------------------------------------------------
        - Perception\n
        - Source: {self.source}
        - Content:
        \t{self.content}\n
        --------------------------------------------------------------------------
        """
    
    def __rich__(self):
        """Rich console representation for debugging."""
        return Panel(
            f"Source: {self.source}\nConfidence: {self.confidence}\nContent: {self.content}",
            title="Perception",
            border_style="green",
        )
