"""OpenAI-compatible API client with tool calling support.

Works with any OpenAI-compatible API (OpenAI, DeepSeek, Groq, etc.).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any, cast

from openai import NOT_GIVEN, AsyncOpenAI

from kp3.llm.config import LLMConfig

logger = logging.getLogger(__name__)


class OpenAICompatibleClient:
    """Async client for OpenAI-compatible APIs with tool calling support."""

    def __init__(
        self,
        config: LLMConfig | None = None,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        """Initialize the client.

        Args:
            config: LLMConfig instance (preferred). If provided, other args are ignored.
            api_key: API key (used if config not provided).
            base_url: Base URL for API (used if config not provided).
            model: Model name (used if config not provided).

        If neither config nor api_key is provided, loads from environment variables.
        """
        if config is not None:
            self.api_key = config.api_key
            self.base_url = config.base_url
            self.model = config.model
        elif api_key is not None:
            self.api_key = api_key
            self.base_url = base_url or "https://api.deepseek.com"
            self.model = model or "deepseek-chat"
        else:
            # Load from environment
            env_config = LLMConfig.from_env()
            self.api_key = env_config.api_key
            self.base_url = env_config.base_url
            self.model = env_config.model

        self._client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    async def generate(  # noqa: ASYNC109 - timeout passed to OpenAI client
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        timeout: float = 120.0,
        tools: list[dict[str, Any]] | None = None,
        tool_handlers: dict[str, Callable[..., Awaitable[str]]] | None = None,
    ) -> str:
        """Generate a response, handling tool calls if needed.

        Args:
            system_prompt: System message for the model.
            user_prompt: User message to process.
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature.
            timeout: Request timeout in seconds.
            tools: List of OpenAI-format tool definitions.
            tool_handlers: Dict mapping tool names to async handler functions.

        Returns:
            The final text response after all tool calls are resolved.
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Maximum iterations to prevent infinite loops
        max_iterations = 10

        for iteration in range(max_iterations):
            logger.debug(
                "LLM iteration %d/%d, messages=%d",
                iteration + 1,
                max_iterations,
                len(messages),
            )

            response = await self._client.chat.completions.create(
                model=self.model,
                messages=cast(Any, messages),
                max_tokens=max_tokens,
                temperature=temperature,
                tools=cast(Any, tools if tools else NOT_GIVEN),
                timeout=timeout,
            )

            choice = response.choices[0]
            assistant_message = choice.message

            # If no tool calls, return the content
            if not assistant_message.tool_calls:
                return assistant_message.content or ""

            # Process tool calls
            logger.info(
                "LLM requested %d tool call(s)",
                len(assistant_message.tool_calls),
            )

            # Add assistant message with tool calls to history
            messages.append(
                {
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": cast(Any, tc).function.name,
                                "arguments": cast(Any, tc).function.arguments,
                            },
                        }
                        for tc in assistant_message.tool_calls
                    ],
                }
            )

            # Execute each tool call and add results
            for tool_call in assistant_message.tool_calls:
                func = cast(Any, tool_call).function
                tool_name: str = func.name
                tool_args: dict[str, Any] = json.loads(func.arguments)

                logger.info("Executing tool: %s(%s)", tool_name, tool_args)

                if tool_handlers and tool_name in tool_handlers:
                    try:
                        result = await tool_handlers[tool_name](**tool_args)
                    except Exception as e:
                        logger.exception("Tool %s failed", tool_name)
                        result = f"Error: {type(e).__name__}: {e}"
                else:
                    result = f"Error: Unknown tool '{tool_name}'"
                    logger.warning("No handler for tool: %s", tool_name)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )

        # If we hit max iterations, return whatever we have
        logger.warning("LLM hit max iterations (%d)", max_iterations)
        last_content = messages[-1].get("content", "")
        if isinstance(last_content, str):
            return last_content
        return ""
