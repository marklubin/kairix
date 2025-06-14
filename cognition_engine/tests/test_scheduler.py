from unittest.mock import Mock

from cognition_engine.executor import Executor
from cognition_engine.types import Action, StimulusBus

from examples.schedulers import InlineExecutionScheduler, HesitatingExecutionScheduler, Hesitator


def test_inline_scheduler():
    bus = StimulusBus()
    scheduler = InlineExecutionScheduler(bus)
    
    emitted = []
    bus.subscribe(lambda s: emitted.append(s))
    
    actions = [
        Action(type="say", parameters={"text": "Test"})
    ]
    
    result = scheduler.schedule(actions)
    
    assert result is True
    assert len(emitted) == 1
    assert emitted[0].type.name == "execution_attempt"


def test_hesitating_scheduler():
    bus = StimulusBus()
    scheduler = HesitatingExecutionScheduler(bus)
    
    emitted = []
    bus.subscribe(lambda s: emitted.append(s))
    
    # High priority action should execute
    actions = [
        Action(type="say", parameters={"text": "Test"}, priority=1)
    ]
    
    result = scheduler.schedule(actions)
    
    assert result is True
    assert len(emitted) == 1


def test_hesitator():
    hesitator = Hesitator()
    
    # Low priority action should be hesitated
    low_priority = Action(type="test", parameters={}, priority=-1)
    assert hesitator.hesitates(low_priority)
    
    # Normal priority action should not be hesitated
    normal_priority = Action(type="test", parameters={}, priority=0)
    assert not hesitator.hesitates(normal_priority)


def test_inline_scheduler_exception_handling():
    """Test that InlineExecutionScheduler handles exceptions correctly."""
    bus = StimulusBus()
    
    # Create a mock executor that raises an exception
    failing_executor = Mock(spec=Executor)
    failing_executor.attempt.side_effect = Exception("Test exception")
    
    scheduler = InlineExecutionScheduler(bus, executors=[failing_executor])
    
    emitted = []
    bus.subscribe(lambda s: emitted.append(s))
    
    action = Action(type="test", parameters={})
    result = scheduler.do_now(action)
    
    # Verify the result indicates failure
    assert result.success is False
    assert result.result is None
    assert result.action == action
