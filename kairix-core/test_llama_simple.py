#!/usr/bin/env python3
"""
Simplified performance test for llama.cpp to identify bottlenecks
"""

import time
import asyncio
from llama_cpp import Llama

MODEL_REPO = "NousResearch/Nous-Hermes-2-Mistral-7B-DPO-GGUF"
MODEL_FILE = "Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf"

SYSTEM_PROMPT = """You are a knowledge extraction agent. Extract facts from the given text."""
USER_PROMPT = """I'm building an AI assistant for my startup while learning about vector databases."""

def time_it(func, name):
    """Time a function and print results"""
    start = time.time()
    result = func()
    elapsed = time.time() - start
    print(f"{name}: {elapsed:.2f}s")
    return result, elapsed

print("=" * 80)
print("LLAMA.CPP PERFORMANCE TEST")
print("=" * 80)

# Test 1: Basic inference timing
print("\nTest 1: Basic Inference (n_ctx=2048)")
llama1, load_time = time_it(
    lambda: Llama.from_pretrained(
        repo_id=MODEL_REPO,
        filename=MODEL_FILE,
        n_gpu_layers=-1,
        n_ctx=2048,
        verbose=False
    ),
    "Model Load"
)

response1, inf_time1 = time_it(
    lambda: llama1.create_chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT}
        ],
        max_tokens=256
    ),
    "First Inference"
)

# Test subsequent inference (cache should help)
response2, inf_time2 = time_it(
    lambda: llama1.create_chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT + " This is run 2."}
        ],
        max_tokens=256
    ),
    "Second Inference"
)

print(f"Cache speedup: {inf_time1/inf_time2:.2f}x")

# Test 2: Context size impact
print("\n\nTest 2: Context Size Impact")
for ctx_size in [512, 2048, 8192]:
    print(f"\nn_ctx={ctx_size}:")
    
    llama_ctx = Llama.from_pretrained(
        repo_id=MODEL_REPO,
        filename=MODEL_FILE,
        n_gpu_layers=-1,
        n_ctx=ctx_size,
        verbose=False
    )
    
    _, ctx_time = time_it(
        lambda: llama_ctx.create_chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT}
            ],
            max_tokens=256
        ),
        f"  Inference"
    )
    del llama_ctx

# Test 3: Thread count impact
print("\n\nTest 3: Thread Count Impact (n_ctx=2048)")
for n_threads in [1, 4, 8]:
    print(f"\nn_threads={n_threads}:")
    
    llama_threads = Llama.from_pretrained(
        repo_id=MODEL_REPO,
        filename=MODEL_FILE,
        n_gpu_layers=-1,
        n_ctx=2048,
        n_threads=n_threads,
        verbose=False
    )
    
    _, thread_time = time_it(
        lambda: llama_threads.create_chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT}
            ],
            max_tokens=256
        ),
        f"  Inference"
    )
    del llama_threads

# Test 4: Async overhead
print("\n\nTest 4: Async Overhead")
llama_async = Llama.from_pretrained(
    repo_id=MODEL_REPO,
    filename=MODEL_FILE,
    n_gpu_layers=-1,
    n_ctx=2048,
    verbose=False
)

def sync_call():
    return llama_async.create_chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT}
        ],
        max_tokens=256
    )

_, sync_time = time_it(sync_call, "Sync call")

async def async_call():
    return await asyncio.to_thread(sync_call)

async def test_async():
    _, async_time = time_it(
        lambda: asyncio.run(async_call()),
        "Async call"
    )
    print(f"Async overhead: {async_time - sync_time:.2f}s ({(async_time/sync_time - 1)*100:.1f}%)")

asyncio.run(test_async())

# Test 5: Multiple models (pooling simulation)
print("\n\nTest 5: Multiple Models (Pool Simulation)")
print("Creating 3 models...")
models = []
for i in range(3):
    model = Llama.from_pretrained(
        repo_id=MODEL_REPO,
        filename=MODEL_FILE,
        n_gpu_layers=-1,
        n_ctx=2048,
        verbose=False
    )
    models.append(model)
    print(f"  Model {i+1} loaded")

print("\nTesting inference on each model:")
for i, model in enumerate(models):
    _, pool_time = time_it(
        lambda: model.create_chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT}
            ],
            max_tokens=256
        ),
        f"  Model {i+1}"
    )

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)

# Print summary
print("\nKEY FINDINGS:")
print(f"- Base inference time: ~{inf_time1:.1f}s")
print(f"- Model load time: ~{load_time:.1f}s") 
print(f"- Cache provides ~{inf_time1/inf_time2:.1f}x speedup")
print("\nCheck the results above to identify bottlenecks.")