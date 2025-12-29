"""Evaluation services for managing test cases, runs, and results."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.evals.models import (
    EvalResult,
    EvalRun,
    EvalScoreDimension,
    EvalTestCase,
)


# =============================================================================
# Test Case Management
# =============================================================================


async def create_test_case(
    session: AsyncSession,
    *,
    name: str,
    category: str,
    memory_state: dict[str, Any],
    input_message: str,
    expected_behavior: str,
    eval_criteria: dict[str, Any],
    prior_messages: list[dict[str, Any]] | None = None,
    gold_response: str | None = None,
    difficulty: str | None = None,
    tags: list[str] | None = None,
    notes: str | None = None,
) -> EvalTestCase:
    """Create a new test case."""
    case = EvalTestCase(
        name=name,
        category=category,
        memory_state=memory_state,
        prior_messages=prior_messages or [],
        input_message=input_message,
        expected_behavior=expected_behavior,
        eval_criteria=eval_criteria,
        gold_response=gold_response,
        difficulty=difficulty,
        tags=tags or [],
        notes=notes,
    )
    session.add(case)
    await session.flush()
    return case


async def get_test_case(session: AsyncSession, case_id: UUID) -> EvalTestCase | None:
    """Get a test case by ID."""
    return await session.get(EvalTestCase, case_id)


async def get_test_case_by_name(session: AsyncSession, name: str) -> EvalTestCase | None:
    """Get a test case by name."""
    stmt = select(EvalTestCase).where(EvalTestCase.name == name)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_test_cases(
    session: AsyncSession,
    *,
    category: str | None = None,
    tags: list[str] | None = None,
    difficulty: str | None = None,
    limit: int = 100,
) -> list[EvalTestCase]:
    """List test cases with optional filters."""
    stmt = select(EvalTestCase).order_by(EvalTestCase.name).limit(limit)
    
    if category:
        stmt = stmt.where(EvalTestCase.category == category)
    if difficulty:
        stmt = stmt.where(EvalTestCase.difficulty == difficulty)
    if tags:
        stmt = stmt.where(EvalTestCase.tags.contains(tags))
    
    result = await session.execute(stmt)
    return list(result.scalars().all())


# =============================================================================
# Eval Run Management
# =============================================================================


async def create_eval_run(
    session: AsyncSession,
    *,
    name: str,
    system_prompt_text: str,
    model: str,
    config: dict[str, Any] | None = None,
    system_prompt_ref: str | None = None,
    test_case_filter: dict[str, Any] | None = None,
    notes: str | None = None,
) -> EvalRun:
    """Create a new eval run."""
    run = EvalRun(
        name=name,
        system_prompt_text=system_prompt_text,
        system_prompt_ref=system_prompt_ref,
        model=model,
        config=config or {},
        test_case_filter=test_case_filter,
        status="pending",
        notes=notes,
    )
    session.add(run)
    await session.flush()
    return run


async def get_eval_run(session: AsyncSession, run_id: UUID) -> EvalRun | None:
    """Get an eval run by ID."""
    return await session.get(EvalRun, run_id)


async def list_eval_runs(
    session: AsyncSession,
    *,
    status: str | None = None,
    limit: int = 50,
) -> list[EvalRun]:
    """List eval runs with optional status filter."""
    stmt = select(EvalRun).order_by(EvalRun.created_at.desc()).limit(limit)
    
    if status:
        stmt = stmt.where(EvalRun.status == status)
    
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_run_status(
    session: AsyncSession,
    run: EvalRun,
    status: str,
    *,
    error_message: str | None = None,
) -> None:
    """Update run status and timing."""
    run.status = status
    
    if status == "running" and run.started_at is None:
        run.started_at = datetime.now(timezone.utc)
    elif status in ("completed", "failed"):
        run.completed_at = datetime.now(timezone.utc)
    
    if error_message:
        run.error_message = error_message
    
    await session.flush()


# =============================================================================
# Result Management
# =============================================================================


async def create_result(
    session: AsyncSession,
    *,
    run_id: UUID,
    test_case_id: UUID,
    raw_output: str,
    tool_calls: list[dict[str, Any]],
    latency_ms: int,
    auto_scores: dict[str, Any],
    thinking: str | None = None,
    token_count: int | None = None,
    error: str | None = None,
) -> EvalResult:
    """Create a new eval result."""
    result = EvalResult(
        run_id=run_id,
        test_case_id=test_case_id,
        raw_output=raw_output,
        tool_calls=tool_calls,
        latency_ms=latency_ms,
        auto_scores=auto_scores,
        thinking=thinking,
        token_count=token_count,
        error=error,
    )
    session.add(result)
    await session.flush()
    return result


async def update_result_scores(
    session: AsyncSession,
    result_id: UUID,
    *,
    human_scores: dict[str, Any],
    human_notes: str | None = None,
) -> EvalResult | None:
    """Update a result with human scores."""
    result = await session.get(EvalResult, result_id)
    if not result:
        return None
    
    result.human_scores = human_scores
    result.human_notes = human_notes
    result.reviewed_at = datetime.now(timezone.utc)
    
    # Recompute composite score
    result.composite_score = await _compute_composite_score(session, result)
    
    await session.flush()
    return result


async def get_results_for_run(
    session: AsyncSession,
    run_id: UUID,
    *,
    needs_review: bool = False,
) -> list[EvalResult]:
    """Get all results for a run."""
    stmt = select(EvalResult).where(EvalResult.run_id == run_id)
    
    if needs_review:
        stmt = stmt.where(EvalResult.human_scores.is_(None))
    
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def _compute_composite_score(
    session: AsyncSession,
    result: EvalResult,
) -> float | None:
    """Compute weighted composite score from auto + human scores."""
    if not result.human_scores:
        return None
    
    # Get all score dimensions
    stmt = select(EvalScoreDimension)
    dims_result = await session.execute(stmt)
    dimensions = {d.name: d for d in dims_result.scalars().all()}
    
    total_weight = 0.0
    weighted_sum = 0.0
    
    # Process auto scores
    for name, value in result.auto_scores.items():
        if name in dimensions:
            dim = dimensions[name]
            weighted_sum += float(value) * dim.weight
            total_weight += dim.weight
    
    # Process human scores
    for name, value in result.human_scores.items():
        if name in dimensions:
            dim = dimensions[name]
            # Normalize to 0-1 range if needed
            if dim.score_type == "1-5":
                value = (value - 1) / 4
            elif dim.score_type == "1-10":
                value = (value - 1) / 9
            weighted_sum += float(value) * dim.weight
            total_weight += dim.weight
    
    if total_weight == 0:
        return None
    
    return weighted_sum / total_weight


# =============================================================================
# Analysis
# =============================================================================


async def compare_runs(
    session: AsyncSession,
    run_names: list[str],
    *,
    dimension: str | None = None,
) -> dict[str, Any]:
    """Compare aggregate scores across runs.
    
    Returns:
        {
            "runs": [
                {"name": "v1", "aggregate_scores": {...}, "completed": 50},
                {"name": "v2", "aggregate_scores": {...}, "completed": 50},
            ],
            "dimension_comparison": {...}  # If dimension specified
        }
    """
    stmt = select(EvalRun).where(EvalRun.name.in_(run_names))
    result = await session.execute(stmt)
    runs = list(result.scalars().all())
    
    comparison = {
        "runs": [
            {
                "name": r.name,
                "aggregate_scores": r.aggregate_scores,
                "completed_cases": r.completed_cases,
                "status": r.status,
            }
            for r in runs
        ]
    }
    
    if dimension:
        # Get per-run scores for this dimension
        dimension_scores = {}
        for run in runs:
            if run.aggregate_scores and dimension in run.aggregate_scores:
                dimension_scores[run.name] = run.aggregate_scores[dimension]
        comparison["dimension_comparison"] = {
            "dimension": dimension,
            "scores": dimension_scores,
        }
    
    return comparison


async def compute_aggregate_scores(
    session: AsyncSession,
    run_id: UUID,
) -> dict[str, Any]:
    """Compute aggregate scores for a run from its results."""
    results = await get_results_for_run(session, run_id)
    
    if not results:
        return {}
    
    # Collect all scores across results
    auto_totals: dict[str, list[float]] = {}
    human_totals: dict[str, list[float]] = {}
    composite_scores: list[float] = []
    
    for result in results:
        for name, value in result.auto_scores.items():
            if name not in auto_totals:
                auto_totals[name] = []
            auto_totals[name].append(float(value))
        
        if result.human_scores:
            for name, value in result.human_scores.items():
                if name not in human_totals:
                    human_totals[name] = []
                human_totals[name].append(float(value))
        
        if result.composite_score is not None:
            composite_scores.append(result.composite_score)
    
    # Compute averages
    aggregates: dict[str, Any] = {
        "auto": {name: sum(vals) / len(vals) for name, vals in auto_totals.items()},
        "human": {name: sum(vals) / len(vals) for name, vals in human_totals.items()},
        "total_results": len(results),
        "reviewed_count": sum(1 for r in results if r.human_scores),
    }
    
    if composite_scores:
        aggregates["composite_mean"] = sum(composite_scores) / len(composite_scores)
    
    # Update the run
    run = await get_eval_run(session, run_id)
    if run:
        run.aggregate_scores = aggregates
        await session.flush()
    
    return aggregates


# =============================================================================
# Score Dimensions
# =============================================================================


async def create_score_dimension(
    session: AsyncSession,
    *,
    name: str,
    category: str,
    description: str,
    score_type: str = "binary",
    weight: float = 1.0,
    rubric: dict[str, Any] | None = None,
) -> EvalScoreDimension:
    """Create a new score dimension."""
    dim = EvalScoreDimension(
        name=name,
        category=category,
        description=description,
        score_type=score_type,
        weight=weight,
        rubric=rubric,
    )
    session.add(dim)
    await session.flush()
    return dim


async def list_score_dimensions(
    session: AsyncSession,
    category: str | None = None,
) -> list[EvalScoreDimension]:
    """List all score dimensions."""
    stmt = select(EvalScoreDimension).order_by(EvalScoreDimension.name)
    if category:
        stmt = stmt.where(EvalScoreDimension.category == category)
    result = await session.execute(stmt)
    return list(result.scalars().all())
