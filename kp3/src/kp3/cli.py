"""KP3 command-line interface."""

import asyncio
import json
import logging
from pathlib import Path
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
    from rich.console import Console
    from rich.panel import Panel

    from kp3.services.search import search_passages

    async def _search() -> None:
        async with async_session() as session:
            results = await search_passages(
                session,
                query,
                mode=mode,  # type: ignore[arg-type]
                limit=limit,
            )

            if not results:
                click.echo("No results found.")
                return

            console = Console()
            console.print(f"\n[bold]{mode.upper()}[/bold] search for: [cyan]{query}[/cyan]\n")

            for i, result in enumerate(results, 1):
                score = f"[bold green][{result.score:.4f}][/]"
                ptype = f"[bold blue]{result.passage_type}[/]"
                title = f"#{i} {score} {ptype}"
                subtitle = f"[dim]{result.id}[/]"

                console.print(
                    Panel(
                        result.content,
                        title=title,
                        subtitle=subtitle,
                        title_align="left",
                        subtitle_align="left",
                        border_style="blue",
                        padding=(1, 2),
                    )
                )
                console.print()

    asyncio.run(_search())


@cli.group()
def importer() -> None:
    """Import data from external sources."""
    pass


@importer.command("kairix")
@click.argument("db_path", type=click.Path(exists=True, path_type=Path))
def import_kairix(db_path: Path) -> None:
    """Import memory shards from a Kairix SQLite backup.

    DB_PATH is the path to the SQLite database file (e.g., mark.db).
    """
    from kp3.importers.kairix_sqlite import import_memory_shards

    async def _import() -> None:
        async with async_session() as session:
            async with session.begin():
                stats = await import_memory_shards(session, db_path)

                click.echo("Import complete:")
                click.echo(f"  Total shards: {stats.total_shards}")
                click.echo(f"  Imported:     {stats.imported}")
                click.echo(f"  Duplicates:   {stats.skipped_duplicate}")
                click.echo(f"  Empty:        {stats.skipped_empty}")

    asyncio.run(_import())


if __name__ == "__main__":
    cli()
