import pytest
from cognition_engine.types import Action

from examples.executors import SayDoExecutor


@pytest.mark.asyncio
async def test_executor_say_action():
    executor = SayDoExecutor()
    
    action = Action(
        type="say",
        parameters={"text": "Hello world"}
    )
    
    result = await executor.attempt(action)
    
    assert result is not None
    assert result["said"] == "Hello world"


@pytest.mark.asyncio
async def test_executor_do_action():
    executor = SayDoExecutor()
    
    action = Action(
        type="do",
        parameters={"task": "test_task"}
    )
    
    result = await executor.attempt(action)
    
    assert result is not None
    assert result["done"]["task"] == "test_task"


@pytest.mark.asyncio
async def test_executor_unknown_action():
    executor = SayDoExecutor()
    
    action = Action(
        type="unknown_action",
        parameters={}
    )
    
    result = await executor.attempt(action)
    
    assert result is None
