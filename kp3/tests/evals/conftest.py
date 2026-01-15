"""Pytest configuration for DeepEval-based evaluations.

This module configures the judge model (DeepSeek) and provides shared fixtures
for evaluation tests.

IMPORTANT: Environment variables must be set before deepeval imports happen,
so we set them at module level (top of file) rather than in pytest hooks.
"""

import os

# =============================================================================
# EARLY CONFIGURATION - Must happen before any deepeval imports
# =============================================================================

# Use DEEPSEEK_API_KEY if OPENAI_API_KEY not set
# DeepEval's GEval uses OpenAI client internally
if not os.environ.get("OPENAI_API_KEY") and os.environ.get("DEEPSEEK_API_KEY"):
    os.environ["OPENAI_API_KEY"] = os.environ["DEEPSEEK_API_KEY"]

# Set DeepEval to use DeepSeek via OpenAI-compatible API
os.environ.setdefault("OPENAI_API_BASE", "https://api.deepseek.com")
os.environ.setdefault("DEEPEVAL_JUDGE_MODEL", "deepseek/deepseek-chat")

# =============================================================================

import pytest


@pytest.fixture(scope="session")
def deepseek_api_key() -> str:
    """Get DeepSeek API key from environment."""
    key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        pytest.skip("DEEPSEEK_API_KEY or OPENAI_API_KEY required for eval tests")
    return key


@pytest.fixture(scope="session")
def judge_model_name() -> str:
    """Return the judge model name for reference."""
    return "deepseek/deepseek-chat"
