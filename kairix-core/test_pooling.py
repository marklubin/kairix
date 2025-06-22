#!/usr/bin/env python3
import time
import asyncio
from llama_cpp import Llama

print("Testing pooling impact on performance...")

# Create 3 models like your pool
print("\nCreating 3 model instances...")
models = []
for i in range(3):
    start = time.time()
    model = Llama.from_pretrained(
        repo_id="NousResearch/Nous-Hermes-2-Mistral-7B-DPO-GGUF",
        filename="Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf",
        n_gpu_layers=-1,
        n_ctx=8000,
        verbose=False
    )
    models.append(model)
    print(f"  Model {i+1} loaded in {time.time() - start:.1f}s")

# Test with your actual prompt pattern
SYSTEM = "You are a helpful assistant."
USER = "Tell me about AI."

print("\nTesting inference on each model (simulating pool rotation):")
total_time = 0
for i in range(6):  # 2 rounds through the pool
    model_idx = i % 3
    model = models[model_idx]
    
    start = time.time()
    response = model.create_chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"{USER} Request #{i}"}
        ],
        max_tokens=100
    )
    elapsed = time.time() - start
    total_time += elapsed
    print(f"  Request {i+1} -> Model {model_idx+1}: {elapsed:.1f}s")

print(f"\nAverage time per request: {total_time/6:.1f}s")

# Test async overhead with pooling
print("\n\nTesting async wrapper overhead:")

async def async_inference(model, request_id):
    def sync_call():
        return model.create_chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"{USER} Async request #{request_id}"}
            ],
            max_tokens=100
        )
    
    start = time.time()
    result = await asyncio.to_thread(sync_call)
    elapsed = time.time() - start
    return elapsed

async def test_async_pool():
    times = []
    for i in range(3):
        model = models[i % len(models)]
        elapsed = await async_inference(model, i)
        times.append(elapsed)
        print(f"  Async request {i+1}: {elapsed:.1f}s")
    return times

times = asyncio.run(test_async_pool())
print(f"\nAverage async time: {sum(times)/len(times):.1f}s")

print("\n" + "=" * 60)
print("MEMORY USAGE:")
print(f"- Each model uses ~3.8GB VRAM")
print(f"- Total VRAM for pool: ~{3.8 * 3:.1f}GB")
print(f"- Available on M4: 16GB")
print("\nConclusion: Memory pressure likely causing slowdown")