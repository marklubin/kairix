"""MCP server for passage search."""

from dotenv import load_dotenv
from fastmcp import FastMCP

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
    """
    # Clamp limit to valid range
    limit = max(1, min(50, limit))

    async with async_session() as session:
        results = await search_passages(session, query, mode=mode, limit=limit)

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
