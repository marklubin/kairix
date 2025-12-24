"""KP3 command-line interface."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from sqlalchemy import select, text

# Load .env file before importing config
load_dotenv()

from kp3.db.engine import async_session  # noqa: E402
from kp3.db.models import Passage  # noqa: E402
from kp3.processors.base import Processor, ProcessorGroup  # noqa: E402
from kp3.processors.embedding import EmbeddingProcessor  # noqa: E402
from kp3.processors.llm_prompt import LLMPromptProcessor  # noqa: E402
from kp3.processors.world_model import WorldModelConfig, WorldModelProcessor  # noqa: E402
from kp3.scripts.backfill_world_models import backfill_world_models  # noqa: E402
from kp3.scripts.seed_prompts import seed_all_prompts  # noqa: E402
from kp3.services.passages import create_passage  # noqa: E402
from kp3.services.refs import (  # noqa: E402
    create_ref_hook,
    get_ref_history,
    get_ref_passage,
    list_ref_hooks,
    list_refs,
)
from kp3.services.runs import create_run, execute_run, list_runs  # noqa: E402


def setup_logging(verbose: bool) -> None:
    """Configure logging based on verbosity."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def get_processor(processor_type: str, session: Any = None) -> Processor[Any]:  # noqa: ANN401
    """Get processor instance by type."""
    if processor_type == "world_model":
        if session is None:
            raise click.ClickException("world_model processor requires a session")
        return WorldModelProcessor(session)

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
        _ = proc.parse_config(config_dict)  # Validate config

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


# =============================================================================
# REFS COMMANDS
# =============================================================================


@cli.group()
def refs() -> None:
    """Manage passage refs (mutable pointers to passages)."""
    pass


@refs.command("list")
@click.option("--prefix", "-p", help="Ref prefix to filter by")
def refs_list(prefix: str | None) -> None:
    """List all refs."""

    async def _list() -> None:
        async with async_session() as session:
            ref_list = await list_refs(session, prefix=prefix)

            if not ref_list:
                click.echo("No refs found.")
                return

            for ref in ref_list:
                click.echo(
                    f"{ref['name']:<30} -> {ref['passage_id']}  "
                    f"({ref['updated_at']:%Y-%m-%d %H:%M})"
                )

    asyncio.run(_list())


@refs.command("get")
@click.argument("name")
def refs_get(name: str) -> None:
    """Get details of a specific ref."""

    async def _get() -> None:
        async with async_session() as session:
            passage = await get_ref_passage(session, name)

            if not passage:
                click.echo(f"Ref '{name}' not found.")
                return

            console = Console()
            console.print(f"\n[bold]Ref:[/] {name}")
            console.print(f"[bold]Passage ID:[/] {passage.id}")
            console.print(f"[bold]Type:[/] {passage.passage_type}")
            console.print(f"[bold]Created:[/] {passage.created_at}")
            console.print()
            console.print(Panel(passage.content, title="Content", border_style="blue"))

    asyncio.run(_get())


@refs.command("history")
@click.argument("name")
@click.option("--limit", "-n", default=10, help="Max history entries to show")
def refs_history(name: str, limit: int) -> None:
    """Show history of changes for a ref."""

    async def _history() -> None:
        async with async_session() as session:
            history = await get_ref_history(session, name, limit=limit)

            if not history:
                click.echo(f"No history found for ref '{name}'.")
                return

            click.echo(f"\nHistory for ref: {name}\n")
            for entry in history:
                prev = entry["previous_passage_id"] or "(none)"
                click.echo(
                    f"  {entry['changed_at']:%Y-%m-%d %H:%M:%S}  {prev} -> {entry['passage_id']}"
                )

    asyncio.run(_history())


@refs.command("hooks")
@click.option("--ref", "-r", "ref_name", help="Filter by ref name")
def refs_hooks(ref_name: str | None) -> None:
    """List configured hooks for refs."""

    async def _hooks() -> None:
        async with async_session() as session:
            hooks = await list_ref_hooks(session, ref_name=ref_name)

            if not hooks:
                click.echo("No hooks found.")
                return

            for hook in hooks:
                status = "[green]enabled[/]" if hook.enabled else "[red]disabled[/]"
                Console().print(
                    f"{hook.ref_name:<30} {hook.action_type:<25} {status}  "
                    f"config={json.dumps(hook.config)}"
                )

    asyncio.run(_hooks())


@refs.command("add-hook")
@click.argument("ref_name")
@click.argument("action_type")
@click.argument("config_json")
def refs_add_hook(ref_name: str, action_type: str, config_json: str) -> None:
    """Add a hook to a ref.

    ACTION_TYPE should be e.g., "letta_agent_block_update".
    CONFIG_JSON should be a JSON object with action-specific config.
    """
    try:
        config = json.loads(config_json)
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid JSON: {e}") from e

    async def _add() -> None:
        async with async_session() as session:
            async with session.begin():
                hook = await create_ref_hook(
                    session,
                    ref_name=ref_name,
                    action_type=action_type,
                    config=config,
                )
                click.echo(f"Created hook: {hook.id}")

    asyncio.run(_add())


