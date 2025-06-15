"""Test OpenAI API parallelism with multiple concurrent requests."""

import asyncio
import os
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest
from agents import Runner

from kairix_engine.basic_chat import Chat


@pytest.mark.asyncio
async def test_openai_concurrent_requests():
    """Test if multiple OpenAI requests can run concurrently."""
    
    # Mock the Runner to simulate API calls
    mock_responses = []
    call_times = []
    
    async def mock_run(agent, prompt):
        start_time = time.time()
        call_times.append(start_time)
        
        # Simulate API latency
        await asyncio.sleep(0.1)  # 100ms simulated latency
        
        response = Mock()
        response.final_output_as = Mock(return_value=f"Response for: {prompt[:20]}...")
        mock_responses.append(response)
        return response
    
    # Mock perceptor
    mock_perceptor = Mock()
    mock_perceptor.perceive = AsyncMock(return_value=[])
    
    # Create multiple chat instances
    chats = []
    for _ in range(5):
        chat = Chat(
            user_name="Test",
            agent_name="Assistant",
            perceptor=mock_perceptor,
            enable_history=False
        )
        chats.append(chat)
    
    with patch("kairix_engine.basic_chat.Runner.run", side_effect=mock_run):
        # Prepare tasks for concurrent execution
        tasks = []
        messages = [f"Message {i}: What is {i} + {i}?" for i in range(5)]
        
        start_time = time.time()
        
        # Create tasks
        for chat, msg in zip(chats, messages, strict=False):
            task = chat.chat(msg)
            tasks.append(task)
        
        # Run concurrently with gather
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify all requests completed
        assert len(results) == 5
        assert all(r.startswith("Response for:") for r in results)
        
        # Check if requests were concurrent
        # If sequential: ~500ms (5 * 100ms)
        # If concurrent: ~100ms (plus overhead)
        assert total_time < 0.3, f"Requests took {total_time:.2f}s - not concurrent!"
        
        # Verify call times are close together (started within 50ms)
        if call_times:
            time_spread = max(call_times) - min(call_times)
            assert time_spread < 0.05, f"Calls spread over {time_spread:.2f}s"
        
        print(f"✓ Completed 5 requests in {total_time:.2f}s")
        print(f"✓ Calls initiated within {time_spread:.2f}s of each other")


@pytest.mark.asyncio
async def test_openai_streaming_parallelism():
    """Test if streaming responses can be processed concurrently."""
    
    async def mock_stream_generator(msg):
        """Simulate streaming response."""
        words = msg.split()
        for word in words:
            await asyncio.sleep(0.01)  # Simulate streaming delay
            yield word + " "
    
    class MockResult:
        def __init__(self, msg):
            self.msg = msg
            
        def final_output_as(self, type_):
            return f"Final: {self.msg}"
    
    def mock_run_streamed(agent, prompt):
        return MockResult(prompt)
    
    async def mock_stream_text_from(result):
        async for chunk in mock_stream_generator(result.msg):
            yield chunk
    
    # Mock perceptor
    mock_perceptor = Mock()
    mock_perceptor.perceive = AsyncMock(return_value=[])
    
    # Create chat instances
    chats = []
    for _ in range(3):
        chat = Chat(
            user_name="Test",
            agent_name="Assistant",
            perceptor=mock_perceptor,
            enable_history=False
        )
        chats.append(chat)
    
    with (
        patch("kairix_engine.basic_chat.Runner.run_streamed", 
              side_effect=mock_run_streamed),
        patch("kairix_engine.basic_chat.VoiceWorkflowHelper.stream_text_from", 
              side_effect=mock_stream_text_from)
    ):
        
        async def collect_stream(chat, msg):
            """Collect all chunks from a stream."""
            chunks = []
            async for chunk in chat.run(msg):
                chunks.append(chunk)
            return "".join(chunks)
        
        # Run multiple streams concurrently
        messages = [
            "Hello world one", 
            "Testing concurrent two", 
            "Parallel streams three"
        ]
        
        start_time = time.time()
        
        tasks = [
            collect_stream(chat, msg) 
            for chat, msg in zip(chats, messages, strict=False)
        ]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify results
        assert len(results) == 3
        assert "Hello world one" in results[0]
        assert "Testing concurrent two" in results[1]
        assert "Parallel streams three" in results[2]
        
        # Check concurrency - should be faster than sequential
        # Sequential would take ~0.09s (3 messages * 3 words * 0.01s)
        assert total_time < 0.06, f"Streaming took {total_time:.2f}s - not concurrent!"
        
        print(f"✓ Streamed 3 responses concurrently in {total_time:.2f}s")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set"
)
async def test_real_openai_parallelism():
    """Test real OpenAI API parallelism (requires API key)."""
    from cognition_engine.perceptor.conversation_remembering_perceptor import (
        ConversationRememberingPerceptor,
    )
    
    # Create a simple memory provider
    def memory_provider(query, k):
        return []
    
    # Create perceptor
    perceptor = ConversationRememberingPerceptor(
        Runner(),
        memory_provider=memory_provider,
        k_memories=0  # No memories for this test
    )
    
    # Create multiple chat instances
    chats = []
    for i in range(3):
        chat = Chat(
            user_name="Test",
            agent_name=f"Assistant{i}",
            perceptor=perceptor,
            enable_history=False
        )
        await chat.initialize()
        chats.append(chat)
    
    # Different questions to avoid caching
    questions = [
        "What is 123 + 456?",
        "What is the capital of France?",
        "How many days in a week?"
    ]
    
    start_time = time.time()
    
    # Run requests concurrently
    tasks = [chat.chat(q) for chat, q in zip(chats, questions, strict=False)]
    results = await asyncio.gather(*tasks)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Verify we got responses
    assert len(results) == 3
    assert "579" in results[0] or "five hundred" in results[0].lower()
    assert "paris" in results[1].lower()
    assert "7" in results[2] or "seven" in results[2].lower()
    
    print(f"✓ Real API: 3 concurrent requests completed in {total_time:.2f}s")
    print(f"✓ Average time per request: {total_time/3:.2f}s")
    
    # Close chats
    for chat in chats:
        await chat.close()