from typing import Optional, Any
from rich.console import Console
from src.executor import Executor
from src.types import Action

console = Console()


class SayDoExecutor(Executor):
    """
    Example executor that handles 'say' and 'do' actions.
    
    - 'say' actions print text to the console
    - 'do' actions print the action parameters
    """
    
    def attempt(self, action: Action) -> Optional[Any]:
        console.print(f"[bold red]Executor attempting: {action.type}[/bold red]")
        
        try:
            if action.type == "say":
                text = action.parameters.get("text", "")
                console.print(f"[bold blue]>> {text}[/bold blue]")
                return {"said": text}
            elif action.type == "do":
                console.print(f"[yellow]Doing: {action.parameters}[/yellow]")
                return {"done": action.parameters}
            else:
                console.print(f"[red]Unknown action type: {action.type}[/red]")
                return None
        except Exception as e:
            console.print(f"[bold red]Execution failed: {e}[/bold red]")
            return None