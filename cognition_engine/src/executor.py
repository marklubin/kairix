from typing import Optional
from rich.console import Console
from .types import Action

console = Console()


class Executor:
    def attempt(self, action: Action) -> Optional[dict]:
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