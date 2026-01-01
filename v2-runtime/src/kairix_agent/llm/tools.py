"""Tool definitions for BlockManagerAgent."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from kairix_agent.config import Config

logger = logging.getLogger(__name__)

# OpenAI-format tool definition for KP3 search
SEARCH_KP3_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "search_kp3",
        "description": (
            "Search KP3 passages for relevant context. Use this when you need "
            "background information about topics, people, or events mentioned "
            "in the conversation."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query - key topics, names, or concepts to look up",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return (1-10)",
                    "default": 5,
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}


async def handle_search_kp3(query: str, limit: int = 5, agent_id: str | None = None) -> str:
    """Execute KP3 search and return formatted results.

    Args:
        query: Search query text.
        limit: Maximum number of results (1-10).
        agent_id: Optional agent ID to scope results (includes passages with NULL agent_id).

    Returns:
        Formatted search results as a string.
    """
    kp3_url = Config.KP3_URL.value
    logger.info("Searching KP3: query=%r, limit=%d, agent_id=%s", query, limit, agent_id)

    headers: dict[str, str] = {}
    if agent_id:
        headers["X-Agent-ID"] = agent_id

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{kp3_url}/passages/search",
            params={"query": query, "mode": "hybrid", "limit": min(limit, 10)},
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])

    if not results:
        logger.info("KP3 search returned no results")
        return "No relevant passages found."

    logger.info("KP3 search returned %d results", len(results))

    formatted = []
    for r in results:
        content = r.get("content", "")
        # Truncate long content
        if len(content) > 500:
            content = content[:500] + "..."
        formatted.append(f"- {content}")

    return "\n".join(formatted)
