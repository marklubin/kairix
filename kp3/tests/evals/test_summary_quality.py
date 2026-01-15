"""Evaluation tests for session summary quality.

These tests evaluate the quality of summaries that would be generated
by the BlockManagerAgent summarizer after conversation sessions.

Test Philosophy:
----------------
We test summaries against three dimensions:
1. Factual coverage - Does the summary capture key facts?
2. Emotional tone - Does it preserve the conversation's emotional context?
3. Temporal accuracy - Are time references accurate?

Each test case is designed to stress a specific aspect of summary quality.
The test data represents realistic conversation scenarios.
"""

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from tests.evals.metrics.summary import (
    create_emotional_tone_metric,
    create_summary_factual_coverage_metric,
    create_temporal_accuracy_metric,
)

# =============================================================================
# Test Data: Conversation Transcripts and Summaries
# =============================================================================

# Scenario 1: Technical project discussion with deadlines
TECHNICAL_PROJECT_TRANSCRIPT = """
User: I'm working on the API integration for the Kairix project. We have 3 endpoints done but need 5 more by next Friday.
Assistant: That's a tight timeline. What's blocking the remaining endpoints?
User: The authentication middleware is giving me trouble. I've been stuck on JWT validation for two days.
Assistant: JWT validation can be tricky. Are you using RS256 or HS256?
User: RS256 with rotating keys. The key rotation is what's causing issues.
Assistant: That's a common pain point. Have you considered using a JWKS endpoint for dynamic key fetching?
User: That's a good idea. I'll try that approach tomorrow.
"""

TECHNICAL_PROJECT_GOOD_SUMMARY = """
Mark is working on API integration for Kairix with a deadline of next Friday.
3 of 8 required endpoints are complete. The main blocker is JWT validation
in the authentication middleware, specifically RS256 with rotating keys.
Plan to try JWKS endpoint approach for dynamic key fetching.
"""

TECHNICAL_PROJECT_BAD_SUMMARY_MISSING_FACTS = """
Mark is working on a project with some API endpoints.
"""

TECHNICAL_PROJECT_BAD_SUMMARY_WRONG_TEMPORAL = """
Mark finished the API integration last Friday. All 8 endpoints are complete.
The JWT validation issue was resolved yesterday using JWKS.
"""

# Scenario 2: Emotionally charged conversation
EMOTIONAL_TRANSCRIPT = """
User: I'm really frustrated with this job search. It's been three months and nothing.
Assistant: Three months of searching is exhausting. What's been the most discouraging part?
User: I keep getting to final rounds and then ghosted. It's demoralizing.
Assistant: Being ghosted after investing in final rounds is particularly painful. You're putting in real effort.
User: Exactly. I'm starting to doubt if I'm even qualified for these roles.
Assistant: Self-doubt after repeated rejection is natural, but your track record suggests otherwise. What roles have you been targeting?
User: Senior ML engineer positions at AI startups. Maybe I'm aiming too high.
Assistant: Given your background building production ML systems, senior roles seem appropriate. The market is just competitive right now.
"""

EMOTIONAL_GOOD_SUMMARY = """
Mark is frustrated and demoralized after three months of job searching for
Senior ML Engineer positions at AI startups. He's reached final rounds multiple
times but been ghosted, leading to self-doubt about his qualifications.
Despite his experience building production ML systems, the competitive market
is making the search difficult.
"""

EMOTIONAL_BAD_SUMMARY_WRONG_TONE = """
Mark is calmly exploring job opportunities in the ML space. He's had some
interviews and is optimistic about his prospects. He's considering senior
positions and feels confident about his qualifications.
"""

# Scenario 3: Neutral technical discussion (no strong emotion)
NEUTRAL_TRANSCRIPT = """
User: What's the difference between PostgreSQL's JSONB and regular JSON types?
Assistant: JSONB stores data in a decomposed binary format, while JSON stores the exact text. JSONB is faster for operations but slightly slower to insert.
User: When would I use regular JSON then?
Assistant: Regular JSON preserves whitespace and key order, which matters if you need exact text reproduction. It's also slightly faster for insert-heavy workloads.
User: Got it. I'll use JSONB since I need to query the data frequently.
"""

NEUTRAL_GOOD_SUMMARY = """
Discussion about PostgreSQL JSON types. JSONB is better for query-heavy
workloads (binary format, faster operations), while JSON preserves exact
text and is faster for inserts. Decision: use JSONB for frequent queries.
"""


# =============================================================================
# Test Classes
# =============================================================================


