# Kairix Evaluation Framework

This directory contains LLM-based evaluations for the Kairix memory architecture using [DeepEval](https://deepeval.com).

## Quick Start

```bash
# Install eval dependencies
cd kp3
uv sync --extra eval

# Set judge model API key
export DEEPSEEK_API_KEY="sk-..."

# Run all evaluations
deepeval test run tests/evals/

# Run specific test file
deepeval test run tests/evals/test_summary_quality.py

# Run with parallel execution (4 workers)
deepeval test run tests/evals/ -n 4

# Run via pytest (alternative)
uv run pytest tests/evals/ -m eval -v
```

## DeepEval Primer

### What is DeepEval?

DeepEval is an open-source framework for evaluating LLM applications. Instead of writing custom scoring logic, you define **metrics** that describe what "good" looks like, and DeepEval uses an LLM judge to score outputs.

### Core Concepts

#### 1. Test Cases (`LLMTestCase`)

A test case packages the data needed for evaluation:

```python
from deepeval.test_case import LLMTestCase

test_case = LLMTestCase(
    input="What's the weather?",           # User's input
    actual_output="It's sunny in Paris.",   # LLM's response
    expected_output="Sunny, 24°C",          # Optional: ideal response
    context=["Weather data: Paris, sunny"], # Optional: retrieval context
)
```

| Field | Purpose |
|-------|---------|
| `input` | The prompt or user message |
| `actual_output` | The LLM's response to evaluate |
| `expected_output` | Optional ideal response for comparison |
| `context` | Optional retrieved context (for RAG evaluation) |
| `retrieval_context` | Alternative field for retrieved documents |

#### 2. Metrics

Metrics define evaluation criteria. DeepEval provides built-in metrics and supports custom ones.

**Built-in Metrics:**
- `SummarizationMetric` - Evaluates summary coverage and alignment
- `FaithfulnessMetric` - Checks if output is grounded in context
- `AnswerRelevancyMetric` - Evaluates response relevance
- `KnowledgeRetentionMetric` - Tests memory across conversation turns
- `RoleAdherenceMetric` - Checks persona/role consistency

**Custom Metrics with GEval:**

GEval lets you define metrics using natural language criteria:

```python
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams

my_metric = GEval(
    name="MyMetric",
    criteria="Evaluate whether the response is helpful and accurate.",
    evaluation_steps=[
        "Check if the response addresses the user's question.",
        "Verify factual claims are accurate.",
        "Score 1.0 for excellent, 0.0 for poor.",
    ],
    evaluation_params=[
        LLMTestCaseParams.INPUT,
        LLMTestCaseParams.ACTUAL_OUTPUT,
    ],
    threshold=0.7,  # Minimum passing score
)
```

#### 3. Running Evaluations

**With `assert_test`** (fails if below threshold):
```python
from deepeval import assert_test

def test_response_quality():
    test_case = LLMTestCase(...)
    assert_test(test_case, [my_metric])
```

**With `measure`** (returns score for inspection):
```python
my_metric.measure(test_case)
print(my_metric.score)   # 0.0 - 1.0
print(my_metric.reason)  # Judge's explanation
```

#### 4. Evaluation Parameters

The `evaluation_params` field tells GEval which test case fields to pass to the judge:

| Parameter | Maps To |
|-----------|---------|
| `LLMTestCaseParams.INPUT` | `test_case.input` |
| `LLMTestCaseParams.ACTUAL_OUTPUT` | `test_case.actual_output` |
| `LLMTestCaseParams.EXPECTED_OUTPUT` | `test_case.expected_output` |
| `LLMTestCaseParams.CONTEXT` | `test_case.context` |

---

## Our Evaluation Strategy

### What We're Evaluating

Kairix's memory architecture has three main evaluation surfaces:

1. **Session Summaries** - Generated after conversation sessions end
2. **Block Updates** - Updates to human/persona/world memory blocks
3. **Conversational Responses** - How well the agent uses memory in responses

### Metric Design Philosophy

Our metrics are designed around Kairix's core goal: **longitudinal understanding**.

The agent should feel like a peer who knows you over time, not a stateless assistant or a system that announces "According to my database...".

#### Summary Quality Metrics

| Metric | What It Tests | Why It Matters |
|--------|---------------|----------------|
| `SummaryFactualCoverage` | Are key facts captured? | Summaries feed into KP3 for retrieval |
| `EmotionalTonePreservation` | Is emotional context preserved? | Memory should capture *how* things were said |
| `TemporalAccuracy` | Are time references correct? | "Tomorrow" in transcript ≠ "yesterday" in summary |

**Example test case structure:**
```python
# Good: Captures facts + emotion
"Mark is frustrated after three months of job searching..."

# Bad: Misses emotional context
"Mark is exploring job opportunities..."

# Bad: Wrong temporal reference
"Mark finished the project last week..."  # (was "next week" in transcript)
```

#### Block Quality Metrics

| Metric | What It Tests | Why It Matters |
|--------|---------------|----------------|
| `HumanBlockAccuracy` | Are user facts correct? | Hallucinated user info erodes trust |
| `UpdateNecessity` | Does update add value? | Prevent churn / unnecessary rewrites |
| `PersonaConsistency` | Does persona stay coherent? | Contradictory persona confuses users |
| `NoSycophancy` | Is response substantive? | Flattery without substance is useless |

**The sycophancy problem:**

```python
# Bad: Sycophantic
"Great question! That's a wonderful approach! You're so talented!"

# Good: Direct and substantive
"The approach has merit, but consider the memory pressure trade-off..."
```

#### Conversational Quality Metrics

| Metric | What It Tests | Why It Matters |
|--------|---------------|----------------|
| `NaturalMemoryUsage` | Is memory used without announcing? | "I remember..." feels robotic |
| `PersonalizationDepth` | Does response use context? | Generic responses waste memory |
| `ContinuityScore` | Does it build on past? | Relationships have continuity |

**The memory announcement problem:**

```python
# Bad: Announced
"I remember from our previous conversations that you prefer async..."

# Good: Natural
"Given your preference for async communication, I'd suggest a doc..."
```

---

## Test Data Design

### Positive vs Negative Cases

Each test file includes:
1. **Positive cases** - Examples that should pass (score ≥ threshold)
2. **Negative cases** - Examples that should fail (score < threshold)

Testing both ensures the metric can distinguish quality.

### Realistic Scenarios

Test data is based on realistic Kairix use cases:

| Scenario | What It Tests |
|----------|---------------|
| Technical project discussion | Factual coverage, temporal accuracy |
| Emotional support conversation | Tone preservation, empathy |
| Job search frustration | Emotional context, personalization |
| Database design decision | Continuity, building on past |

### Ground Truth Strategy

We use **synthetic ground truth** - carefully crafted examples where we know what "good" looks like. This is more reliable than automated generation for evaluation design.

---

## Directory Structure

```
tests/evals/
├── README.md                    # This file
├── conftest.py                  # Judge model configuration
├── metrics/
│   ├── __init__.py              # Metric exports
│   ├── summary.py               # Summary quality metrics
│   ├── blocks.py                # Block update metrics
│   └── conversational.py        # Multi-turn conversation metrics
├── datasets/                    # Test data (future expansion)
├── test_summary_quality.py      # Summary evaluation tests
├── test_block_quality.py        # Block update tests
└── test_conversational.py       # Conversational quality tests
```

---

## Configuration

### Judge Model

We use DeepSeek as the judge model (configured in `conftest.py`):

```python
os.environ["DEEPEVAL_LLM_MODEL"] = "deepseek/deepseek-chat"
os.environ["DEEPEVAL_LLM_BASE_URL"] = "https://api.deepseek.com"
```

DeepSeek provides good evaluation quality at lower cost than GPT-4.

### Thresholds

Each metric has a `threshold` - the minimum score to pass:

| Metric Type | Typical Threshold | Rationale |
|-------------|-------------------|-----------|
| Factual accuracy | 0.7 - 0.8 | Some flexibility for wording |
| Tone preservation | 0.7 | Subjective, allow variation |
| Temporal accuracy | 0.8 | Facts should be correct |
| No sycophancy | 0.8 | Strong preference for direct |
| Natural memory | 0.9 | Memory announcements are obvious |

---

## Adding New Tests

### 1. Define the metric (if new)

```python
# metrics/my_category.py
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams

my_new_metric = GEval(
    name="MyNewMetric",
    criteria="...",
    evaluation_steps=["...", "..."],
    evaluation_params=[...],
    threshold=0.7,
)
```

### 2. Create test data

Design positive and negative examples that clearly distinguish quality.

### 3. Write the test

```python
# test_my_category.py
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from tests.evals.metrics.my_category import my_new_metric

@pytest.mark.eval
class TestMyCategory:
    def test_good_example_passes(self):
        test_case = LLMTestCase(
            input="...",
            actual_output="...",  # Good example
        )
        assert_test(test_case, [my_new_metric])

    def test_bad_example_fails(self):
        test_case = LLMTestCase(
            input="...",
            actual_output="...",  # Bad example
        )
        my_new_metric.measure(test_case)
        assert my_new_metric.score < 0.5
```

---

## Troubleshooting

### "OPENAI_API_KEY required"

DeepEval uses the OpenAI client internally. Set your DeepSeek key:

```bash
export DEEPSEEK_API_KEY="sk-..."
# or
export OPENAI_API_KEY="sk-..."  # DeepEval will use this
```

### Slow tests

Use parallel execution:
```bash
deepeval test run tests/evals/ -n 4
```

### Flaky scores

LLM judges can have variance. If a test is flaky:
1. Make the test case more clear-cut
2. Adjust threshold (but document why)
3. Consider if the metric criteria needs refinement

---

## References

- [DeepEval Documentation](https://docs.confident-ai.com/)
- [GEval Paper](https://arxiv.org/abs/2303.16634) - The research behind GEval
- [LLM-as-Judge](https://arxiv.org/abs/2306.05685) - Theory of using LLMs for evaluation
- [Kairix World Model Design](/docs/kp3-world-model-design.md) - Memory architecture context
