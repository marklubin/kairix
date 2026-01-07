"""Conversational metrics for multi-turn interaction quality.

These metrics evaluate how well the agent maintains context, personalizes
responses, and uses memory naturally across conversation turns.

Theory:
-------
The goal of Kairix is "longitudinal understanding" - the agent should act
as a witness to the user's life, not just a stateless assistant.

Key qualities:
1. **Knowledge retention**: Remember facts across turns and sessions
2. **Personalization**: Adapt responses based on accumulated user knowledge
3. **Natural memory use**: Integrate memory without announcing it
4. **Continuity**: Reference past interactions when appropriate

The agent should feel like a peer who knows you, not a system querying a database.
"""

# Import _config first to set up environment before deepeval imports
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams

from tests.evals.metrics._config import get_judge_model


def create_memory_usage_metric() -> GEval:
    """Create the natural memory usage metric with configured judge model."""
    return GEval(
        name="NaturalMemoryUsage",
        criteria=(
            "Evaluate whether the assistant uses memory naturally without "
            "explicitly announcing that it's using memory."
        ),
        evaluation_steps=[
            "Check for explicit memory announcements: 'According to my memory...', "
            "'I remember that...', 'Based on what I know about you...'",
            "Check for phrases like 'From our previous conversations...', "
            "'As I recall...', 'My records show...'",
            "Natural integration: using known facts without calling attention to it.",
            "Example of natural: 'Given your preference for async communication...'",
            "Example of unnatural: 'I remember you said you prefer async communication...'",
            "Score 1.0 for natural integration, 0.0 for explicit announcements.",
        ],
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.9,
        model=get_judge_model(),
    )


def create_personalization_metric() -> GEval:
    """Create the personalization depth metric with configured judge model."""
    return GEval(
        name="PersonalizationDepth",
        criteria=(
            "Evaluate how well the assistant personalizes responses based on "
            "accumulated user knowledge available in context."
        ),
        evaluation_steps=[
            "Identify user-specific information in the context: preferences, "
            "history, current situation, communication style, expertise level.",
            "Check if the response references or adapts to this information.",
            "Generic responses that could apply to anyone score low.",
            "Responses that leverage specific user context score high.",
            "Example: If user prefers technical depth, response should be detailed. "
            "If user is stressed about a deadline, acknowledge the pressure.",
            "Score 1.0 for deeply personalized, 0.0 for completely generic.",
        ],
        evaluation_params=[
            LLMTestCaseParams.INPUT,  # User message
            LLMTestCaseParams.ACTUAL_OUTPUT,  # Assistant response
            LLMTestCaseParams.CONTEXT,  # User profile / memory blocks
        ],
        threshold=0.7,
        model=get_judge_model(),
    )


def create_continuity_metric() -> GEval:
    """Create the continuity score metric with configured judge model."""
    return GEval(
        name="ContinuityScore",
        criteria=(
            "Evaluate whether the assistant appropriately references or builds on "
            "past interactions when relevant."
        ),
        evaluation_steps=[
            "Identify opportunities in the conversation to reference past context: "
            "related topics discussed before, callbacks to previous decisions, "
            "follow-ups on mentioned plans.",
            "Check if the assistant makes appropriate references when opportunities exist.",
            "Verify references are accurate (not hallucinated past interactions).",
            "Don't penalize for not referencing past when it's not relevant.",
            "Forced/awkward references to past are worse than no reference.",
            "Score 1.0 for appropriate use of history, 0.5 for missed opportunities, "
            "0.0 for hallucinated references.",
        ],
        evaluation_params=[
            LLMTestCaseParams.INPUT,  # Current user message
            LLMTestCaseParams.ACTUAL_OUTPUT,  # Assistant response
            LLMTestCaseParams.CONTEXT,  # Conversation history / past sessions
        ],
        threshold=0.6,
        model=get_judge_model(),
    )
