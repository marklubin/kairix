from typing import List, Optional
from rich.console import Console
from cognition_engine.perceptor import Perceptor
from cognition_engine.types import Stimulus, Perception, Source, Sink

console = Console()


class UserMessagePerceptor(Perceptor):
    """
    Example perceptor that processes user messages.
    
    This perceptor recognizes USER_MESSAGE stimuli and creates perceptions
    about the message content and intent.
    """
    
    def __init__(self, sources: Optional[List[Source]] = None, sinks: Optional[List[Sink]] = None):
        # Sources and sinks are internal implementation details
        self._sources = sources or []
        self._sinks = sinks or []
    
    def perceive(self, stimulus: Stimulus) -> List[Perception]:
        console.print(f"[bold green]Perceptor processing stimulus: {stimulus.type.value}[/bold green]")
        
        perceptions = []
        
        # Process user messages
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