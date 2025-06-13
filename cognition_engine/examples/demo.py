from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from src import (
    Persona, 
    StimulusBus,
    Stimulus,
    StimulusType
)
from .perceptors import UserMessagePerceptor
from .proposers import PerceptionSpeakingProposer
from .schedulers import InlineExecutionScheduler, HesitatingExecutionScheduler

console = Console()


def main():
    console.print(Panel.fit(
        "[bold cyan]Kairix Psyche Engine[/bold cyan]\n"
        "[yellow]Agent-based Cognition Architecture[/yellow]",
        border_style="cyan"
    ))
    
    # Initialize components
    stimulus_bus = StimulusBus()
    perceptors = [UserMessagePerceptor()]
    proposers = [PerceptionSpeakingProposer()]
    
    # Choose scheduler type
    scheduler_type = Prompt.ask(
        "Choose scheduler", 
        choices=["inline", "hesitating"],
        default="inline"
    )
    
    if scheduler_type == "inline":
        schedulers = [InlineExecutionScheduler(stimulus_bus)]
    else:
        schedulers = [HesitatingExecutionScheduler(stimulus_bus)]
    
    # Create persona
    persona = Persona(
        perceptors=perceptors,
        proposers=proposers,
        schedulers=schedulers
    )
    
    # Subscribe persona to stimulus bus for self-perception
    stimulus_bus.subscribe(lambda s: persona.react(s) if s.type == StimulusType.EXECUTION_ATTEMPT else None)
    
    console.print("[green]System initialized. Type messages to interact (or 'quit' to exit)[/green]")
    
    # Main interaction loop
    while True:
        user_input = Prompt.ask("[bold blue]You[/bold blue]")
        
        if user_input.lower() in ['quit', 'exit']:
            console.print("[yellow]Shutting down...[/yellow]")
            break
        
        # Create user message stimulus
        stimulus = Stimulus(
            content={"text": user_input},
            type=StimulusType.USER_MESSAGE
        )
        
        # Process stimulus
        persona.react(stimulus)
        console.print()


if __name__ == "__main__":
    main()
