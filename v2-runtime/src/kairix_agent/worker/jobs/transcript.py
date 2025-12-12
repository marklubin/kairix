"""Shared transcript formatting for worker jobs."""

import logging
from typing import Any

from letta_client.types.agents import (
    AssistantMessage,
    ReasoningMessage,
    UserMessage,
)

logger = logging.getLogger(__name__)


def format_transcript(messages: list[Any]) -> str:
    """Format Letta messages into a readable transcript.

    Only includes user, assistant, and reasoning messages.
    All other message types are logged and skipped.

    Args:
        messages: List of Letta message objects.

    Returns:
        Formatted transcript string.
    """
    formatted: list[str] = []

    for msg in messages:
        if isinstance(msg, UserMessage):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            formatted.append(f"[user]: {content}")
        elif isinstance(msg, AssistantMessage):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            formatted.append(f"[assistant]: {content}")
        elif isinstance(msg, ReasoningMessage):
            formatted.append(f"[reasoning]: {msg.reasoning}")
        else:
            # Log and skip everything else (system, tool calls, tool returns, etc.)
            msg_type = type(msg).__name__
            logger.debug("Skipping message type: %s", msg_type)

    return "\n".join(formatted) if formatted else "(no messages)"