from src.scheduler import InlineExecutionScheduler, HesitatingExecutionScheduler, Hesitator
from src.types import Action, StimulusBus


def test_inline_scheduler():
    bus = StimulusBus()
    scheduler = InlineExecutionScheduler(bus)
    
    emitted = []
    bus.subscribe(lambda s: emitted.append(s))
    
    actions = [
        Action(type="say", parameters={"text": "Test"})
    ]
    
    scheduler.schedule(actions)
    
    assert len(emitted) == 1
    assert emitted[0].type.name == "EXECUTION_ATTEMPT"


def test_hesitating_scheduler():
    bus = StimulusBus()
    scheduler = HesitatingExecutionScheduler(bus)
    
    emitted = []
    bus.subscribe(lambda s: emitted.append(s))
    
    # High priority action should execute
    actions = [
        Action(type="say", parameters={"text": "Test"}, priority=1)
    ]
    
    scheduler.schedule(actions)
    
    assert len(emitted) == 1


def test_hesitator():
    hesitator = Hesitator()
    
    # Low priority action should be hesitated
    low_priority = Action(type="test", parameters={}, priority=-1)
    assert hesitator.hesitates(low_priority)
    
    # Normal priority action should not be hesitated
    normal_priority = Action(type="test", parameters={}, priority=0)
    assert not hesitator.hesitates(normal_priority)