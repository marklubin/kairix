"""KP3 command-line interface."""

import asyncio
import json
import logging
from typing import Any

import click
from dotenv import load_dotenv
from sqlalchemy import text

# Load .env file before importing config
load_dotenv()


def setup_logging(verbose: bool) -> None:
    """Configure logging based on verbosity."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


from kp3.db.engine import async_session
from kp3.processors.base import Processor
from kp3.processors.embedding import EmbeddingProcessor
from kp3.processors.llm_prompt import LLMPromptProcessor
from kp3.services.passages import create_passage
from kp3.services.runs import create_run, execute_run, list_runs


def get_processor(processor_type: str) -> Processor[Any]:
    """Get processor instance by type."""
    processors: dict[str, Processor[Any]] = {
        "embedding": EmbeddingProcessor(),
        "llm_prompt": LLMPromptProcessor(),
    }
    if processor_type not in processors:
        raise click.ClickException(f"Unknown processor type: {processor_type}")
    return processors[processor_type]


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """KP3 - Knowledge Processing Pipeline."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    setup_logging(verbose)


@cli.group()
def run() -> None:
    """Manage processing runs."""
    pass


@run.command("create")
@click.argument("input_sql")
@click.option("--processor", "-p", required=True, help="Processor type (embedding, llm_prompt)")
@click.option("--config", "-c", default="{}", help="Processor config as JSON")
def run_create(input_sql: str, processor: str, config: str) -> None:
    """Create and execute a processing run.

    INPUT_SQL is the SQL query that returns groups to process.
    Must return columns: passage_ids (UUID[]), group_key (TEXT), group_metadata (JSONB).
    """
    try:
        config_dict = json.loads(config)
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid JSON config: {e}") from e

    async def _run() -> None:
        proc = get_processor(processor)
        typed_config = proc.parse_config(config_dict)

        async with async_session() as session:
            async with session.begin():
                processing_run = await create_run(
                    session,
                    input_sql=input_sql,
                    processor_type=processor,
                    processor_config=config_dict,
                )
                click.echo(f"Created run: {processing_run.id}")

                processing_run = await execute_run(session, processing_run, proc)

                click.echo(f"Status: {processing_run.status}")
                click.echo(
                    f"Groups: {processing_run.processed_groups}/{processing_run.total_groups}"
                )
                click.echo(f"Output: {processing_run.output_count} passages created")

                if processing_run.error_message:
                    click.echo(f"Error: {processing_run.error_message}", err=True)

    asyncio.run(_run())


@run.command("ls")
@click.option("--status", "-s", help="Filter by status (pending, running, completed, failed)")
@click.option("--limit", "-n", default=20, help="Max runs to show")
def run_ls(status: str | None, limit: int) -> None:
    """List processing runs."""

    async def _list() -> None:
        async with async_session() as session:
            runs = await list_runs(session, status=status, limit=limit)

            if not runs:
                click.echo("No runs found.")
                return

            for r in runs:
                status_str = r.status.upper()
                groups = f"{r.processed_groups or 0}/{r.total_groups or 0}"
                click.echo(
                    f"{r.id}  {status_str:<10} {r.processor_type:<12} "
                    f"groups={groups}  output={r.output_count or 0}  "
                    f"{r.created_at:%Y-%m-%d %H:%M}"
                )

    asyncio.run(_list())


@cli.command("sql")
@click.argument("query")
def sql_cmd(query: str) -> None:
    """Execute raw SQL and print results (for debugging)."""

    async def _sql() -> None:
        async with async_session() as session:
            result = await session.execute(text(query))
            rows = result.fetchall()

            if not rows:
                click.echo("No results.")
                return

            for row in rows:
                click.echo(row)

    asyncio.run(_sql())


@cli.group()
def passage() -> None:
    """Manage passages."""
    pass


@passage.command("create")
@click.argument("content")
@click.option("--type", "-t", "passage_type", default="manual_input", help="Passage type")
def passage_create(content: str, passage_type: str) -> None:
    """Create a new passage from command line input."""

    async def _create() -> None:
        async with async_session() as session:
            async with session.begin():
                p = await create_passage(
                    session,
                    content=content,
                    passage_type=passage_type,
                )
                click.echo(f"Created passage: {p.id}")

    asyncio.run(_create())


