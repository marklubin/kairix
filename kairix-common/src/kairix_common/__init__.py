"""Kairix Common - shared types and utilities."""

from kairix_common.kp3_client import (
    PassageCreate,
    PassageCreateResponse,
    PassageResult,
    PromptResponse,
    SearchMode,
    SearchResponse,
)
from kairix_common.llm import LLMConfig, OpenAICompatibleClient

__all__ = [
    # KP3 client types
    "PassageCreate",
    "PassageCreateResponse",
    "PassageResult",
    "PromptResponse",
    "SearchMode",
    "SearchResponse",
    # LLM
    "LLMConfig",
    "OpenAICompatibleClient",
]
