from typing import List
from rich.console import Console
from .types import Action, ActionResult, Stimulus, StimulusType, StimulusBus, InAction, ExecutedAction, Failure
from .executor import Executor

console = Console()


class InlineExecutionScheduler:
    def __init__(self, stimulus_bus: StimulusBus, executors: List[Executor] = None):
        self.stimulus_bus = stimulus_bus
        self.executors = executors or [Executor()]

    def schedule(self, actions: List[Action]) -> None:
        console.print("[bold yellow]Scheduling actions...[/bold yellow]")
        
        for action in actions:
            attempt = self.do_now(action)
            
            # Emit result as stimulus
            if isinstance(attempt, ActionResult):
                stimulus = Stimulus(
                    content={"action": action.type, "result": str(attempt.result)},
                    type=StimulusType.EXECUTION_ATTEMPT
                )
                self.stimulus_bus.emit(stimulus)

    def do_now(self, action: Action) -> ActionResult:
        try:
            # Use first available executor
            executor = self.executors[0] if self.executors else Executor()
            result = executor.attempt(action)
            return ActionResult(action=action, result=result, success=result is not None)
        except Exception as e:
            console.print(f"[bold red]Action failed: {e}[/bold red]")
            return ActionResult(action=action, result=None, success=False)


class Hesitator:
    def hesitates(self, action: Action) -> bool:
        # Placeholder: hesitate on low priority actions
        return action.priority < 0


class HesitatingExecutionScheduler:
    def __init__(self, stimulus_bus: StimulusBus, executors: List[Executor] = None, hesitator: Hesitator = None):
        self.stimulus_bus = stimulus_bus
        self.executors = executors or [Executor()]
        self.hesitator = hesitator or Hesitator()

    def schedule(self, actions: List[Action]) -> None:
        console.print("[bold yellow]Hesitating scheduler processing actions...[/bold yellow]")
        
        for action in actions:
            attempt = self.do_now(action)
            
            # Emit result as stimulus
            if isinstance(attempt, ExecutedAction):
                stimulus = Stimulus(
                    content={"action": action.type, "result": str(attempt.result)},
                    type=StimulusType.EXECUTION_ATTEMPT
                )
                self.stimulus_bus.emit(stimulus)
            elif isinstance(attempt, InAction):
                console.print(f"[yellow]Skipped action due to: {attempt.reason}[/yellow]")

    def do_now(self, action: Action):
        if self.hesitator.hesitates(action):
            return InAction(action)
        
        try:
            executor = self.executors[0] if self.executors else Executor()
            result = executor.attempt(action)
            return ExecutedAction(action=action, result=result)
        except Exception as e:
            return Failure(action=action, exception=e)