@pytest.mark.eval
class TestSummaryFactualCoverage:
    """Test that summaries capture key facts from conversations."""

    def test_good_summary_captures_facts(self) -> None:
        """A good summary should capture all key facts."""
        metric = create_summary_factual_coverage_metric()
        test_case = LLMTestCase(
            input=TECHNICAL_PROJECT_TRANSCRIPT,
            actual_output=TECHNICAL_PROJECT_GOOD_SUMMARY,
        )
        assert_test(test_case, [metric])

    def test_bad_summary_missing_facts_scores_low(self) -> None:
        """A summary missing key facts should score below threshold."""
        metric = create_summary_factual_coverage_metric()
        test_case = LLMTestCase(
            input=TECHNICAL_PROJECT_TRANSCRIPT,
            actual_output=TECHNICAL_PROJECT_BAD_SUMMARY_MISSING_FACTS,
        )
        # This should fail - the summary misses most facts
        metric.measure(test_case)
        assert metric.score < 0.5, (
            f"Expected low score for incomplete summary, got {metric.score}"
        )

    def test_neutral_conversation_summary(self) -> None:
        """Neutral technical discussion should have factual summary."""
        metric = create_summary_factual_coverage_metric()
        test_case = LLMTestCase(
            input=NEUTRAL_TRANSCRIPT,
            actual_output=NEUTRAL_GOOD_SUMMARY,
        )
        assert_test(test_case, [metric])


@pytest.mark.eval
class TestEmotionalTonePreservation:
    """Test that summaries preserve emotional context."""

    def test_good_summary_preserves_emotion(self) -> None:
        """A good summary should preserve the emotional tone."""
        metric = create_emotional_tone_metric()
        test_case = LLMTestCase(
            input=EMOTIONAL_TRANSCRIPT,
            actual_output=EMOTIONAL_GOOD_SUMMARY,
        )
        assert_test(test_case, [metric])

    def test_wrong_tone_scores_low(self) -> None:
        """A summary with wrong emotional tone should score below threshold."""
        metric = create_emotional_tone_metric()
        test_case = LLMTestCase(
            input=EMOTIONAL_TRANSCRIPT,
            actual_output=EMOTIONAL_BAD_SUMMARY_WRONG_TONE,
        )
        # This should fail - the summary mischaracterizes the emotional state
        metric.measure(test_case)
        assert metric.score < 0.5, (
            f"Expected low score for wrong tone, got {metric.score}"
        )

    def test_neutral_stays_neutral(self) -> None:
        """A neutral conversation should have a neutral summary."""
        metric = create_emotional_tone_metric()
        test_case = LLMTestCase(
            input=NEUTRAL_TRANSCRIPT,
            actual_output=NEUTRAL_GOOD_SUMMARY,
        )
        assert_test(test_case, [metric])


@pytest.mark.eval
class TestTemporalAccuracy:
    """Test that summaries maintain accurate time references."""

    def test_good_summary_temporal_accuracy(self) -> None:
        """A good summary should have accurate temporal references."""
        metric = create_temporal_accuracy_metric()
        test_case = LLMTestCase(
            input=TECHNICAL_PROJECT_TRANSCRIPT,
            actual_output=TECHNICAL_PROJECT_GOOD_SUMMARY,
        )
        assert_test(test_case, [metric])

    def test_wrong_temporal_scores_low(self) -> None:
        """A summary with incorrect temporal references should score low."""
        metric = create_temporal_accuracy_metric()
        test_case = LLMTestCase(
            input=TECHNICAL_PROJECT_TRANSCRIPT,
            actual_output=TECHNICAL_PROJECT_BAD_SUMMARY_WRONG_TEMPORAL,
        )
        # This should fail - the temporal references are wrong
        metric.measure(test_case)
        assert metric.score < 0.5, (
            f"Expected low score for wrong temporal refs, got {metric.score}"
        )


@pytest.mark.eval
class TestSummaryQualityIntegrated:
    """Integrated tests checking all summary quality dimensions."""

    def test_high_quality_summary_passes_all_metrics(self) -> None:
        """A high-quality summary should pass all metrics."""
        test_case = LLMTestCase(
            input=EMOTIONAL_TRANSCRIPT,
            actual_output=EMOTIONAL_GOOD_SUMMARY,
        )
        assert_test(
            test_case,
            [
                create_summary_factual_coverage_metric(),
                create_emotional_tone_metric(),
                create_temporal_accuracy_metric(),
            ],
        )