# =============================================================================
# WORLD MODEL COMMANDS
# =============================================================================


@cli.group("world-model")
def world_model() -> None:
    """World model extraction and management."""
    pass


@world_model.command("backfill")
@click.option("--branch", "-b", default="HEAD", help="Ref branch name (e.g., HEAD, experiment-v2)")
@click.option("--model", "-m", default="deepseek-chat", help="LLM model to use")
@click.option("--limit", "-n", type=int, help="Max passages to process")
@click.option("--dry-run", is_flag=True, help="Don't update refs")
@click.option(
    "--type", "-t", "passage_type", default="memory_shard", help="Passage type to process"
)
def world_model_backfill(
    branch: str, model: str, limit: int | None, dry_run: bool, passage_type: str
) -> None:
    """Process historical passages to build world model state.

    Processes passages sequentially using fold semantic (each passage
    conditioned on prior state). Shows progress bar for long operations.
    """

    async def _backfill() -> None:
        async with async_session() as session:
            # Count total passages for progress bar
            count_stmt = select(Passage).where(Passage.passage_type == passage_type)
            if limit:
                count_stmt = count_stmt.limit(limit)
            count_result = await session.execute(count_stmt)
            total = len(count_result.scalars().all())

            console = Console()
            console.print("\n[bold]World Model Backfill[/]")
            console.print(f"  Branch: {branch}")
            console.print(f"  Model: {model}")
            console.print(f"  Passages: {total}")
            if dry_run:
                console.print("  [yellow](dry run - refs not updated)[/]")
            console.print()

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Processing passages...", total=total)

                # Run backfill with progress updates
                stats = await backfill_world_models(
                    session,
                    branch=branch,
                    llm_model=model,
                    limit=limit,
                    dry_run=dry_run,
                    passage_type=passage_type,
                )

                progress.update(task, completed=stats["processed"])

            console.print("\n[bold green]Backfill complete:[/]")
            console.print(f"  Run ID:    {stats['run_id']}")
            console.print(f"  Branch:    {stats['branch']}")
            console.print(f"  Total:     {stats['total']}")
            console.print(f"  Processed: {stats['processed']}")
            console.print(f"  Errors:    {stats['errors']}")
            if stats["dry_run"]:
                console.print("  [yellow](dry run - refs not updated)[/]")

    asyncio.run(_backfill())


@world_model.command("commit")
@click.argument("passage_id")
@click.option("--branch", "-b", default="HEAD", help="Ref branch name")
@click.option("--model", "-m", default="deepseek-chat", help="LLM model to use")
def world_model_commit(passage_id: str, branch: str, model: str) -> None:
    """Process a single passage to update world model state.

    Takes an existing passage and updates the world model refs based on it.
    This is the "tick" operation that processes one passage through the
    world model extraction.
    """

    async def _commit() -> None:
        async with async_session() as session:
            async with session.begin():
                # Get the passage
                passage = await session.get(Passage, UUID(passage_id))
                if not passage:
                    raise click.ClickException(f"Passage {passage_id} not found")

                # Create processor and config
                processor = WorldModelProcessor(session)
                config = WorldModelConfig(
                    llm_model=model,
                    human_ref=f"world/human/{branch}",
                    persona_ref=f"world/persona/{branch}",
                    world_ref=f"world/world/{branch}",
                    update_refs=True,
                    fire_hooks=True,
                )

                # Create a group with just this passage
                group = ProcessorGroup(
                    passage_ids=[passage.id],
                    passages=[passage],
                    group_key=str(passage.id),
                    group_metadata={},
                )

                console = Console()
                console.print("\n[bold]World Model Commit[/]")
                console.print(f"  Passage: {passage.id}")
                console.print(f"  Branch: {branch}")
                console.print(f"  Model: {model}")
                console.print()

                with console.status("Processing passage..."):
                    result = await processor.process(group, config)

                if result.action == "create":
                    content = json.loads(result.content) if result.content else {}
                    console.print("[bold green]Success![/]")
                    console.print(f"  Human passage:  {content.get('human_id')}")
                    console.print(f"  Persona passage: {content.get('persona_id')}")
                    console.print(f"  World passage:   {content.get('world_id')}")
                else:
                    console.print(f"[bold red]Failed:[/] {result.action}")

    asyncio.run(_commit())


@world_model.command("seed-prompts")
def world_model_seed_prompts() -> None:
    """Seed the initial world model extraction prompts."""

    async def _seed() -> None:
        async with async_session() as session:
            async with session.begin():
                await seed_all_prompts(session)
                click.echo("Seeded world model prompts (human, persona, world).")

    asyncio.run(_seed())


if __name__ == "__main__":
    cli()
