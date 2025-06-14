from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


class StimulusType(Enum):
    user_message = "user_message"
    execution_attempt = "execution_attempt"
    time_tick = "time_tick"
    world_event = "world_event"


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
    content: str
    source: str
    confidence: float = 1.0

    def __rich__(self):
        return Panel(
            f"Source: {self.source}\nConfidence: {self.confidence}\nContent: {self.content}",
            title="Perception",
            border_style="green",
        )


@dataclass
class Action:
    type: str
    parameters: Dict[str, Any]
    priority: int = 0

    def do(self) -> Any:
        console.print(f"[bold yellow]Executing action: {self.type}[/bold yellow]")
        return {"type": self.type, "result": "placeholder"}

    def __rich__(self):
        table = Table(title=f"Action: {self.type}")
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="magenta")
        for key, value in self.parameters.items():
            table.add_row(key, str(value))
        return table


@dataclass
class ActionResult:
    action: Action
    result: Any
    success: bool = True


@dataclass
class InAction:
    action: Action
    reason: str = "Hesitated"


@dataclass
class ExecutedAction:
    action: Action
    result: Any


@dataclass
class Failure:
    action: Action
    exception: Exception


class Source:
    def get(self, key: str) -> Any:
        return None


class Sink:
    def put(self, key: str, value: Any) -> None:
        pass


class StimulusBus:
    def __init__(self):
        self.listeners = []

    def emit(self, stimulus: Stimulus):
        console.print(Panel(f"[bold cyan]Emitting: {stimulus.type.value}[/bold cyan]"))
        for listener in self.listeners:
            listener(stimulus)

    def subscribe(self, listener):
        self.listeners.append(listener)
