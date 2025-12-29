"""Evaluation run execution engine."""

import logging
import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.config import get_settings
from kp3.evals.models import EvalResult, EvalRun, EvalTestCase
from kp3.evals.scorers.auto import run_auto_scorers
from kp3.evals.services import (
    create_result,
    get_results_for_run,
    list_test_cases,
    update_run_status,
)

logger = logging.getLogger(__name__)


async def execute_eval_run(
    session: AsyncSession,
    run: EvalRun,
    *,
    client: anthropic.AsyncAnthropic | None = None,
) -> EvalRun:
    """Execute an eval run against all matching test cases.
    
    Flow:
    1. Get test cases (filtered by run.test_case_filter if set)
    2. For each case, invoke the agent with configured system prompt
    3. Score the output with auto-scorers
    4. Store results
    5. Update run status
    """
    settings = get_settings()
    client = client or anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    
    logger.info("Starting eval run %s: %s", run.id, run.name)
    
    await update_run_status(session, run, "running")
    
    try:
        # Get test cases
        filter_kwargs = run.test_case_filter or {}
        test_cases = await list_test_cases(session, **filter_kwargs)
        
        run.total_cases = len(test_cases)
        await session.flush()
        
        logger.info("Found %d test cases to run", len(test_cases))
        
        for i, case in enumerate(test_cases, 1):
            logger.info(
                "Running case %d/%d: %s",
                i, len(test_cases), case.name
            )
            
            try:
                result = await _run_single_case(
                    session=session,
                    run=run,
                    case=case,
                    client=client,
                )
                run.completed_cases += 1
                logger.info(
                    "Case %s completed: latency=%dms, auto_scores=%s",
                    case.name, result.latency_ms, result.auto_scores
                )
            except Exception as e:
                run.failed_cases += 1
                logger.exception("Case %s failed: %s", case.name, e)
                # Create a failed result record
                await create_result(
                    session,
                    run_id=run.id,
                    test_case_id=case.id,
                    raw_output="",
                    tool_calls=[],
                    latency_ms=0,
                    auto_scores={},
                    error=str(e),
                )
            
            await session.flush()
        
        await update_run_status(session, run, "completed")
        logger.info(
            "Eval run %s completed: %d/%d passed, %d failed",
            run.id, run.completed_cases, run.total_cases, run.failed_cases
        )
        
    except Exception as e:
        await update_run_status(session, run, "failed", error_message=str(e))
        logger.exception("Eval run %s failed: %s", run.id, e)
        raise
    
    return run


async def _run_single_case(
    session: AsyncSession,
    run: EvalRun,
    case: EvalTestCase,
    client: anthropic.AsyncAnthropic,
) -> EvalResult:
    """Run a single test case and store the result."""
    
    # Build messages
    messages = _build_messages(case)
    
    # Build system prompt with memory blocks
    system_prompt = _inject_memory_blocks(
        run.system_prompt_text,
        case.memory_state,
    )
    
    # Prepare request
    request_kwargs: dict[str, Any] = {
        "model": run.model,
        "max_tokens": run.config.get("max_tokens", 1024),
        "system": system_prompt,
        "messages": messages,
    }
    
    # Add tools if configured
    if run.config.get("tools"):
        request_kwargs["tools"] = run.config["tools"]
    
    # Execute
    start_time = time.perf_counter()
    response = await client.messages.create(**request_kwargs)
    latency_ms = int((time.perf_counter() - start_time) * 1000)
    
    # Extract output
    raw_output = ""
    tool_calls = []
    thinking = None
    
    for block in response.content:
        if block.type == "text":
            raw_output += block.text
        elif block.type == "tool_use":
            tool_calls.append({
                "id": block.id,
                "name": block.name,
                "input": block.input,
            })
        elif block.type == "thinking":
            thinking = block.thinking
    
    # Run auto scorers
    auto_scores = await run_auto_scorers(
        case=case,
        output=raw_output,
        tool_calls=tool_calls,
    )
    
    # Store result
    result = await create_result(
        session,
        run_id=run.id,
        test_case_id=case.id,
        raw_output=raw_output,
        tool_calls=tool_calls,
        latency_ms=latency_ms,
        auto_scores=auto_scores,
        thinking=thinking,
        token_count=response.usage.output_tokens if response.usage else None,
    )
    
    return result


def _build_messages(case: EvalTestCase) -> list[dict[str, Any]]:
    """Build message list from prior messages + input message."""
    messages = []
    
    # Add prior conversation history
    for msg in case.prior_messages:
        messages.append(msg)
    
    # Add the test input
    messages.append({
        "role": "user",
        "content": case.input_message,
    })
    
    return messages


def _inject_memory_blocks(
    system_prompt: str,
    memory_state: dict[str, Any],
) -> str:
    """Inject memory block values into system prompt.
    
    Looks for {block_name} placeholders and replaces with values.
    Also supports a <memory_blocks> section that gets populated.
    """
    # Simple placeholder replacement
    for block_name, value in memory_state.items():
        placeholder = f"{{{block_name}}}"
        if placeholder in system_prompt:
            system_prompt = system_prompt.replace(placeholder, str(value))
    
    # If there's a <memory_blocks> section, populate it
    if "<memory_blocks>" in system_prompt and "</memory_blocks>" in system_prompt:
        blocks_content = "\n".join(
            f"<{name}>\n{value}\n</{name}>"
            for name, value in memory_state.items()
        )
        # Replace empty memory_blocks with populated one
        import re
        system_prompt = re.sub(
            r"<memory_blocks>.*?</memory_blocks>",
            f"<memory_blocks>\n{blocks_content}\n</memory_blocks>",
            system_prompt,
            flags=re.DOTALL,
        )
    
    return system_prompt
