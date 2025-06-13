from typing import List
from rich.console import Console
from .types import Stimulus, Perception, Source, Sink

console = Console()


class Perceptor:
    def __init__(self, sources: List[Source] = None, sinks: List[Sink] = None):
        self.sources = sources or []
        self.sinks = sinks or []

    def perceive(self, stimulus: Stimulus) -> List[Perception]:
        console.print(f"[bold green]Perceptor processing stimulus: {stimulus.type.value}[/bold green]")
        
        perceptions = []
        
        # Placeholder implementation
        if stimulus.type.name == "USER_MESSAGE":
            perceptions.append(
                Perception(
                    content={"message": stimulus.content.get("text", ""), "intent": "unknown"},
                    source="user_input_perceptor",
                    confidence=0.8
                )
            )
        
        for perception in perceptions:
            console.print(perception)
        
        return perceptions