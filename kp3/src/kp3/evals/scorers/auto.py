"""Automated scorers for evaluation results.

These run immediately after each test case executes and produce
binary or numeric scores based on observable behavior.
"""

from typing import Any, Callable

from kp3.evals.models import EvalTestCase


# Type for scorer functions
ScorerFn = Callable[[EvalTestCase, str, list[dict[str, Any]]], int | float | None]


# Registry of available auto scorers
SCORERS: dict[str, ScorerFn] = {}


def scorer(name: str):
    """Decorator to register a scorer function."""
    def decorator(fn: ScorerFn) -> ScorerFn:
        SCORERS[name] = fn
        return fn
    return decorator


async def run_auto_scorers(
    case: EvalTestCase,
    output: str,
    tool_calls: list[dict[str, Any]],
) -> dict[str, Any]:
    """Run all applicable auto scorers for a test case.
    
    Scorers to run are determined by case.eval_criteria["auto"].
    """
    scores: dict[str, Any] = {}
    
    auto_criteria = case.eval_criteria.get("auto", [])
    
    for scorer_name in auto_criteria:
        if scorer_name in SCORERS:
            score = SCORERS[scorer_name](case, output, tool_calls)
            if score is not None:
                scores[scorer_name] = score
    
    return scores


# =============================================================================
# Tool Use Scorers
# =============================================================================


@scorer("should_search_kp3")
def score_should_search_kp3(
    case: EvalTestCase,
    output: str,
    tool_calls: list[dict[str, Any]],
) -> int:
    """Did it search KP3 when it should have?
    
    Use for cases where the input references past context
    not present in memory blocks.
    """
    searched = any(
        t.get("name") == "search_kp3_passages"
        for t in tool_calls
    )
    return 1 if searched else 0


@scorer("should_not_search")
def score_should_not_search(
    case: EvalTestCase,
    output: str,
    tool_calls: list[dict[str, Any]],
) -> int:
    """Did it avoid searching when unnecessary?
    
    Use for cases where all context is in memory blocks.
    """
    searched = any(
        t.get("name") in ("search_kp3_passages", "web_search")
        for t in tool_calls
    )
    return 1 if not searched else 0


@scorer("should_web_search")
def score_should_web_search(
    case: EvalTestCase,
    output: str,
    tool_calls: list[dict[str, Any]],
) -> int:
    """Did it search the web when it should have?
    
    Use for cases requiring external/current information.
    """
    searched = any(
        t.get("name") == "web_search"
        for t in tool_calls
    )
    return 1 if searched else 0


@scorer("used_any_tool")
def score_used_any_tool(
    case: EvalTestCase,
    output: str,
    tool_calls: list[dict[str, Any]],
) -> int:
    """Did it use any tool at all?"""
    return 1 if tool_calls else 0


@scorer("no_tools_used")
def score_no_tools_used(
    case: EvalTestCase,
    output: str,
    tool_calls: list[dict[str, Any]],
) -> int:
    """Did it avoid using tools?"""
    return 1 if not tool_calls else 0


# =============================================================================
# Output Content Scorers
# =============================================================================


@scorer("output_not_empty")
def score_output_not_empty(
    case: EvalTestCase,
    output: str,
    tool_calls: list[dict[str, Any]],
) -> int:
    """Did it produce non-empty output?"""
    return 1 if output.strip() else 0


@scorer("output_concise")
def score_output_concise(
    case: EvalTestCase,
    output: str,
    tool_calls: list[dict[str, Any]],
) -> int:
    """Is the output reasonably concise? (<500 chars)"""
    return 1 if len(output) < 500 else 0


@scorer("output_not_verbose")
def score_output_not_verbose(
    case: EvalTestCase,
    output: str,
    tool_calls: list[dict[str, Any]],
) -> int:
    """Is the output not excessively verbose? (<2000 chars)"""
    return 1 if len(output) < 2000 else 0


@scorer("no_memory_announcement")
def score_no_memory_announcement(
    case: EvalTestCase,
    output: str,
    tool_calls: list[dict[str, Any]],
) -> int:
    """Did it avoid announcing memory usage?
    
    Penalizes phrases like "According to my memory...",
    "I remember that...", "Based on what I know about you..."
    """
    announcement_phrases = [
        "according to my memory",
        "i remember that",
        "based on what i know about you",
        "from our previous",
        "as i recall",
        "my records show",
        "based on my knowledge of you",
    ]
    output_lower = output.lower()
    for phrase in announcement_phrases:
        if phrase in output_lower:
            return 0
    return 1


@scorer("uses_memory_content")
def score_uses_memory_content(
    case: EvalTestCase,
    output: str,
    tool_calls: list[dict[str, Any]],
) -> int | None:
    """Did the output incorporate info from memory blocks?
    
    Checks if key terms from memory_state appear in output.
    Returns None if no memory_check_terms in eval_criteria.
    """
    check_terms = case.eval_criteria.get("memory_check_terms", [])
    if not check_terms:
        return None
    
    output_lower = output.lower()
    matches = sum(1 for term in check_terms if term.lower() in output_lower)
    
    # Score based on percentage of terms found
    return 1 if matches >= len(check_terms) * 0.5 else 0


# =============================================================================
# Tone / Register Scorers
# =============================================================================


@scorer("no_sycophancy")
def score_no_sycophancy(
    case: EvalTestCase,
    output: str,
    tool_calls: list[dict[str, Any]],
) -> int:
    """Did it avoid sycophantic openers?
    
    Penalizes "Great question!", "That's a wonderful...", etc.
    """
    sycophantic_phrases = [
        "great question",
        "excellent question",
        "wonderful question",
        "that's a great",
        "that's an excellent",
        "what a great",
        "i love that",
        "absolutely!",
    ]
    output_lower = output.lower()
    for phrase in sycophantic_phrases:
        if output_lower.startswith(phrase) or f"\n{phrase}" in output_lower:
            return 0
    return 1


@scorer("no_excessive_caveats")
def score_no_excessive_caveats(
    case: EvalTestCase,
    output: str,
    tool_calls: list[dict[str, Any]],
) -> int:
    """Did it avoid excessive hedging/caveating?"""
    caveat_phrases = [
        "i should note that",
        "it's important to remember",
        "keep in mind that",
        "i want to be clear",
        "i should mention",
        "just to be safe",
    ]
    output_lower = output.lower()
    caveat_count = sum(1 for phrase in caveat_phrases if phrase in output_lower)
    return 1 if caveat_count <= 1 else 0


# =============================================================================
# Gold Response Comparison
# =============================================================================


@scorer("matches_gold_response")
def score_matches_gold_response(
    case: EvalTestCase,
    output: str,
    tool_calls: list[dict[str, Any]],
) -> int | None:
    """Does the output semantically match the gold response?
    
    Simple word overlap for now - could be upgraded to embedding similarity.
    Returns None if no gold response defined.
    """
    if not case.gold_response:
        return None
    
    # Simple word overlap score
    output_words = set(output.lower().split())
    gold_words = set(case.gold_response.lower().split())
    
    if not gold_words:
        return None
    
    overlap = len(output_words & gold_words) / len(gold_words)
    return 1 if overlap > 0.5 else 0
