# Kairix Psyche Engine

## Pschedule Algorithm

```
class Perceptor:

    sources: List[Sources]
    sinks: List[Sink]
    
    def perceive(self, stimulus: Stimulus) -> List[Perception]:
        # Gather the info from the store
        # Find pieces of info relating to stimuluous
        # Update them considering the stimulus as new input
        # Return a list of updated perceptions updating the present state
        pass
    
   
    
    
class Proposer:
    def consider(self, perceptions: List[Perceptions]) -> List[Action]:
        # Given the stimulus and the Persona's perceptions of it generate an Action 
        #    eg. Say, Do
        
        

        
Class Executor:
    
    def attempt(action: Action): -> None
        #Try to do something or return None if it failed, trigger a stimulus for self perception
  
class Stimulus:
        content: dict[str, str]
        type: StimulusType
        
StimulusType = Enum('StimulusType', ['user_message', 'execution_attempt','time_tick', 'world_event']
        
        
        
class Persona:

    perceptors: List[Perceptors]
    proposers: List[Proposers]
    scheduler: Scheduler

    def react(stimulus: Stimulus)->None:
        perceptions: list[Perceptions] = []
        for perceptor in perceptors:
            results = perceptor.perceive(stimulus)
            perceptions.extend(results)
            
        proposed_actions: list[Actions] = []
        for proposer in purposers:
            results = proposer.consider(stimulus, perceptions)
            proposed_actions.extend(results)
        
        scheduler.schedule(proposed_actions)
        
        
class InlineExecutionScheduler:

    stimulus_bus: StimulusBus
    executors: list[Executors] # list of supported executors to schedule against
    
    def schedule(self, actions: List[Action]) -> None:
        for action in actions:
            attempt = do_now(action)
            stimulus_bus.emit(attempt)
          
                
                
    def do_now(action: Action): ActionResult
        try:
            return ActionResult(action.do())
        except Exception as e:
           return Failure(action,e)
          
                
# You can be indecisive     
        
class HesistingExecutionScheduler

    stimulus_bus: StimulusBus
    executors: list[Executors] # list of supported executors to schedule against
    hesitator: Hesitator
    
    def schedule(self, actions: List[Action]) -> None:
        for action in actions:
            attempt = do_now(action)
            stimulus_bus.emit(attempt)
          
                
                
    def do_now(action: Action): Attempt
        if hesitator.hesitates(action):
            return InAction(action)
        return ExecutedAction(action.do())
        
    
        
# Action effects on external world come back through normal stimulus channels like acting in the real world
       
```