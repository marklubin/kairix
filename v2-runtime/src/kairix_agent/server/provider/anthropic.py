"""Anthropic streaming provider implementation."""

from collections.abc import AsyncIterator

from anthropic import AsyncAnthropic
from anthropic.types import MessageParam

from kairix_agent.server.provider.base import LLMProvider


class AnthropicProvider(LLMProvider):
    """Anthropic Claude streaming provider."""

    def __init__(self) -> None:
        self.client = AsyncAnthropic()  # Uses ANTHROPIC_API_KEY env var
        self.max_tokens = 1024
        self.model = "claude-sonnet-4-5-20250929"

    async def stream_response(self, user_message: str) -> AsyncIterator[str]:
        anthro_message: MessageParam = MessageParam(role="user", content=user_message)
        async with self.client.messages.stream(
            max_tokens=self.max_tokens,
            messages=[anthro_message],
            model=self.model,
        ) as stream:
            async for message in stream.text_stream:
                yield message
