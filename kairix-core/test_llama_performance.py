#!/usr/bin/env python3
"""
Systematic performance testing for llama.cpp inference issues.
Tests various configurations to identify the cause of slow inference.
"""

import time
import asyncio
import json
from typing import Literal, Optional, List
from pydantic import BaseModel, ConfigDict
from llama_cpp import Llama
import os

# Print basic system info
print(f"CPU Count: {os.cpu_count()}")
print("-" * 80)

# Model configuration
MODEL_REPO = "NousResearch/Nous-Hermes-2-Mistral-7B-DPO-GGUF"
MODEL_FILE = "Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf"

# Test prompt
SYSTEM_PROMPT = """You are a knowledge extraction agent. Extract facts from the given text."""
USER_PROMPT = """I'm building an AI assistant for my startup while learning about vector databases. 
The system needs to handle real-time inference and scale to thousands of users."""

# Schema for testing JSON output
class Subject(BaseModel):
    model_config = ConfigDict(strict=False)
    type: Literal["person", "concept", "action", "technology"]
    name: str

class Fact(BaseModel):
    model_config = ConfigDict(strict=False)
    s: Subject
    t: Subject
    relationship: str

class Extract(BaseModel):
    model_config = ConfigDict(strict=False)
    facts: Optional[List[Fact]]


def test_basic_inference():
    """Test 1: Basic inference with minimal configuration"""
    print("\n=== TEST 1: Basic Inference (Minimal Config) ===")
    
    start_load = time.time()
    llama = Llama.from_pretrained(
        repo_id=MODEL_REPO,
        filename=MODEL_FILE,
        n_gpu_layers=-1,
        n_ctx=2048,
        verbose=False
    )
    load_time = time.time() - start_load
    print(f"Model load time: {load_time:.2f}s")
    
    # Simple completion
    start_inference = time.time()
    response = llama.create_chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT}
        ],
        max_tokens=256
    )
    inference_time = time.time() - start_inference
    
    tokens_generated = len(response['choices'][0]['message']['content'])
    print(f"Inference time: {inference_time:.2f}s")
    print(f"Tokens generated: ~{tokens_generated//4}")
    print(f"Tokens/second: ~{(tokens_generated//4) / inference_time:.1f}")
    
    return inference_time


def test_context_sizes():
    """Test 4: Different context sizes"""
    print("\n=== TEST 4: Context Size Impact ===")
    
    context_sizes = [512, 1024, 2048, 4096, 8192]
    results = {}
    
    for ctx_size in context_sizes:
        print(f"\nTesting n_ctx={ctx_size}")
        start_load = time.time()
        
        llama = Llama.from_pretrained(
            repo_id=MODEL_REPO,
            filename=MODEL_FILE,
            n_gpu_layers=-1,
            n_ctx=ctx_size,
            verbose=False  # Less verbose for comparison
        )
        
        # Skip memory measurement for now
        
        start_inference = time.time()
        response = llama.create_chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT}
            ],
            max_tokens=256
        )
        inference_time = time.time() - start_inference
        
        results[ctx_size] = inference_time
        print(f"Inference time: {inference_time:.2f}s")
        
        # Clean up
        del llama
    
    print("\n--- Context Size Summary ---")
    for ctx, time_taken in results.items():
        print(f"n_ctx={ctx}: {time_taken:.2f}s")


def test_json_schema_impact():
    """Test 7: JSON schema validation impact"""
    print("\n=== TEST 7: JSON Schema Impact ===")
    
    llama = Llama.from_pretrained(
        repo_id=MODEL_REPO,
        filename=MODEL_FILE,
        n_gpu_layers=-1,
        n_ctx=2048,
        verbose=False
    )
    
    # Test without schema
    print("\nWithout JSON schema:")
    start = time.time()
    response1 = llama.create_chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT}
        ],
        max_tokens=256
    )
    time_no_schema = time.time() - start
    print(f"Time: {time_no_schema:.2f}s")
    
    # Test with schema
    print("\nWith JSON schema:")
    start = time.time()
    response2 = llama.create_chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT + "\nRespond with JSON."},
            {"role": "user", "content": USER_PROMPT}
        ],
        max_tokens=256,
        response_format={"type": "json_object", "schema": Extract.model_json_schema()}
    )
    time_with_schema = time.time() - start
    print(f"Time: {time_with_schema:.2f}s")
    print(f"Schema overhead: {time_with_schema - time_no_schema:.2f}s")


async def test_async_overhead():
    """Test 2: Async overhead comparison"""
    print("\n=== TEST 2: Async Overhead ===")
    
    llama = Llama.from_pretrained(
        repo_id=MODEL_REPO,
        filename=MODEL_FILE,
        n_gpu_layers=-1,
        n_ctx=2048,
        verbose=False
    )
    
    # Sync version
    def sync_inference():
        return llama.create_chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT}
            ],
            max_tokens=256
        )
    
    # Test direct sync call
    print("\nDirect sync call:")
    start = time.time()
    response = sync_inference()
    sync_time = time.time() - start
    print(f"Time: {sync_time:.2f}s")
    
    # Test with asyncio.to_thread
    print("\nWith asyncio.to_thread:")
    start = time.time()
    response = await asyncio.to_thread(sync_inference)
    async_time = time.time() - start
    print(f"Time: {async_time:.2f}s")
    print(f"Async overhead: {async_time - sync_time:.2f}s")


def test_multiple_inferences():
    """Test repeated inference to check caching behavior"""
    print("\n=== TEST: Multiple Inferences (Cache Behavior) ===")
    
    llama = Llama.from_pretrained(
        repo_id=MODEL_REPO,
        filename=MODEL_FILE,
        n_gpu_layers=-1,
        n_ctx=2048,
        verbose=False,
        cache_prompt=True  # Enable prompt caching
    )
    
    times = []
    for i in range(5):
        start = time.time()
        response = llama.create_chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT if i == 0 else f"{USER_PROMPT} Run {i}"}
            ],
            max_tokens=256
        )
        elapsed = time.time() - start
        times.append(elapsed)
        print(f"Run {i+1}: {elapsed:.2f}s")
    
    print(f"\nAverage time: {sum(times)/len(times):.2f}s")
    print(f"First run: {times[0]:.2f}s, Subsequent avg: {sum(times[1:])/len(times[1:]):.2f}s")


def test_thread_configuration():
    """Test different thread configurations"""
    print("\n=== TEST: Thread Configuration ===")
    
    thread_counts = [1, 4, 8, 16]
    
    for n_threads in thread_counts:
        print(f"\nTesting n_threads={n_threads}")
        
        llama = Llama.from_pretrained(
            repo_id=MODEL_REPO,
            filename=MODEL_FILE,
            n_gpu_layers=-1,
            n_ctx=2048,
            n_threads=n_threads,
            verbose=False
        )
        
        start = time.time()
        response = llama.create_chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT}
            ],
            max_tokens=256
        )
        elapsed = time.time() - start
        print(f"Time: {elapsed:.2f}s")
        
        del llama


async def main():
    """Run all tests systematically"""
    print("Starting systematic performance tests for llama.cpp")
    print("=" * 80)
    
    # Test 1: Basic inference
    test_basic_inference()
    
    # Test 2: Async overhead
    await test_async_overhead()
    
    # Test 4: Context sizes
    test_context_sizes()
    
    # Test 7: JSON schema impact
    test_json_schema_impact()
    
    # Additional tests
    test_multiple_inferences()
    test_thread_configuration()
    
    print("\n" + "=" * 80)
    print("Testing complete. Check results above for performance bottlenecks.")


if __name__ == "__main__":
    asyncio.run(main())