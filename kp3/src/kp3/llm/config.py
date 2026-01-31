"""LLM configuration types."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class LLMConfig:
    """Configuration for OpenAI-compatible LLM API.

    Can be constructed directly with values or loaded from environment variables.
    """

    api_key: str
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"

    @classmethod
    def from_env(
        cls,
        api_key_var: str = "LLM_API_KEY",
        base_url_var: str = "LLM_BASE_URL",
        model_var: str = "LLM_MODEL",
    ) -> LLMConfig:
        """Load configuration from environment variables.

        Args:
            api_key_var: Name of env var for API key (default: LLM_API_KEY)
            base_url_var: Name of env var for base URL (default: LLM_BASE_URL)
            model_var: Name of env var for model name (default: LLM_MODEL)

        Returns:
            LLMConfig instance populated from environment.

        Raises:
            ValueError: If required API key is not set.
        """
        api_key = os.getenv(api_key_var, "")
        if not api_key:
            msg = f"{api_key_var} environment variable is required"
            raise ValueError(msg)

        return cls(
            api_key=api_key,
            base_url=os.getenv(base_url_var, cls.base_url),
            model=os.getenv(model_var, cls.model),
        )
