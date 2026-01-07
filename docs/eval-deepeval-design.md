# Kairix Evaluation Framework v2 - DeepEval Implementation

## Overview

Replace the partially-implemented custom eval framework (`kp3/src/kp3/evals/`) with [DeepEval](https://deepeval.com), an open-source LLM evaluation framework that provides:

- Built-in metrics for summarization, knowledge retention, role adherence, faithfulness
- Custom metric support via `GEval` and `ConversationalGEval`
- pytest integration for CI/CD
- Dataset management and synthetic data generation
- Optional Confident AI cloud dashboard

**Location:** `~/kairix/kp3/tests/evals/` (pytest-based, alongside existing tests)

---

## Part 1: Metric Mapping

Map original evaluation goals to DeepEval metrics:

### 1.1 Summary Quality

| Original Criterion | DeepEval Metric | Notes |
|-------------------|-----------------|-------|
| Factual completeness | `SummarizationMetric` | Built-in coverage + alignment scores |
| Temporal accuracy | `GEval` (custom) | Custom criteria for time references |
| Emotional tone preservation | `GEval` (custom) | Custom criteria for tone |

### 1.2 Block Update Quality

| Original Criterion | DeepEval Metric | Notes |
|-------------------|-----------------|-------|
| Persona consistency | `RoleAdherenceMetric` | Built-in for role/persona |
| Human block accuracy | `FaithfulnessMetric` | Facts grounded in context |
| World block relevance | `GEval` (custom) | Custom relevance criteria |
| Update necessity | `GEval` (custom) | Was update meaningful? |

### 1.3 Conversational Quality

| Original Criterion | DeepEval Metric | Notes |
|-------------------|-----------------|-------|
| Knowledge retention | `KnowledgeRetentionMetric` | Built-in for multi-turn |
| Personalization depth | `ConversationalGEval` | Custom criteria |
| Continuity score | `ConversationalGEval` | References to past context |

### 1.4 Retrieval Quality (KP3)

| Original Criterion | DeepEval Metric | Notes |
|-------------------|-----------------|-------|
| Search relevance | `ContextualRelevancyMetric` | Retrieved context relevance |
| Cross-session recall | `GEval` (custom) | Fact planted → retrieved |

---

## Part 2: Test Structure

```
kp3/
├── tests/
│   ├── evals/                          # DeepEval-based evaluations
│   │   ├── conftest.py                 # Shared fixtures, judge model config
│   │   ├── metrics/                    # Custom GEval metrics
│   │   │   ├── __init__.py
│   │   │   ├── summary.py              # Summary quality metrics
│   │   │   ├── blocks.py               # Block update metrics
│   │   │   └── memory.py               # Memory/retrieval metrics
│   │   ├── datasets/                   # Test data
│   │   │   ├── transcripts/            # Sample conversations
│   │   │   ├── summaries/              # Expected summaries
│   │   │   └── scenarios.yaml          # Scenario definitions
│   │   ├── test_summary_quality.py     # Summary evaluation tests
│   │   ├── test_block_updates.py       # Block quality tests
│   │   ├── test_conversational.py      # Multi-turn conversation tests
│   │   └── test_retrieval.py           # KP3 search quality tests
│   └── ...existing tests...
├── src/kp3/
│   └── evals/                          # REMOVE or repurpose for data models only
└── pyproject.toml                      # Add deepeval dependency
```

---

## Part 3: Custom Metrics

### 3.1 Summary Metrics

```python
# tests/evals/metrics/summary.py

from deepeval.metrics import GEval, SummarizationMetric
from deepeval.test_case import LLMTestCaseParams

# Built-in summarization with custom assessment questions
summary_quality_metric = SummarizationMetric(
    threshold=0.7,
    model="deepseek/deepseek-chat",  # Use DeepSeek as judge
    assessment_questions=[
        "Does the summary capture all key facts mentioned in the conversation?",
        "Does the summary preserve the emotional tone of the conversation?",
        "Are temporal references (dates, sequences) accurate?",
        "Is the summary appropriate length (not too verbose, not missing details)?",
    ]
)

# Custom metric for emotional tone preservation
emotional_tone_metric = GEval(
    name="EmotionalTonePreservation",
    criteria="Evaluate whether the summary accurately reflects the emotional tone and sentiment of the original conversation.",
    evaluation_steps=[
        "Identify the emotional tone of the original conversation (frustrated, excited, anxious, neutral, etc.)",
        "Check if the summary acknowledges or reflects this emotional context",
        "Penalize summaries that mischaracterize the user's emotional state",
        "Penalize overly clinical summaries of emotional conversations",
    ],
    evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
    threshold=0.7,
    model="deepseek/deepseek-chat",
)

# Custom metric for temporal accuracy
temporal_accuracy_metric = GEval(
    name="TemporalAccuracy",
    criteria="Evaluate whether time references in the summary are accurate relative to the source conversation.",
    evaluation_steps=[
        "Identify temporal claims in the summary (dates, 'yesterday', 'next week', sequences)",
        "Verify each temporal claim against the source conversation",
        "Penalize incorrect temporal ordering or misattributed dates",
        "A summary with no temporal claims should score 1.0 if source has none",
    ],
    evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
    threshold=0.8,
    model="deepseek/deepseek-chat",
)
```

### 3.2 Block Update Metrics

```python
# tests/evals/metrics/blocks.py

from deepeval.metrics import GEval, RoleAdherenceMetric
from deepeval.test_case import LLMTestCaseParams

# Built-in role adherence for persona consistency
persona_consistency_metric = RoleAdherenceMetric(
    threshold=0.8,
    model="deepseek/deepseek-chat",
)

# Custom metric for block update necessity
update_necessity_metric = GEval(
    name="UpdateNecessity",
    criteria="Evaluate whether the block update adds meaningful new information or is unnecessary churn.",
    evaluation_steps=[
        "Compare the old block value with the new block value",
        "Identify what information was added, removed, or modified",
        "Assess whether changes add genuine new signal vs trivial rewording",
        "Score 1.0 if update clearly necessary, 0.0 if pure churn, 0.5 if marginal",
    ],
    evaluation_params=[
        LLMTestCaseParams.INPUT,           # Old block value
        LLMTestCaseParams.ACTUAL_OUTPUT,   # New block value
        LLMTestCaseParams.CONTEXT,         # Session summary that triggered update
    ],
    threshold=0.6,
    model="deepseek/deepseek-chat",
)

# Custom metric for human block factual accuracy
human_block_accuracy_metric = GEval(
    name="HumanBlockAccuracy",
    criteria="Evaluate whether facts in the human block are accurate based on conversation history.",
    evaluation_steps=[
        "Extract factual claims from the human block (name, preferences, situation)",
        "Verify each claim against the provided conversation context",
        "Penalize incorrect facts more heavily than missing facts",
        "Hallucinated facts about the user should score 0",
    ],
    evaluation_params=[
        LLMTestCaseParams.ACTUAL_OUTPUT,   # Human block content
        LLMTestCaseParams.CONTEXT,         # Conversation history as ground truth
    ],
    threshold=0.8,
    model="deepseek/deepseek-chat",
)

# Custom metric for no sycophancy in responses
no_sycophancy_metric = GEval(
    name="NoSycophancy",
    criteria="Evaluate whether the response avoids sycophantic or overly effusive language.",
    evaluation_steps=[
        "Check for sycophantic openers ('Great question!', 'That's a wonderful idea!')",
        "Check for excessive validation without substance",
        "Check for hedging that avoids giving direct answers",
        "Direct, substantive responses score 1.0; sycophantic responses score 0",
    ],
    evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
    threshold=0.8,
    model="deepseek/deepseek-chat",
)
```

### 3.3 Conversational Metrics

```python
# tests/evals/metrics/memory.py

from deepeval.metrics import KnowledgeRetentionMetric, ConversationalGEval
from deepeval.test_case import TurnParams

# Built-in knowledge retention across conversation turns
knowledge_retention_metric = KnowledgeRetentionMetric(
    threshold=0.7,
    model="deepseek/deepseek-chat",
)

# Custom metric for personalization depth
personalization_metric = ConversationalGEval(
    name="PersonalizationDepth",
    criteria="Evaluate how well the assistant personalizes responses based on accumulated user knowledge.",
    evaluation_steps=[
        "Identify user-specific information available in context (preferences, history, situation)",
        "Check if assistant responses reference or adapt to this information",
        "Generic responses that ignore available context score low",
        "Deeply personalized responses that leverage history score high",
    ],
    evaluation_params=[TurnParams.ROLE, TurnParams.CONTENT, TurnParams.RETRIEVAL_CONTEXT],
    threshold=0.7,
    model="deepseek/deepseek-chat",
)

# Custom metric for appropriate memory usage (no announcements)
memory_usage_metric = GEval(
    name="NaturalMemoryUsage",
    criteria="Evaluate whether the assistant uses memory naturally without explicitly announcing it.",
    evaluation_steps=[
        "Check for phrases like 'According to my memory...', 'I remember that...'",
        "Check for 'Based on what I know about you...' announcements",
        "Natural integration of known facts scores 1.0",
        "Explicit memory announcements score 0",
    ],
    evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
    threshold=0.9,
    model="deepseek/deepseek-chat",
)
```

---

## Part 4: Test Implementation

### 4.1 Summary Quality Tests

```python
# tests/evals/test_summary_quality.py

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from deepeval.dataset import EvaluationDataset

from .metrics.summary import (
    summary_quality_metric,
    emotional_tone_metric,
    temporal_accuracy_metric,
)


class TestSummaryQuality:
    """Evaluate session summary quality."""

    @pytest.fixture
    def sample_transcripts(self):
        """Load sample conversation transcripts."""
        return [
            {
                "transcript": """
                User: I'm feeling really stressed about the project deadline next Friday.
                Assistant: I understand. What aspects are causing the most stress?
                User: The API integration is behind schedule and I'm worried we won't make it.
                Assistant: Let's break it down - what's the current status?
                User: We have 3 endpoints done, need 5 more. Plus testing.
                """,
                "expected_facts": [
                    "Project deadline is next Friday",
                    "User is stressed",
                    "API integration is behind schedule",
                    "3 endpoints complete, 5 remaining",
                ],
                "expected_tone": "stressed, anxious",
            },
            # More samples...
        ]

    @pytest.mark.parametrize("sample_idx", [0])  # Expand as dataset grows
    def test_summary_captures_facts(self, sample_transcripts, summarizer, sample_idx):
        """Test that summaries capture key facts."""
        sample = sample_transcripts[sample_idx]

        # Generate summary using actual summarizer
        summary = summarizer.summarize(sample["transcript"])

        test_case = LLMTestCase(
            input=sample["transcript"],
            actual_output=summary,
        )

        assert_test(test_case, [summary_quality_metric])

    def test_summary_preserves_tone(self, sample_transcripts, summarizer):
        """Test that summaries preserve emotional tone."""
        sample = sample_transcripts[0]
        summary = summarizer.summarize(sample["transcript"])

        test_case = LLMTestCase(
            input=sample["transcript"],
            actual_output=summary,
        )

        assert_test(test_case, [emotional_tone_metric])


# Run with: deepeval test run tests/evals/test_summary_quality.py
```

### 4.2 Block Update Tests

```python
# tests/evals/test_block_updates.py

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from .metrics.blocks import (
    persona_consistency_metric,
    update_necessity_metric,
    human_block_accuracy_metric,
    no_sycophancy_metric,
)


class TestBlockUpdates:
    """Evaluate block update quality."""

    def test_human_block_accuracy(self):
        """Test that human block contains accurate facts."""
        test_case = LLMTestCase(
            input="",  # Not used for this metric
            actual_output="""
            Name: Mark
            Profession: Software engineer working on AI systems
            Communication preference: Async, detailed technical explanations
            Current focus: Memory systems for AI agents
            """,
            context=[
                "User: Hi, I'm Mark. I'm a software engineer working on AI systems.",
                "User: I prefer async communication and detailed technical explanations.",
                "User: I'm currently working on a memory system for AI agents.",
            ],
        )

        assert_test(test_case, [human_block_accuracy_metric])

    def test_update_is_necessary(self):
        """Test that block updates add meaningful information."""
        test_case = LLMTestCase(
            input="""
            Name: Mark
            Profession: Software engineer
            """,  # Old block value
            actual_output="""
            Name: Mark
            Profession: Software engineer working on AI memory systems
            Communication preference: Prefers async, detailed technical discussions
            Current project: Kairix - voice AI with longitudinal memory
            """,  # New block value
            context=[
                "Session summary: Mark discussed his work on Kairix, a voice AI project...",
            ],
        )

        assert_test(test_case, [update_necessity_metric])

    def test_no_sycophancy_in_responses(self):
        """Test that responses avoid sycophantic language."""
        # Good response
        good_case = LLMTestCase(
            input="What do you think about my architecture?",
            actual_output="The separation of concerns looks solid. One consideration: the embedding service might become a bottleneck under load.",
        )
        assert_test(good_case, [no_sycophancy_metric])

        # Bad response (should fail or score low)
        # bad_case = LLMTestCase(
        #     input="What do you think?",
        #     actual_output="Great question! That's a wonderful approach!",
        # )
```

### 4.3 Conversational Tests

```python
# tests/evals/test_conversational.py

import pytest
from deepeval import assert_test
from deepeval.test_case import ConversationalTestCase, Turn

from .metrics.memory import (
    knowledge_retention_metric,
    personalization_metric,
    memory_usage_metric,
)


class TestConversational:
    """Evaluate multi-turn conversation quality."""

    def test_knowledge_retention_across_turns(self):
        """Test that agent retains knowledge across conversation turns."""
        test_case = ConversationalTestCase(
            turns=[
                Turn(role="user", content="My name is Sarah and I'm a data scientist."),
                Turn(role="assistant", content="Nice to meet you, Sarah! What kind of data science work do you focus on?"),
                Turn(role="user", content="Mostly NLP and recommendation systems."),
                Turn(role="assistant", content="That's a great combination. NLP for understanding content and recommendations for surfacing it."),
                Turn(role="user", content="What's my background again?"),
                Turn(role="assistant", content="You're a data scientist specializing in NLP and recommendation systems."),
            ]
        )

        assert_test(test_case, [knowledge_retention_metric])

    def test_natural_memory_usage(self):
        """Test that memory is used naturally without announcements."""
        # Good: natural integration
        good_case = LLMTestCase(
            input="Should I use PostgreSQL or MongoDB?",
            actual_output="Given your preference for SQL and the relational nature of your user data, PostgreSQL would be a better fit.",
        )
        assert_test(good_case, [memory_usage_metric])
```

---

## Part 5: Configuration

### 5.1 conftest.py

```python
# tests/evals/conftest.py

import os
import pytest
from deepeval.models import DeepEvalBaseLLM
from openai import OpenAI


class DeepSeekModel(DeepEvalBaseLLM):
    """DeepSeek model for evaluation judging."""

    def __init__(self):
        self.client = OpenAI(
            api_key=os.environ.get("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
        )

    def load_model(self):
        return self.client

    def generate(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        return response.choices[0].message.content

    async def a_generate(self, prompt: str) -> str:
        return self.generate(prompt)

    def get_model_name(self) -> str:
        return "deepseek-chat"


@pytest.fixture(scope="session")
def judge_model():
    """Provide DeepSeek model for evaluation."""
    return DeepSeekModel()


@pytest.fixture(scope="session")
def summarizer():
    """Provide BlockManagerAgent summarizer for testing."""
    from kairix_agent.llm import BlockManagerAgent, SUMMARIZER_CONFIG
    return BlockManagerAgent(SUMMARIZER_CONFIG)
```

### 5.2 pyproject.toml additions

```toml
[project.optional-dependencies]
eval = [
    "deepeval>=1.0.0",
]

[tool.pytest.ini_options]
markers = [
    "eval: marks tests as evaluation tests (deselect with '-m \"not eval\"')",
]
```

---

## Part 6: Migration Plan

### Phase 1: Setup (Day 1)
- [ ] Add `deepeval` to kp3 dependencies
- [ ] Create `tests/evals/` directory structure
- [ ] Implement `conftest.py` with DeepSeek judge model
- [ ] Create basic custom metrics in `metrics/`

### Phase 2: Core Metrics (Day 2)
- [ ] Implement summary quality tests
- [ ] Implement block update tests
- [ ] Create 5-10 sample test cases from real conversations

### Phase 3: Conversational Tests (Day 3)
- [ ] Implement conversational test cases
- [ ] Test knowledge retention across sessions
- [ ] Test personalization depth

### Phase 4: Integration (Day 4)
- [ ] Run full eval suite against live system
- [ ] Tune metric thresholds based on results
- [ ] Document findings and adjust metrics

### Phase 5: Cleanup (Day 5)
- [ ] Remove old `kp3/src/kp3/evals/` code (or archive)
- [ ] Remove unused alembic migration (if tables not in use)
- [ ] Update CLAUDE.md with eval instructions

---

## Part 7: Running Evaluations

```bash
# Install eval dependencies
cd kp3
uv add deepeval --optional eval

# Set judge model API key
export DEEPSEEK_API_KEY="sk-..."

# Run all evals
deepeval test run tests/evals/

# Run specific test file
deepeval test run tests/evals/test_summary_quality.py

# Run with parallel execution
deepeval test run tests/evals/ -n 4

# Run via pytest (alternative)
uv run pytest tests/evals/ -m eval -v
```

---

## Part 8: Comparison with Original Plan

| Aspect | Original (Custom) | New (DeepEval) |
|--------|-------------------|----------------|
| LOC to maintain | ~1500 (models, services, runner, scorers) | ~300 (custom metrics only) |
| Judge model | Custom DeepSeekJudge class | Built-in model support |
| Test runner | Custom execute_eval_run() | pytest + deepeval CLI |
| Metrics | 15 custom scorers | 5-6 custom GEval + built-in |
| Dataset management | Custom DB tables | EvaluationDataset or YAML |
| CI integration | Manual | Built-in pytest support |
| Dashboard | Custom OpenObserve metrics | Optional Confident AI cloud |

**Key Benefits:**
1. **Less code to maintain** - DeepEval handles runner, scoring, reporting
2. **Battle-tested metrics** - SummarizationMetric, KnowledgeRetention already tuned
3. **Pytest native** - Fits existing test infrastructure
4. **GEval flexibility** - Custom criteria without custom scorer code
5. **Active development** - DeepEval is actively maintained

**Trade-offs:**
1. External dependency (but well-maintained, MIT licensed)
2. Less control over exact scoring algorithms
3. Requires API key for judge model (DeepSeek or OpenAI)

---

## Appendix: Removing Old Eval Code

If proceeding with DeepEval, the following can be removed:

```
kp3/src/kp3/evals/           # Entire directory
  ├── __init__.py
  ├── models.py              # EvalTestCase, EvalRun, EvalResult, EvalScoreDimension
  ├── services.py            # CRUD operations
  ├── runner.py              # execute_eval_run
  ├── analysis.py
  └── scorers/
      ├── __init__.py
      ├── auto.py            # 15 custom scorers
      └── rubric.py

kp3/alembic/versions/f1a2b3c4d567_add_evaluation_framework.py  # Migration
```

Alternatively, keep the DB models if you want to store eval results long-term, but use DeepEval for execution and scoring.
