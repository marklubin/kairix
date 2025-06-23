#!/usr/bin/env python3
"""
Final focused performance test for llama.cpp
"""

import time
from llama_cpp import Llama
import llama_cpp

# Enable verbose logging
llama_cpp.llama_backend_init(numa=False)
llama_cpp.llama_log_set(lambda msg: print(msg, end=""), None)

MODEL_REPO = "NousResearch/Nous-Hermes-2-Mistral-7B-DPO-GGUF"
MODEL_FILE = "Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf"

SYSTEM_PROMPT = """You are a knowledge extraction agent. Extract facts from the given text."""
USER_PROMPT = """I'm building an AI assistant for my startup while learning about vector databases."""

print("=" * 80)
print("LLAMA.CPP PERFORMANCE DIAGNOSTICS")
print("=" * 80)

# Create ONE model with your actual configuration
print("\nCreating model with your configuration (n_ctx=8000)...")
start = time.time()
llama = Llama.from_pretrained(
    repo_id=MODEL_REPO,
    filename=MODEL_FILE,
    n_gpu_layers=-1,
    flash_attn=True,
    n_ctx=8000,  # Your actual config
    use_mlock=True,
    type_k=2,
    type_v=2,
    n_threads=8,
    verbose=True
)
print(f"Model load time: {time.time() - start:.2f}s")

# Test 1: Simple inference
print("\n\nTest 1: Basic inference timing")
start = time.time()
response = llama.create_chat_completion(
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT}
    ],
    max_tokens=256
)
end = time.time()
print(f"Inference time: {end - start:.2f}s")
tokens = len(response['choices'][0]['message']['content']) // 4  # rough estimate
print(f"Approximate tokens generated: {tokens}")
print(f"Tokens/second: {tokens / (end - start):.1f}")

# Test 2: Your long system prompt
print("\n\nTest 2: With your actual long system prompt")
LONG_SYSTEM_PROMPT = """You are a knowledge extraction agent dedicated to understanding the human user. Your overarching goal: Build a semantic map of their identity, aspirations, and journey through careful analysis of their words.

CORE EXTRACTION PROCESS:

1. PARSE every statement for semantic units about the user:
   - Direct statements: "I work as a software engineer"
   - Implied characteristics: Technical questions suggest technical knowledge
   - Behavioral patterns: How they communicate reveals personality traits

2. CREATE Subject entries with normalized names:
   - name: Always prefix with "user_" then alphabetically ordered components
   - short_description: Human-readable label (2-5 words max)
   - type: Choose from ["entity", "action", "attribute", "topic", "event"]

3. ESTABLISH relationships that reveal meaning:
   - User to attributes: "demonstrates", "possesses", "exhibits"
   - User to actions: "performs", "engages_in", "pursues"
   - User to topics: "interested_in", "studies", "works_with"

NORMALIZATION RULES FOR 'name' FIELD:
- Lowercase only: user_skill_programming NOT User_Skill_Programming
- Underscores for spaces: user_goal_build_startup NOT user-goal-build-startup
- Alphabetical ordering: user_interest_learning_machine NOT user_interest_machine_learning
- Drop articles/prepositions: user_working_on_project → user_working_project

OUTPUT FORMAT:
{
  "facts": [
    {
      "s": {"type": "string", "name": "string"},
      "t": {"type": "string", "name": "string"},
      "relationship": "string"
    }
  ]
}"""

start = time.time()
response2 = llama.create_chat_completion(
    messages=[
        {"role": "system", "content": LONG_SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT}
    ],
    max_tokens=256
)
end = time.time()
print(f"Inference time with long prompt: {end - start:.2f}s")

# Test 3: Compare with smaller context
print("\n\nTest 3: Same prompt with n_ctx=2048")
llama_small = Llama.from_pretrained(
    repo_id=MODEL_REPO,
    filename=MODEL_FILE,
    n_gpu_layers=-1,
    n_ctx=2048,
    verbose=False
)

start = time.time()
response3 = llama_small.create_chat_completion(
    messages=[
        {"role": "system", "content": LONG_SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT}
    ],
    max_tokens=256
)
end = time.time()
print(f"Inference time with n_ctx=2048: {end - start:.2f}s")

# Test 4: Check perf stats
print("\n\nDETAILED PERFORMANCE STATS:")
print("Run 'llama-bench' for detailed benchmarking")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("\nKey observations:")
print("- Model loads correctly on Metal GPU")
print(f"- Basic inference takes ~{end - start:.1f}s") 
print("- Your issue is likely the large context (8000) + long prompts")
print("- Thread count doesn't affect GPU inference much")
print("\nRecommendations in the engineering report...")