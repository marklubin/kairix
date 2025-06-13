from typing import List
from rich.console import Console
from src.proposer import Proposer
from src.types import Stimulus, Perception, Action

console = Console()


class PerceptionSpeakingProposer(Proposer):
    """
    Example proposer that generates 'say' actions based on perceptions.
    
    This proposer creates actions that speak about what was perceived,
    particularly for user input perceptions.
    """
    
    def consider(self, stimulus: Stimulus, perceptions: List[Perception]) -> List[Action]:
        console.print("[bold magenta]Proposer considering actions...[/bold magenta]")
        
        actions = []
        
        # Generate say actions for user input perceptions
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