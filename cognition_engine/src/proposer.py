from typing import List
from rich.console import Console
from .types import Stimulus, Perception, Action

console = Console()


class Proposer:
    def consider(self, stimulus: Stimulus, perceptions: List[Perception]) -> List[Action]:
        console.print("[bold magenta]Proposer considering actions...[/bold magenta]")
        
        actions = []
        
        # Placeholder implementation
        for perception in perceptions:
            if perception.source == "user_input_perceptor":
                actions.append(
                    Action(
                        type="say",
                        parameters={"text": f"I perceived: {perception.content.get('message', '')}"},
                        priority=1
                    )
                )
        
        for action in actions:
            console.print(action)
        
        return actions