@passage.command("ls")
@click.option("--type", "-t", "passage_type", help="Filter by passage type")
@click.option("--limit", "-n", default=20, help="Max passages to show")
def passage_ls(passage_type: str | None, limit: int) -> None:
    """List passages."""
    from kp3.services.passages import list_passages

    async def _list() -> None:
        async with async_session() as session:
            passages = await list_passages(session, passage_type=passage_type, limit=limit)

            if not passages:
                click.echo("No passages found.")
                return

            for p in passages:
                content_preview = p.content[:60].replace("\n", " ")
                if len(p.content) > 60:
                    content_preview += "..."
                click.echo(f"{p.id}  {p.passage_type:<15} {content_preview}")

    asyncio.run(_list())


@passage.command("search")
@click.argument("query")
@click.option("--mode", "-m", default="hybrid", type=click.Choice(["fts", "semantic", "hybrid"]))
@click.option("--limit", "-n", default=5, help="Max results to show")
def passage_search(query: str, mode: str, limit: int) -> None:
    """Search passages using FTS, semantic, or hybrid search."""
    from kp3.processors.embedding import generate_embedding

    async def _search() -> None:
        async with async_session() as session:
            if mode == "fts":
                # Full-text search only
                sql = text("""
                    SELECT id, content, passage_type,
                           ts_rank(content_tsv, websearch_to_tsquery('english', :query)) as score
                    FROM passages
                    WHERE content_tsv @@ websearch_to_tsquery('english', :query)
                    ORDER BY score DESC
                    LIMIT :limit
                """)
                result = await session.execute(sql, {"query": query, "limit": limit})

            elif mode == "semantic":
                # Semantic search only
                query_embedding = await generate_embedding(query)
                sql = text("""
                    SELECT id, content, passage_type,
                           1 - (embedding_qwen3 <=> cast(:embedding as vector)) as score
                    FROM passages
                    WHERE embedding_qwen3 IS NOT NULL
                    ORDER BY embedding_qwen3 <=> cast(:embedding as vector)
                    LIMIT :limit
                """)
                result = await session.execute(
                    sql, {"embedding": str(query_embedding), "limit": limit}
                )

            else:  # hybrid
                # Combine FTS and semantic with RRF
                query_embedding = await generate_embedding(query)
                sql = text("""
                    WITH fts AS (
                        SELECT id, row_number() OVER (ORDER BY ts_rank(content_tsv, websearch_to_tsquery('english', :query)) DESC) as rank
                        FROM passages
                        WHERE content_tsv @@ websearch_to_tsquery('english', :query)
                    ),
                    semantic AS (
                        SELECT id, row_number() OVER (ORDER BY embedding_qwen3 <=> cast(:embedding as vector)) as rank
                        FROM passages
                        WHERE embedding_qwen3 IS NOT NULL
                    )
                    SELECT p.id, p.content, p.passage_type,
                           COALESCE(1.0 / (60 + fts.rank), 0) + COALESCE(1.0 / (60 + semantic.rank), 0) as score
                    FROM passages p
                    LEFT JOIN fts ON p.id = fts.id
                    LEFT JOIN semantic ON p.id = semantic.id
                    WHERE fts.id IS NOT NULL OR semantic.id IS NOT NULL
                    ORDER BY score DESC
                    LIMIT :limit
                """)
                result = await session.execute(
                    sql, {"query": query, "embedding": str(query_embedding), "limit": limit}
                )

            rows = result.fetchall()
            if not rows:
                click.echo("No results found.")
                return

            click.echo(f"\n{mode.upper()} search for: {query}\n")
            for row in rows:
                content_preview = row.content[:80].replace("\n", " ")
                if len(row.content) > 80:
                    content_preview += "..."
                click.echo(f"[{row.score:.4f}] {row.passage_type}")
                click.echo(f"  {content_preview}")
                click.echo()

    asyncio.run(_search())


if __name__ == "__main__":
    cli()
