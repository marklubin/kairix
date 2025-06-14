from typing import List
from rich.console import Console
from rich.panel import Panel
from ..types import Stimulus, Perception, Action
from ..perceptor import Perceptor
from ..proposer import Proposer
from ..scheduler import Scheduler

console = Console()


class Persona:
    """
    The main orchestrator of the cognition cycle.

    A Persona coordinates perceptors, proposers, and schedulers to process
    stimuli and generate responses. It supports multiple schedulers in a
    prioritized list where the first scheduler to accept an action handles it.
    """

    def __init__(
        self,
        perceptors: List[Perceptor],
        proposers: List[Proposer],
        schedulers: List[Scheduler],
    ):
        self.perceptors = perceptors
        self.proposers = proposers
        self.schedulers = schedulers

    async def react(self, stimulus: Stimulus) -> None:
        """Process a stimulus through the perception-proposal-execution cycle."""
        console.print(
            Panel(
                f"[bold cyan]Persona reacting to stimulus: {stimulus.type.value}[/bold cyan]",
                title="Reaction Cycle",
                border_style="cyan",
            )
        )

        # Perception phase
        perceptions: List[Perception] = []
        for perceptor in self.perceptors:
            results = await perceptor.perceive(stimulus)
            perceptions.extend(results)

        # Proposal phase
        proposed_actions: List[Action] = []
        for proposer in self.proposers:
            results = await proposer.consider(stimulus, perceptions)
            proposed_actions.extend(results)

        # Scheduling phase - first scheduler to accept wins
        if proposed_actions:
            scheduled = False
            for scheduler in self.schedulers:
                if scheduler.schedule(proposed_actions):
                    scheduled = True
                    break

            if not scheduled:
                raise RuntimeError(
                    f"No scheduler accepted actions: {[a.type for a in proposed_actions]}"
                )
        else:
            console.print("[yellow]No actions proposed[/yellow]")
