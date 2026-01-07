"""Evaluation tests for multi-turn conversation quality.

These tests evaluate how well the agent maintains context, personalizes
responses, and uses memory naturally across conversation turns.

Test Philosophy:
----------------
Kairix aims for "longitudinal understanding" - the agent should feel like
a peer who knows you, not a system querying a database.

Key qualities tested:
1. Natural memory use - Integrate knowledge without announcing it
2. Personalization - Adapt based on user context
3. Continuity - Build on past interactions appropriately
"""

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from tests.evals.metrics.conversational import (
    create_continuity_metric,
    create_memory_usage_metric,
    create_personalization_metric,
)

# =============================================================================
# Test Data: Responses and Contexts
# =============================================================================

# Memory usage scenarios
RESPONSE_NATURAL_MEMORY = """
Given your preference for async communication, I'd suggest documenting this
in a shared doc rather than scheduling a meeting. You can review it on your
own time and add comments.
"""

RESPONSE_ANNOUNCED_MEMORY = """
I remember from our previous conversations that you prefer async communication.
Based on what I know about you, meetings aren't your favorite. According to
my memory, you'd rather read a doc. So I suggest documenting this instead.
"""

RESPONSE_NO_MEMORY_USED = """
There are several ways to share this information. You could schedule a meeting,
send an email, or create a document. Each has pros and cons depending on your
team's preferences.
"""

# Personalization scenarios
USER_MESSAGE_DEADLINE = "I'm stressed about the API deadline."

USER_CONTEXT_DETAILED = [
    "Human block: Mark is a software engineer working on Kairix. "
    "He's pragmatic, prefers concrete solutions over theoretical discussion. "
    "Currently under pressure with multiple deadlines. "
    "Communication style: direct, appreciates brevity.",
    "World block: Kairix API deadline is next Friday. "
    "3 of 8 endpoints complete. JWT auth is the main blocker.",
]

RESPONSE_HIGHLY_PERSONALIZED = """
The JWT auth is your bottleneck - let's focus there. For the JWKS approach:
here's a concrete implementation pattern that handles key rotation. Once that's
unblocked, the remaining 5 endpoints should be straightforward given your
current architecture.
"""

RESPONSE_GENERIC = """
Deadlines can be stressful. It's important to prioritize your tasks and break
them down into manageable chunks. Consider talking to your team about the
timeline if needed. Remember to take breaks too!
"""

# Continuity scenarios
CONVERSATION_HISTORY = [
    "Past session: Mark mentioned he was struggling with the decision between "
    "PostgreSQL and MongoDB for the new service. He was leaning toward PostgreSQL "
    "because of his SQL expertise but worried about schema flexibility.",
    "Past session: Mark decided to go with PostgreSQL after our discussion about "
    "JSONB columns for flexible data.",
]

USER_MESSAGE_DATABASE = "The new service is coming along. Just finished the data layer."

RESPONSE_GOOD_CONTINUITY = """
Nice progress! How's the PostgreSQL + JSONB approach working out for the
flexible data you were concerned about? Any schema evolution issues so far?
"""

RESPONSE_MISSED_CONTINUITY = """
That's great to hear. What database are you using for the data layer?
"""

RESPONSE_HALLUCINATED_CONTINUITY = """
Good to hear the MongoDB migration is complete! I remember you were excited
about the document model fitting your use case perfectly.
"""


# =============================================================================
# Test Classes
# =============================================================================


@pytest.mark.eval
class TestNaturalMemoryUsage:
    """Test that memory is used naturally without announcements."""

    def test_natural_memory_integration(self) -> None:
        """Response that naturally integrates memory should score high."""
        metric = create_memory_usage_metric()
        test_case = LLMTestCase(
            input="How should I share this update with the team?",
            actual_output=RESPONSE_NATURAL_MEMORY,
        )
        assert_test(test_case, [metric])

    def test_announced_memory_scores_low(self) -> None:
        """Response that announces memory usage should score low."""
        metric = create_memory_usage_metric()
        test_case = LLMTestCase(
            input="How should I share this update with the team?",
            actual_output=RESPONSE_ANNOUNCED_MEMORY,
        )
        metric.measure(test_case)
        assert metric.score < 0.5, (
            f"Expected low score for announced memory, got {metric.score}"
        )


@pytest.mark.eval
class TestPersonalizationDepth:
    """Test that responses are personalized based on user context."""

    def test_highly_personalized_response(self) -> None:
        """Response that leverages user context should score high."""
        metric = create_personalization_metric()
        test_case = LLMTestCase(
            input=USER_MESSAGE_DEADLINE,
            actual_output=RESPONSE_HIGHLY_PERSONALIZED,
            context=USER_CONTEXT_DETAILED,
        )
        assert_test(test_case, [metric])

    def test_generic_response_scores_low(self) -> None:
        """Generic response ignoring context should score low."""
        metric = create_personalization_metric()
        test_case = LLMTestCase(
            input=USER_MESSAGE_DEADLINE,
            actual_output=RESPONSE_GENERIC,
            context=USER_CONTEXT_DETAILED,
        )
        metric.measure(test_case)
        assert metric.score < 0.6, (
            f"Expected low score for generic response, got {metric.score}"
        )


@pytest.mark.eval
class TestContinuity:
    """Test that responses appropriately reference past interactions."""

    def test_good_continuity(self) -> None:
        """Response that appropriately builds on past should score high."""
        metric = create_continuity_metric()
        test_case = LLMTestCase(
            input=USER_MESSAGE_DATABASE,
            actual_output=RESPONSE_GOOD_CONTINUITY,
            context=CONVERSATION_HISTORY,
        )
        assert_test(test_case, [metric])

    def test_missed_continuity_scores_lower(self) -> None:
        """Response missing opportunity for continuity should score lower."""
        metric = create_continuity_metric()
        test_case = LLMTestCase(
            input=USER_MESSAGE_DATABASE,
            actual_output=RESPONSE_MISSED_CONTINUITY,
            context=CONVERSATION_HISTORY,
        )
        metric.measure(test_case)
        # Should be moderate - not wrong, just missed opportunity
        assert metric.score < 0.8, (
            f"Expected moderate score for missed continuity, got {metric.score}"
        )

    def test_hallucinated_continuity_scores_low(self) -> None:
        """Response with hallucinated past interactions should score low."""
        metric = create_continuity_metric()
        test_case = LLMTestCase(
            input=USER_MESSAGE_DATABASE,
            actual_output=RESPONSE_HALLUCINATED_CONTINUITY,
            context=CONVERSATION_HISTORY,
        )
        metric.measure(test_case)
        assert metric.score < 0.5, (
            f"Expected low score for hallucinated continuity, got {metric.score}"
        )


@pytest.mark.eval
class TestConversationalQualityIntegrated:
    """Integrated tests checking multiple conversational qualities."""

    def test_high_quality_response(self) -> None:
        """A high-quality response should pass multiple metrics."""
        test_case = LLMTestCase(
            input=USER_MESSAGE_DEADLINE,
            actual_output=RESPONSE_HIGHLY_PERSONALIZED,
            context=USER_CONTEXT_DETAILED,
        )
        # Check it passes personalization and natural memory use
        assert_test(
            test_case,
            [create_personalization_metric(), create_memory_usage_metric()],
        )
