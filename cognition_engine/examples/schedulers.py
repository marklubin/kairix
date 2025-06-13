from typing import List
from rich.console import Console
from src.scheduler import Scheduler
from src.types import Action, ActionResult, Stimulus, StimulusType, StimulusBus, ExecutedAction, Failure
from src.executor import Executor
from .executors import SayDoExecutor

console = Console()


class InlineExecutionScheduler(Scheduler):
    """
    Example scheduler that executes actions immediately inline.
    
    This scheduler accepts all actions and executes them immediately,
    emitting successful results as EXECUTION_ATTEMPT stimuli.
    """
    
    def __init__(self, stimulus_bus: StimulusBus, executors: List[Executor] = None):
        self.stimulus_bus = stimulus_bus
        self.executors = executors or [SayDoExecutor()]

    def schedule(self, actions: List[Action]) -> bool:
        console.print("[bold yellow]Scheduling actions...[/bold yellow]")
        
        if not actions:
            return False
        
        for action in actions:
            attempt = self.do_now(action)
            
            # Only emit successful results as stimuli
            if isinstance(attempt, ActionResult) and attempt.success:
                stimulus = Stimulus(
                    content={"action": action.type, "result": str(attempt.result)},
                    type=StimulusType.EXECUTION_ATTEMPT
                )
                self.stimulus_bus.emit(stimulus)
        
        return True

    def do_now(self, action: Action) -> ActionResult:
        try:
            # Use first available executor
            executor = self.executors[0] if self.executors else SayDoExecutor()
            result = executor.attempt(action)
            return ActionResult(action=action, result=result, success=result is not None)
        except Exception as e:
            console.print(f"[bold red]Action failed: {e}[/bold red]")
            return ActionResult(action=action, result=None, success=False)


class Hesitator:
    """Decision maker for whether to hesitate on an action."""
    
    def hesitates(self, action: Action) -> bool:
        # Hesitate on low priority actions
        return action.priority < 0


class HesitatingExecutionScheduler(Scheduler):
    """
    Example scheduler that may hesitate before executing actions.
    
    This scheduler uses a Hesitator to decide whether to execute actions
    based on their priority. Only accepts actions it doesn't hesitate on.
    """
    
    def __init__(self, stimulus_bus: StimulusBus, executors: List[Executor] = None, hesitator: Hesitator = None):
        self.stimulus_bus = stimulus_bus
        self.executors = executors or [SayDoExecutor()]
        self.hesitator = hesitator or Hesitator()

    def schedule(self, actions: List[Action]) -> bool:
        console.print("[bold yellow]Hesitating scheduler processing actions...[/bold yellow]")
        
        if not actions:
            return False
        
        accepted_any = False
        
        for action in actions:
            if self.hesitator.hesitates(action):
                console.print(f"[yellow]Hesitating on action: {action.type}[/yellow]")
                continue
                
            accepted_any = True
            attempt = self.do_now(action)
            
            # Only emit successful executions as stimuli
            if isinstance(attempt, ExecutedAction) and attempt.result is not None:
                stimulus = Stimulus(
                    content={"action": action.type, "result": str(attempt.result)},
                    type=StimulusType.EXECUTION_ATTEMPT
                )
                self.stimulus_bus.emit(stimulus)
        
        return accepted_any

    def do_now(self, action: Action):
        try:
            executor = self.executors[0] if self.executors else SayDoExecutor()
            result = executor.attempt(action)
            return ExecutedAction(action=action, result=result)
        except Exception as e:
            return Failure(action=action, exception=e)