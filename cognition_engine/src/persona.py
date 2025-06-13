from typing import List
from rich.console import Console
from rich.panel import Panel
from .types import Stimulus, Perception, Action
from .perceptor import Perceptor
from .proposer import Proposer

console = Console()


class Persona:
    def __init__(self, perceptors: List[Perceptor] = None, proposers: List[Proposer] = None, scheduler = None):
        self.perceptors = perceptors or [Perceptor()]
        self.proposers = proposers or [Proposer()]
        self.scheduler = scheduler

    def react(self, stimulus: Stimulus) -> None:
        console.print(Panel(
            f"[bold cyan]Persona reacting to stimulus: {stimulus.type.value}[/bold cyan]",
            title="Reaction Cycle",
            border_style="cyan"
        ))
        
        # Perception phase
        perceptions: List[Perception] = []
        for perceptor in self.perceptors:
            results = perceptor.perceive(stimulus)
            perceptions.extend(results)
        
        # Proposal phase
        proposed_actions: List[Action] = []
        for proposer in self.proposers:
            results = proposer.consider(stimulus, perceptions)
            proposed_actions.extend(results)
        
        # Scheduling phase
        if self.scheduler and proposed_actions:
            self.scheduler.schedule(proposed_actions)
        else:
            console.print("[yellow]No scheduler configured or no actions to schedule[/yellow]")