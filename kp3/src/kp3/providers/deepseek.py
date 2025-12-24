"""DeepSeek API client for world model extraction.

Uses the OpenAI SDK since DeepSeek provides an OpenAI-compatible API.
See: https://api-docs.deepseek.com/
"""

import json
from dataclasses import dataclass, field
from typing import Any

from openai import NOT_GIVEN, AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from kp3.config import settings


def _empty_dict() -> dict[str, Any]:
    return {}


@dataclass
class InferenceMetadata:
    """Metadata from an LLM inference call."""

    provider: str = "deepseek"
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str = ""
    response_id: str = ""
    extra: dict[str, Any] = field(default_factory=_empty_dict)


class DeepSeekError(Exception):
    """Error from DeepSeek API."""

    def __init__(
        self, message: str, status_code: int | None = None, response: object = None
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class DeepSeekClient:
    """Async client for DeepSeek chat completions.

    Uses the OpenAI SDK configured for DeepSeek's API endpoint.
    """

    DEFAULT_BASE_URL = "https://api.deepseek.com"
    DEFAULT_MODEL = "deepseek-chat"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        """Initialize the DeepSeek client.

        Args:
            api_key: DeepSeek API key (defaults to settings.DEEPSEEK_API_KEY)
            base_url: Base URL for API (defaults to settings.DEEPSEEK_BASE_URL or standard)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.base_url = (base_url or settings.DEEPSEEK_BASE_URL or self.DEFAULT_BASE_URL).rstrip(
            "/"
        )
        self.timeout = timeout

        if not self.api_key:
            raise ValueError("DeepSeek API key is required (set DEEPSEEK_API_KEY)")

        # Create OpenAI client configured for DeepSeek
        self._client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=timeout,
        )

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        model: str | None = None,
        json_mode: bool = True,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> tuple[str, InferenceMetadata]:
        """Make a chat completion request.

        Args:
            system_prompt: System message content
            user_prompt: User message content
            model: Model to use (defaults to deepseek-chat)
            json_mode: Whether to request JSON output
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            Tuple of (response_content, metadata)

        Raises:
            DeepSeekError: If the API request fails
        """
        model = model or self.DEFAULT_MODEL

        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format=(  # type: ignore[arg-type]
                    {"type": "json_object"} if json_mode else NOT_GIVEN
                ),
            )
        except Exception as e:
            raise DeepSeekError(f"DeepSeek API error: {e}") from e

        # Extract response content
        choice = response.choices[0]
        content = choice.message.content or ""

        # Build metadata
        metadata = InferenceMetadata(
            provider="deepseek",
            model=model,
            prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
            completion_tokens=response.usage.completion_tokens if response.usage else 0,
            total_tokens=response.usage.total_tokens if response.usage else 0,
            finish_reason=choice.finish_reason or "",
            response_id=response.id,
        )

        return content, metadata

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> tuple[dict[str, Any], InferenceMetadata]:
        """Make a chat completion request and parse JSON response.

        Args:
            system_prompt: System message content
            user_prompt: User message content (must contain "json" somewhere)
            model: Model to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            Tuple of (parsed_json, metadata)

        Raises:
            DeepSeekError: If the API request fails or JSON parsing fails
        """
        content, metadata = await self.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            json_mode=True,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            raise DeepSeekError(f"Failed to parse JSON response: {e}", response=content) from e

        return parsed, metadata
