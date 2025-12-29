"""Evaluation framework for Kairix agent testing."""

from kp3.evals.models import (
    EvalResult,
    EvalRun,
    EvalScoreDimension,
    EvalTestCase,
)
from kp3.evals.runner import execute_eval_run
from kp3.evals.services import (
    compare_runs,
    create_eval_run,
    create_test_case,
    update_result_scores,
)

__all__ = [
    # Models
    "EvalTestCase",
    "EvalRun",
    "EvalResult",
    "EvalScoreDimension",
    # Services
    "create_test_case",
    "create_eval_run",
    "execute_eval_run",
    "update_result_scores",
    "compare_runs",
]
