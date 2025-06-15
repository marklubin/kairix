"""Test real OpenAI API parallelism to answer your question."""

import asyncio
import os
import time

import pytest
from openai import AsyncOpenAI


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set"
)
async def test_openai_native_parallelism():
    """Test if OpenAI AsyncClient supports true parallel requests."""
    
    client = AsyncOpenAI()
    
    async def make_request(prompt: str) -> tuple[str, float, float]:
        """Make a single request and track timing."""
        start_time = time.time()
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        content = response.choices[0].message.content or ""
        return content, start_time, duration
    
    # Test 1: Sequential requests
    print("\n=== Sequential Requests ===")
    sequential_start = time.time()
    sequential_results = []
    
    prompts = [
        "What is 2+2?",
        "What is the capital of France?",
        "What color is the sky?",
        "How many days in a week?",
        "What is 10*10?"
    ]
    
    for prompt in prompts:
        result = await make_request(prompt)
        sequential_results.append(result)
        print(f"Request completed in {result[2]:.2f}s")
    
    sequential_total = time.time() - sequential_start
    print(f"Total sequential time: {sequential_total:.2f}s")
    
    # Test 2: Concurrent requests with asyncio.gather
    print("\n=== Concurrent Requests ===")
    concurrent_start = time.time()
    
    # Create all tasks at once
    tasks = [make_request(prompt) for prompt in prompts]
    concurrent_results = await asyncio.gather(*tasks)
    
    concurrent_total = time.time() - concurrent_start
    
    # Analyze results
    for i, (_content, start, duration) in enumerate(concurrent_results):
        relative_start = start - concurrent_start
        print(f"Request {i+1} started at +{relative_start:.3f}s, took {duration:.2f}s")
    
    print(f"Total concurrent time: {concurrent_total:.2f}s")
    
    # Calculate speedup
    speedup = sequential_total / concurrent_total
    print(f"\n🚀 Speedup: {speedup:.2f}x")
    print(f"✓ Requests are {'CONCURRENT' if speedup > 2 else 'SEQUENTIAL'}")
    
    # Verify the requests actually ran in parallel
    # Check if all requests started within 100ms of each other
    start_times = [r[1] for r in concurrent_results]
    start_spread = max(start_times) - min(start_times)
    print(f"✓ All requests started within {start_spread:.3f}s of each other")
    
    assert speedup > 2, f"Expected >2x speedup, got {speedup:.2f}x"
    assert start_spread < 0.1, (
        f"Requests not started concurrently: {start_spread:.3f}s spread"
    )


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set"
)
async def test_openai_streaming_parallelism():
    """Test if OpenAI streaming can be done in parallel."""
    
    client = AsyncOpenAI()
    
    async def stream_request(prompt: str) -> tuple[str, float, list[float]]:
        """Stream a request and collect chunks with timing."""
        start_time = time.time()
        chunk_times = []
        chunks = []
        
        stream = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            stream=True
        )
        
        async for chunk in stream:
            chunk_time = time.time() - start_time
            chunk_times.append(chunk_time)
            
            if chunk.choices[0].delta.content:
                chunks.append(chunk.choices[0].delta.content)
        
        full_response = "".join(chunks)
        total_time = time.time() - start_time
        
        return full_response, total_time, chunk_times
    
    print("\n=== Testing Parallel Streaming ===")
    
    prompts = [
        "Count from 1 to 10 slowly",
        "List 5 colors",
        "Name 5 animals"
    ]
    
    # Run streams in parallel
    start_time = time.time()
    tasks = [stream_request(prompt) for prompt in prompts]
    results = await asyncio.gather(*tasks)
    total_time = time.time() - start_time
    
    # Analyze results
    for i, (response, duration, chunk_times) in enumerate(results):
        print(f"\nStream {i+1}:")
        print(f"  Response: {response[:50]}...")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Chunks: {len(chunk_times)}")
        if chunk_times:
            print(f"  First chunk at: {chunk_times[0]:.3f}s")
        else:
            print("  No chunks")
    
    print(f"\nTotal time for {len(prompts)} parallel streams: {total_time:.2f}s")
    
    # Check if streams were concurrent
    # If they were sequential, total time would be sum of individual times
    individual_times = [r[1] for r in results]
    sequential_estimate = sum(individual_times)
    
    speedup = sequential_estimate / total_time
    print(f"✓ Streaming speedup: {speedup:.2f}x")
    
    assert speedup > 1.5, f"Streams not running in parallel: {speedup:.2f}x speedup"