from dataclasses import dataclass
from enum import Enum
from rich.console import Console
from rich.panel import Panel

console = Console()


class StimulusType(Enum):
    user_message = "user_message"
    execution_attempt = "execution_attempt"
    time_tick = "time_tick"
    world_event = "world_event"
    self_perception = "self_perception"


@dataclass
class Stimulus:
    content: str
    type: StimulusType

    def __rich__(self):
        return Panel(
            f"Type: {self.type.value}\nContent: {self.content}",
            title="Stimulus",
            border_style="blue",
        )


@dataclass
class Perception:
    source: str
    content: str
    confidence: float = 1.0


    def __str__(self):
        return f"""
        --------------------------------------------------------------------------
        - Perception\n
        - Source: {self.source}
        - Content:
        \t{self.content}\n
        --------------------------------------------------------------------------
        """
    def __rich__(self):
        return Panel(
            f"Source: {self.source}\nConfidence: {self.confidence}\nContent: {self.content}",
            title="Perception",
            border_style="green",
        )
