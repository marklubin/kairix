"""Analysis utilities for evaluation results.

Functions for comparing runs, tracking progress, and generating reports.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.evals.models import EvalResult, EvalRun, EvalTestCase


async def get_run_summary(
    session: AsyncSession,
    run_id: UUID,
) -> dict[str, Any]:
    """Get a detailed summary of an eval run.
    
    Returns:
        {
            "run": {...run details...},
            "by_category": {
                "continuity": {"total": 10, "pass_rate": 0.8, ...},
                ...
            },
            "by_dimension": {
                "should_search_kp3": {"mean": 0.9, "count": 10},
                ...
            },
            "worst_cases": [...top 5 lowest scoring cases...],
        }
    """
    run = await session.get(EvalRun, run_id)
    if not run:
        return {}
    
    # Get all results for this run
    stmt = (
        select(EvalResult, EvalTestCase)
        .join(EvalTestCase)
        .where(EvalResult.run_id == run_id)
    )
    result = await session.execute(stmt)
    rows = result.all()
    
    # Group by category
    by_category: dict[str, dict[str, Any]] = {}
    for eval_result, test_case in rows:
        cat = test_case.category
        if cat not in by_category:
            by_category[cat] = {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "composite_scores": [],
            }
        
        by_category[cat]["total"] += 1
        if eval_result.error:
            by_category[cat]["failed"] += 1
        else:
            by_category[cat]["passed"] += 1
            if eval_result.composite_score is not None:
                by_category[cat]["composite_scores"].append(eval_result.composite_score)
    
    # Compute category stats
    for cat, stats in by_category.items():
        scores = stats.pop("composite_scores")
        stats["pass_rate"] = stats["passed"] / stats["total"] if stats["total"] > 0 else 0
        stats["mean_score"] = sum(scores) / len(scores) if scores else None
    
    # Aggregate by dimension
    by_dimension: dict[str, dict[str, Any]] = {}
    for eval_result, _ in rows:
        for dim, value in eval_result.auto_scores.items():
            if dim not in by_dimension:
                by_dimension[dim] = {"values": [], "category": "auto"}
            by_dimension[dim]["values"].append(float(value))
        
        if eval_result.human_scores:
            for dim, value in eval_result.human_scores.items():
                if dim not in by_dimension:
                    by_dimension[dim] = {"values": [], "category": "human"}
                by_dimension[dim]["values"].append(float(value))
    
    for dim, stats in by_dimension.items():
        values = stats.pop("values")
        stats["mean"] = sum(values) / len(values) if values else None
        stats["count"] = len(values)
    
    # Find worst cases
    worst_cases = sorted(
        [(r, c) for r, c in rows if r.composite_score is not None],
        key=lambda x: x[0].composite_score or 0,
    )[:5]
    
    return {
        "run": {
            "id": str(run.id),
            "name": run.name,
            "status": run.status,
            "model": run.model,
            "completed_cases": run.completed_cases,
            "failed_cases": run.failed_cases,
            "aggregate_scores": run.aggregate_scores,
        },
        "by_category": by_category,
        "by_dimension": by_dimension,
        "worst_cases": [
            {
                "test_case": c.name,
                "category": c.category,
                "composite_score": r.composite_score,
                "auto_scores": r.auto_scores,
                "human_scores": r.human_scores,
            }
            for r, c in worst_cases
        ],
    }


async def compare_runs_detailed(
    session: AsyncSession,
    run_ids: list[UUID],
) -> dict[str, Any]:
    """Compare multiple runs in detail.
    
    Returns per-dimension comparison and identifies regressions/improvements.
    """
    summaries = {}
    for run_id in run_ids:
        summaries[str(run_id)] = await get_run_summary(session, run_id)
    
    # Find common dimensions
    all_dimensions = set()
    for summary in summaries.values():
        all_dimensions.update(summary.get("by_dimension", {}).keys())
    
    # Build comparison
    dimension_comparison = {}
    for dim in all_dimensions:
        dimension_comparison[dim] = {}
        for run_id, summary in summaries.items():
            dim_data = summary.get("by_dimension", {}).get(dim, {})
            dimension_comparison[dim][run_id] = dim_data.get("mean")
    
    # Identify improvements/regressions (assuming runs are in chronological order)
    if len(run_ids) >= 2:
        first_id = str(run_ids[0])
        last_id = str(run_ids[-1])
        
        changes = {}
        for dim, scores in dimension_comparison.items():
            if scores.get(first_id) is not None and scores.get(last_id) is not None:
                delta = scores[last_id] - scores[first_id]
                if abs(delta) > 0.05:  # Only report meaningful changes
                    changes[dim] = {
                        "delta": delta,
                        "direction": "improved" if delta > 0 else "regressed",
                        "first": scores[first_id],
                        "last": scores[last_id],
                    }
    else:
        changes = {}
    
    return {
        "summaries": summaries,
        "dimension_comparison": dimension_comparison,
        "changes": changes,
    }


async def get_case_history(
    session: AsyncSession,
    test_case_id: UUID,
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Get historical results for a specific test case across runs.
    
    Useful for seeing if a particular case is consistently problematic.
    """
    stmt = (
        select(EvalResult, EvalRun)
        .join(EvalRun)
        .where(EvalResult.test_case_id == test_case_id)
        .order_by(EvalRun.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    rows = result.all()
    
    return [
        {
            "run_name": run.name,
            "run_created": run.created_at.isoformat(),
            "composite_score": result.composite_score,
            "auto_scores": result.auto_scores,
            "human_scores": result.human_scores,
            "latency_ms": result.latency_ms,
        }
        for result, run in rows
    ]


async def find_flaky_cases(
    session: AsyncSession,
    *,
    min_runs: int = 3,
    variance_threshold: float = 0.3,
) -> list[dict[str, Any]]:
    """Find test cases with high variance across runs.
    
    These might indicate:
    - Ambiguous test cases that need refinement
    - Model sensitivity to specific prompts
    - Non-deterministic behavior
    """
    # Get all test cases with enough results
    stmt = (
        select(
            EvalTestCase.id,
            EvalTestCase.name,
            EvalTestCase.category,
            func.count(EvalResult.id).label("run_count"),
            func.stddev(EvalResult.composite_score).label("score_variance"),
            func.avg(EvalResult.composite_score).label("score_mean"),
        )
        .join(EvalResult)
        .group_by(EvalTestCase.id)
        .having(func.count(EvalResult.id) >= min_runs)
    )
    result = await session.execute(stmt)
    rows = result.all()
    
    flaky = [
        {
            "test_case_id": str(row.id),
            "name": row.name,
            "category": row.category,
            "run_count": row.run_count,
            "score_variance": float(row.score_variance) if row.score_variance else 0,
            "score_mean": float(row.score_mean) if row.score_mean else 0,
        }
        for row in rows
        if row.score_variance and row.score_variance > variance_threshold
    ]
    
    return sorted(flaky, key=lambda x: x["score_variance"], reverse=True)


def format_comparison_report(comparison: dict[str, Any]) -> str:
    """Format a comparison dict as a readable markdown report."""
    lines = ["# Eval Run Comparison", ""]
    
    # Summaries
    lines.append("## Run Summaries")
    for run_id, summary in comparison.get("summaries", {}).items():
        run_info = summary.get("run", {})
        lines.append(f"### {run_info.get('name', run_id)}")
        lines.append(f"- Status: {run_info.get('status')}")
        lines.append(f"- Model: {run_info.get('model')}")
        lines.append(f"- Cases: {run_info.get('completed_cases')} completed, {run_info.get('failed_cases')} failed")
        lines.append("")
    
    # Changes
    changes = comparison.get("changes", {})
    if changes:
        lines.append("## Notable Changes")
        for dim, change in sorted(changes.items(), key=lambda x: abs(x[1]["delta"]), reverse=True):
            direction = "📈" if change["direction"] == "improved" else "📉"
            lines.append(
                f"- {direction} **{dim}**: {change['first']:.2f} → {change['last']:.2f} "
                f"({change['delta']:+.2f})"
            )
        lines.append("")
    
    # Dimension comparison table
    lines.append("## Dimension Comparison")
    dim_comp = comparison.get("dimension_comparison", {})
    if dim_comp:
        run_ids = list(next(iter(dim_comp.values())).keys())
        
        # Header
        lines.append("| Dimension | " + " | ".join(run_ids[:5]) + " |")
        lines.append("|" + "---|" * (len(run_ids[:5]) + 1))
        
        # Rows
        for dim, scores in sorted(dim_comp.items()):
            row = f"| {dim} |"
            for run_id in run_ids[:5]:
                score = scores.get(run_id)
                row += f" {score:.2f} |" if score is not None else " - |"
            lines.append(row)
    
    return "\n".join(lines)
