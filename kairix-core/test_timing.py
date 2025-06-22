#!/usr/bin/env python3
import time
from llama_cpp import Llama

# Minimal test to isolate the issue
print("Testing llama.cpp performance...")

# Test 1: Small context
print("\n1. Loading model with n_ctx=2048...")
start = time.time()
model_small = Llama.from_pretrained(
    repo_id="NousResearch/Nous-Hermes-2-Mistral-7B-DPO-GGUF",
    filename="Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf",
    n_gpu_layers=-1,
    n_ctx=2048,
    verbose=False
)
load_time_small = time.time() - start
print(f"   Load time: {load_time_small:.1f}s")

start = time.time()
resp = model_small("Hello, how are you?", max_tokens=50)
inf_time_small = time.time() - start
print(f"   Inference time: {inf_time_small:.1f}s")

# Test 2: Large context (your config)
print("\n2. Loading model with n_ctx=8000...")
start = time.time()
model_large = Llama.from_pretrained(
    repo_id="NousResearch/Nous-Hermes-2-Mistral-7B-DPO-GGUF",
    filename="Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf",
    n_gpu_layers=-1,
    n_ctx=8000,
    flash_attn=True,
    use_mlock=True,
    verbose=False
)
load_time_large = time.time() - start
print(f"   Load time: {load_time_large:.1f}s")

start = time.time()
resp = model_large("Hello, how are you?", max_tokens=50)
inf_time_large = time.time() - start
print(f"   Inference time: {inf_time_large:.1f}s")

# Test 3: Multiple inference (pooling simulation)
print("\n3. Testing multiple sequential inferences...")
times = []
for i in range(3):
    start = time.time()
    resp = model_large(f"Hello, how are you? This is request {i}", max_tokens=50)
    elapsed = time.time() - start
    times.append(elapsed)
    print(f"   Run {i+1}: {elapsed:.1f}s")

print(f"\n   Average: {sum(times)/len(times):.1f}s")

print("\nSUMMARY:")
print(f"Context size impact: {inf_time_large/inf_time_small:.1f}x slower with 8k context")
print(f"Load time difference: {load_time_large - load_time_small:.1f}s")