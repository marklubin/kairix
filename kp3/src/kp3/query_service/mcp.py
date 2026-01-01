"""MCP server for passage search."""

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers

from kp3.db.engine import async_session
from kp3.services.search import SearchMode, search_passages

# Load .env for standalone stdio mode
load_dotenv()

mcp = FastMCP("KP3 Passages")


@mcp.tool
async def search_kp3_passages(
    query: str,
    mode: SearchMode = "hybrid",
    limit: int = 5,
) -> list[dict[str, object]]:
    """Search KP3 passages using full-text, semantic, or hybrid search.

    Args:
        query: Search query text
        mode: Search mode - "fts" (full-text), "semantic" (vector), or "hybrid" (RRF fusion)
        limit: Maximum number of results to return (1-50)

    Returns:
        List of passage results with id, content, passage_type, and relevance score

    Note:
        When accessed via SSE/HTTP, the X-Agent-ID header can be used to scope
        results to a specific agent (plus shared passages with agent_id=NULL).
    """
    # Clamp limit to valid range
    limit = max(1, min(50, limit))

    # Get agent_id from X-Agent-ID header if available (SSE mode)
    # In stdio mode, this returns an empty dict so agent_id will be None
    headers = get_http_headers()
    agent_id = headers.get("x-agent-id")  # Headers are lowercase

    async with async_session() as session:
        results = await search_passages(session, query, mode=mode, limit=limit, agent_id=agent_id)

    return [
        {
            "id": str(r.id),
            "content": r.content,
            "passage_type": r.passage_type,
            "score": r.score,
        }
        for r in results
    ]


def main() -> None:
    """Run MCP server in stdio mode (for Claude Desktop)."""
    mcp.run()


if __name__ == "__main__":
    main()
