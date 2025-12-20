"""Main entry point for KP3 Query Service."""

import logging
import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

from kp3.query_service.mcp import mcp
from kp3.query_service.router import router

# Load .env before anything else
load_dotenv()

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="KP3 Query Service",
    description="REST and MCP API for searching KP3 passages",
    version="0.1.0",
)

# Include REST routes
app.include_router(router)

# Mount MCP server at /mcp (SSE transport for HTTP clients)
app.mount("/mcp", mcp.http_app(transport="sse"))


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


def main() -> None:
    """Run the query service."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    host = os.getenv("KP3_QUERY_HOST", "0.0.0.0")  # noqa: S104
    port = int(os.getenv("KP3_QUERY_PORT", "8080"))

    logger.info(f"Starting KP3 Query Service on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
