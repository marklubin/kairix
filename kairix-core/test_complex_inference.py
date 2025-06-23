#!/usr/bin/env python3
import time
import json
from llama_cpp import Llama
from typing import Literal, Optional, List
from pydantic import BaseModel, ConfigDict

# Your actual schema
class Subject(BaseModel):
    model_config = ConfigDict(strict=False)
    type: Literal["person", "organization", "concept", "topic", "action", "attribute", "event", "skill", "goal"]
    name: str

class Fact(BaseModel):
    model_config = ConfigDict(strict=False)
    s: Subject
    t: Subject
    relationship: str

class Extract(BaseModel):
    model_config = ConfigDict(strict=False)
    facts: Optional[List[Fact]]

# Your actual long prompt
LONG_PROMPT = """You are a knowledge extraction agent dedicated to understanding the human user. Build a semantic map of their identity, aspirations, and journey through careful analysis of their words.

FOCUS ON:
- Direct statements about themselves
- Implied characteristics from questions/interests
- Behavioral patterns in communication

COMMON TYPES: person, skill, goal, interest, project, attribute, capability, action, role

COMMON RELATIONSHIPS: demonstrates, possesses, engages_in, pursues, interested_in, works_with, learning, specializes_in

EXAMPLE:
{
  "facts": [
    {
      "s": {"type": "person", "name": "user"},
      "t": {"type": "action", "name": "building_ai_assistant"},
      "relationship": "engages_in"
    },
    {
      "s": {"type": "person", "name": "user"},
      "t": {"type": "skill", "name": "python_programming"},
      "relationship": "possesses"
    }
  ]
}

CORE EXTRACTION PROCESS:

1. IDENTIFY semantic units from the text
2. CREATE Subject entries with:
   - type: Choose from the provided Subject type literals
   - name: Clean identifier (no type prefix)
3. ESTABLISH relationships using the provided relationship literals

NORMALIZATION RULES FOR 'name' FIELD:
- Lowercase with underscores
- No type prefixes (type is a separate field)
- Descriptive and clear
- Drop articles/prepositions

OUTPUT FORMAT:
{
  "facts": [
    {
      "s": {"type": "string", "name": "string"},
      "t": {"type": "string", "name": "string"},
      "relationship": "string"
    }
  ]
}

OCCURRENCE TRACKING:
When you encounter semantic units multiple times:
- First occurrence: Create new node
- Subsequent occurrences: Mental note for retention weighting
- Relationship duplicates: Track frequency for importance scoring

GOAL ALIGNMENT CHECK:
Before creating any fact, ask:
- Does this serve our knowledge-building objectives?
- Will this connection enable better understanding?
- How does this fit the larger semantic landscape?

Your extractions seed a living knowledge graph that grows more intelligent with each connection."""

USER_INPUT = """I'm building an AI assistant for my startup while learning about vector databases. 
The system needs to handle real-time inference and scale to thousands of users."""

print("Testing complex inference scenario...")

# Load model
print("\nLoading model...")
model = Llama.from_pretrained(
    repo_id="NousResearch/Nous-Hermes-2-Mistral-7B-DPO-GGUF",
    filename="Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf",
    n_gpu_layers=-1,
    n_ctx=8000,
    verbose=False
)

# Test 1: Without JSON schema
print("\n1. Inference WITHOUT JSON schema enforcement:")
start = time.time()
response1 = model.create_chat_completion(
    messages=[
        {"role": "system", "content": LONG_PROMPT + "\nRespond in JSON format."},
        {"role": "user", "content": USER_INPUT}
    ],
    max_tokens=512,
    temperature=0.7
)
time1 = time.time() - start
print(f"   Time: {time1:.1f}s")
print(f"   Response length: {len(response1['choices'][0]['message']['content'])} chars")

# Test 2: With JSON schema
print("\n2. Inference WITH JSON schema enforcement:")
start = time.time()
response2 = model.create_chat_completion(
    messages=[
        {"role": "system", "content": LONG_PROMPT},
        {"role": "user", "content": USER_INPUT}
    ],
    max_tokens=512,
    temperature=0.7,
    response_format={
        "type": "json_object",
        "schema": Extract.model_json_schema()
    }
)
time2 = time.time() - start
print(f"   Time: {time2:.1f}s")
print(f"   Response length: {len(response2['choices'][0]['message']['content'])} chars")

# Test 3: Smaller prompt
print("\n3. Inference with smaller prompt:")
start = time.time()
response3 = model.create_chat_completion(
    messages=[
        {"role": "system", "content": "Extract facts as JSON."},
        {"role": "user", "content": USER_INPUT}
    ],
    max_tokens=512
)
time3 = time.time() - start
print(f"   Time: {time3:.1f}s")

# Analysis
print("\n" + "=" * 60)
print("ANALYSIS:")
print("- Base inference: ~2.2s")
print(f"- With long prompt: {time1:.1f}s ({time1/2.2:.1f}x base)")
print(f"- With schema validation: {time2:.1f}s ({time2/2.2:.1f}x base)")
print(f"- Schema overhead: {time2 - time1:.1f}s")
print(f"- Prompt size impact: {time1 - time3:.1f}s")

# Check if responses are valid JSON
try:
    json.loads(response1['choices'][0]['message']['content'])
    print("\nResponse 1: Valid JSON ✓")
except:
    print("\nResponse 1: Invalid JSON ✗")

try:
    json.loads(response2['choices'][0]['message']['content'])
    print("Response 2: Valid JSON ✓")
except:
    print("Response 2: Invalid JSON ✗")