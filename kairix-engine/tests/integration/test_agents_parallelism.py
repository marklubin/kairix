"""Test if the agents library supports parallel execution."""

import asyncio
import os
import time

import pytest
from agents import Agent, Runner


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set"
)
async def test_agents_library_parallelism():
    """Test if multiple agents can run concurrently using the agents library."""
    
    # Create multiple agents with different names
    agents = []
    for i in range(5):
        agent = Agent(
            name=f"assistant-{i}",
            instructions=f"You are assistant {i}. Answer questions concisely.",
            model="gpt-4o-mini",
        )
        agents.append(agent)
    
    # Different questions to avoid caching
    questions = [
        "What is 15 + 27?",
        "Name the largest ocean",
        "What year did WW2 end?",
        "How many continents are there?",
        "What is the speed of light?"
    ]
    
    async def run_agent(agent: Agent, question: str) -> tuple[str, float, float]:
        """Run a single agent and track timing."""
        start_time = time.time()
        
        result = await Runner.run(agent, question)
        response = result.final_output_as(str)
        
        end_time = time.time()
        duration = end_time - start_time
        
        return response, start_time, duration
    
    # Test 1: Sequential execution
    print("\n=== Sequential Agent Execution ===")
    sequential_start = time.time()
    sequential_results = []
    
    for agent, question in zip(agents, questions, strict=False):
        result = await run_agent(agent, question)
        sequential_results.append(result)
        print(f"{agent.name} completed in {result[2]:.2f}s")
    
    sequential_total = time.time() - sequential_start
    print(f"Total sequential time: {sequential_total:.2f}s")
    
    # Test 2: Concurrent execution
    print("\n=== Concurrent Agent Execution ===")
    concurrent_start = time.time()
    
    # Create all tasks at once
    tasks = [
        run_agent(agent, question) 
        for agent, question in zip(agents, questions, strict=False)
    ]
    concurrent_results = await asyncio.gather(*tasks)
    
    concurrent_total = time.time() - concurrent_start
    
    # Analyze results
    for i, (response, start, duration) in enumerate(concurrent_results):
        relative_start = start - concurrent_start
        print(f"assistant-{i} started at +{relative_start:.3f}s, took {duration:.2f}s")
        print(f"  Response: {response[:50]}...")
    
    print(f"\nTotal concurrent time: {concurrent_total:.2f}s")
    
    # Calculate speedup
    speedup = sequential_total / concurrent_total
    print(f"\n🚀 Speedup: {speedup:.2f}x")
    print(f"✓ Agents are {'CONCURRENT' if speedup > 2 else 'SEQUENTIAL'}")
    
    # Verify concurrent execution
    start_times = [r[1] for r in concurrent_results]
    start_spread = max(start_times) - min(start_times)
    print(f"✓ All agents started within {start_spread:.3f}s of each other")
    
    assert speedup > 2, f"Expected >2x speedup, got {speedup:.2f}x"
    assert start_spread < 0.1, (
        f"Agents not started concurrently: {start_spread:.3f}s spread"
    )


@pytest.mark.asyncio
async def test_agents_with_shared_resources():
    """Test if agents can share resources while running concurrently."""
    
    # Shared counter to test thread safety
    call_count = 0
    call_times = []
    
    async def mock_api_call():
        """Simulate an API call with tracking."""
        nonlocal call_count
        call_count += 1
        call_times.append(time.time())
        await asyncio.sleep(0.1)  # Simulate API latency
        return f"Response {call_count}"
    
    # Create agents that use the shared resource
    agents = []
    for i in range(3):
        agent = Agent(
            name=f"agent-{i}",
            instructions="Answer briefly.",
            model="gpt-4o-mini",
        )
        agents.append(agent)
    
    # Mock the OpenAI call
    from unittest.mock import AsyncMock, patch
    
    with patch("agents.models.openai_chatcompletions.AsyncOpenAI") as mock_openai:
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client
        
        # Mock the chat completions
        async def mock_create(**kwargs):
            result = await mock_api_call()
            mock_response = AsyncMock()
            mock_response.choices = [
                AsyncMock(message=AsyncMock(content=result))
            ]
            return mock_response
        
        mock_client.chat.completions.create = mock_create
        
        # Run agents concurrently
        start_time = time.time()
        tasks = [Runner.run(agent, f"Question {i}") for i, agent in enumerate(agents)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Verify all agents completed
        assert len(results) == 3
        assert call_count == 3
        
        # Check timing
        assert total_time < 0.3, f"Took {total_time:.2f}s - not concurrent"
        
        # Check call times are close
        if call_times:
            spread = max(call_times) - min(call_times)
            assert spread < 0.05, f"Calls spread over {spread:.2f}s"
        
        print(f"✓ 3 agents completed concurrently in {total_time:.2f}s")
        print(f"✓ Shared resource accessed safely {call_count} times")