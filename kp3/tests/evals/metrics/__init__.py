"""Custom DeepEval metrics for Kairix evaluation.

This package contains GEval-based metrics tailored to Kairix's memory architecture:

- summary: Metrics for evaluating session summary quality
- blocks: Metrics for evaluating memory block updates
- conversational: Metrics for multi-turn conversation quality

All metrics are exposed as factory functions to enable lazy initialization
of the judge model, avoiding import-time API calls.
"""

# Import _config first to set up environment before deepeval imports
from tests.evals.metrics import _config as _  # noqa: F401
from tests.evals.metrics.blocks import (
    create_human_block_accuracy_metric,
    create_no_sycophancy_metric,
    create_persona_consistency_metric,
    create_update_necessity_metric,
)
from tests.evals.metrics.conversational import (
    create_continuity_metric,
    create_memory_usage_metric,
    create_personalization_metric,
)
from tests.evals.metrics.summary import (
    create_emotional_tone_metric,
    create_summary_factual_coverage_metric,
    create_temporal_accuracy_metric,
)

__all__ = [
    "create_continuity_metric",
    "create_emotional_tone_metric",
    "create_human_block_accuracy_metric",
    "create_memory_usage_metric",
    "create_no_sycophancy_metric",
    "create_persona_consistency_metric",
    "create_personalization_metric",
    "create_summary_factual_coverage_metric",
    "create_temporal_accuracy_metric",
    "create_update_necessity_metric",
]
