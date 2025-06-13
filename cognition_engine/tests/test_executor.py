from src.executor import Executor
from src.types import Action


def test_executor_say_action():
    executor = Executor()
    
    action = Action(
        type="say",
        parameters={"text": "Hello world"}
    )
    
    result = executor.attempt(action)
    
    assert result is not None
    assert result["said"] == "Hello world"


def test_executor_do_action():
    executor = Executor()
    
    action = Action(
        type="do",
        parameters={"task": "test_task"}
    )
    
    result = executor.attempt(action)
    
    assert result is not None
    assert result["done"]["task"] == "test_task"


def test_executor_unknown_action():
    executor = Executor()
    
    action = Action(
        type="unknown_action",
        parameters={}
    )
    
    result = executor.attempt(action)
    
    assert result is None