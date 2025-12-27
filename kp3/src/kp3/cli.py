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
    set_ref,
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


@run.command("fold")
@click.argument("sql_query")
@click.option("--processor", "-p", required=True, help="Processor type")
@click.option("--config", "-c", default="{}", help="Processor config as JSON")
@click.option("--dry-run", is_flag=True, help="Show what would be processed without executing")
def run_fold(sql_query: str, processor: str, config: str, dry_run: bool) -> None:
    """Execute a fold operation over passages.

    Takes a SQL query that returns passage IDs and processes each one
    sequentially. Each passage becomes a single-element group, processed
    in order. Processors can implement fold semantics by reading/writing
    external state (e.g., refs) between iterations.

    The SQL query should return rows with a single 'id' column (passage UUIDs),
    ordered as desired. Example:

    \b
        kp3 run fold \\
            "SELECT id FROM passages WHERE passage_type = 'memory_shard' ORDER BY created_at" \\
            -p world_model \\
            -c '{"human_ref": "corindel/human/HEAD", ...}'

    For world_model processor, fold semantics are achieved via refs - each
    step reads current refs, processes the passage, and updates refs for
    the next iteration.
    """
    try:
        config_dict = json.loads(config)
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid JSON config: {e}") from e

    async def _fold() -> None:
        console = Console()

        async with async_session() as session:
            # Execute query to get passage IDs
            result = await session.execute(text(sql_query))
            rows = result.fetchall()

            if not rows:
                console.print("[yellow]No passages found matching query.[/]")
                return

            passage_ids = [row[0] for row in rows]

            console.print("\n[bold]Run Fold[/]")
            console.print(f"  Processor: {processor}")
            console.print(f"  Passages:  {len(passage_ids)}")
            console.print(f"  Config:    {config_dict}")
            console.print()

            if dry_run:
                console.print("[yellow]Dry run - showing first 10 passages:[/]")
                for i, pid in enumerate(passage_ids[:10], 1):
                    console.print(f"  {i}. {pid}")
                if len(passage_ids) > 10:
                    console.print(f"  ... and {len(passage_ids) - 10} more")
                return

            # Transform SQL into single-passage groups for fold processing
            # NOTE: This is intentional SQL construction - user provides SQL query
            groups_sql = f"""
                SELECT
                    ARRAY[id] as passage_ids,
                    id::text as group_key,
                    '{{}}'::jsonb as group_metadata
                FROM ({sql_query}) as q
            """  # noqa: S608

            async with session.begin():
                # Create the run
                processing_run = await create_run(
                    session,
                    input_sql=groups_sql,
                    processor_type=processor,
                    processor_config=config_dict,
                )
                console.print(f"Created run: {processing_run.id}")

                # Get processor instance
                proc = get_processor(processor, session=session)

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=console,
                ) as progress:
                    task = progress.add_task("Processing passages...", total=len(passage_ids))

                    processing_run = await execute_run(session, processing_run, proc)

                    progress.update(task, completed=processing_run.processed_groups or 0)

                console.print("\n[bold green]Fold complete:[/]")
                console.print(f"  Run ID:    {processing_run.id}")
                console.print(f"  Status:    {processing_run.status}")
                groups = f"{processing_run.processed_groups}/{processing_run.total_groups}"
                console.print(f"  Processed: {groups}")
                console.print(f"  Output:    {processing_run.output_count}")
                if processing_run.error_message:
                    console.print(f"  [red]Error: {processing_run.error_message}[/]")

    asyncio.run(_fold())


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


@refs.command("set")
@click.argument("ref_name")
@click.argument("passage_id")
@click.option("--no-hooks", is_flag=True, help="Don't fire hooks after setting ref")
def refs_set(ref_name: str, passage_id: str, no_hooks: bool) -> None:
    """Set a ref to point to a passage.

    Updates the ref to point to the specified passage and fires any
    configured hooks (e.g., Letta block sync).

    Example:
        kp3 refs set corindel/world/HEAD abc123-def456-...
    """

    async def _set() -> None:
        async with async_session() as session:
            async with session.begin():
                # Verify passage exists
                passage = await session.get(Passage, UUID(passage_id))
                if not passage:
                    raise click.ClickException(f"Passage {passage_id} not found")

                await set_ref(
                    session,
                    name=ref_name,
                    passage_id=UUID(passage_id),
                    fire_hooks=not no_hooks,
                )

                console = Console()
                console.print(f"[green]Set ref:[/] {ref_name} -> {passage_id}")
                if not no_hooks:
                    console.print("[dim]Hooks fired[/]")

    asyncio.run(_set())


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


@world_model.command("step")
@click.argument("passage_id")
@click.option("--branch", "-b", default="HEAD", help="Ref branch name")
@click.option("--ref-prefix", "-p", default="world", help="Ref prefix (e.g., 'corindel')")
@click.option("--model", "-m", default="deepseek-chat", help="LLM model to use")
@click.option("--agent-id", "-a", default="", help="Letta agent ID for shadow table sync")
def world_model_step(
    passage_id: str, branch: str, ref_prefix: str, model: str, agent_id: str
) -> None:
    """Process a single passage to update world model state.

    Takes a passage and runs one step of world model extraction, updating
    the human/persona/world blocks based on the passage content.

    Use --ref-prefix to target specific agent refs (e.g., --ref-prefix corindel
    will use corindel/human/HEAD, corindel/persona/HEAD, corindel/world/HEAD).

    If --agent-id is provided, entities will be synced to shadow tables
    (world_model_projects, world_model_entities, world_model_themes) with
    proper agent segmentation for multi-agent support.

    NOTE: Like fold, step does NOT fire hooks directly. Use 'branch promote'
    or 'refs set' to explicitly fire hooks after processing.
    """

    async def _step() -> None:
        async with async_session() as session:
            async with session.begin():
                # Get the passage
                passage = await session.get(Passage, UUID(passage_id))
                if not passage:
                    raise click.ClickException(f"Passage {passage_id} not found")

                # Create processor and config
                # NOTE: fire_hooks=False - step never fires hooks directly
                processor = WorldModelProcessor(session)
                config = WorldModelConfig(
                    llm_model=model,
                    human_ref=f"{ref_prefix}/human/{branch}",
                    persona_ref=f"{ref_prefix}/persona/{branch}",
                    world_ref=f"{ref_prefix}/world/{branch}",
                    update_refs=True,
                    fire_hooks=False,  # Step never fires hooks
                    agent_id=agent_id,
                    sync_shadow_tables=bool(agent_id),
                )

                # Create a group with just this passage
                group = ProcessorGroup(
                    passage_ids=[passage.id],
                    passages=[passage],
                    group_key=str(passage.id),
                    group_metadata={},
                )

                console = Console()
                console.print("\n[bold]World Model Step[/]")
                console.print(f"  Passage: {passage.id}")
                console.print(f"  Refs: {ref_prefix}/*/{branch}")
                console.print(f"  Model: {model}")
                if agent_id:
                    console.print(f"  Agent ID: {agent_id} (shadow sync enabled)")
                console.print()

                with console.status("Processing passage..."):
                    result = await processor.process(group, config)

                if result.action == "create":
                    content = json.loads(result.content) if result.content else {}
                    console.print("[bold green]Success![/]")
                    console.print(f"  Human passage:  {content.get('human_id')}")
                    console.print(f"  Persona passage: {content.get('persona_id')}")
                    console.print(f"  World passage:   {content.get('world_id')}")
                    if agent_id:
                        console.print("  [dim]Shadow tables synced[/]")
                else:
                    console.print(f"[bold red]Failed:[/] {result.action}")

    asyncio.run(_step())


@world_model.command("fold")
@click.argument("sql_query")
@click.option("--branch", "-b", default="HEAD", help="Ref branch name")
@click.option(
    "--ref-prefix", "-p", default="world", help="Ref prefix (e.g., 'corindel')"
)
@click.option("--model", "-m", default="deepseek-chat", help="LLM model to use")
@click.option("--agent-id", "-a", default="", help="Letta agent ID for shadow table sync")
@click.option("--dry-run", is_flag=True, help="Show what would be processed without executing")
@click.pass_context
def world_model_fold(
    ctx: click.Context,
    sql_query: str,
    branch: str,
    ref_prefix: str,
    model: str,
    agent_id: str,
    dry_run: bool,
) -> None:
    """Process multiple passages sequentially with fold semantics.

    Convenience wrapper around 'kp3 run fold' for world model extraction.
    Each step reads current refs, processes the passage, and updates refs
    for the next iteration.

    IMPORTANT: Fold operations NEVER fire hooks directly. Hooks only fire via
    explicit 'world-model branch promote' or 'refs set' commands. This allows
    running fold on experiment branches without affecting production agents.

    \b
        kp3 world-model fold \\
            "SELECT id FROM passages WHERE passage_type = 'memory_shard' ORDER BY created_at" \\
            --ref-prefix corindel \\
            --agent-id agent-56a10649-...
    """
    # Build world model config
    # NOTE: fire_hooks=False - fold NEVER fires hooks directly
    # Hooks only fire via explicit 'branch promote' or 'refs set' commands
    config = {
        "llm_model": model,
        "human_ref": f"{ref_prefix}/human/{branch}",
        "persona_ref": f"{ref_prefix}/persona/{branch}",
        "world_ref": f"{ref_prefix}/world/{branch}",
        "update_refs": True,
        "fire_hooks": False,  # Fold never fires hooks
        "agent_id": agent_id,
        "sync_shadow_tables": bool(agent_id),
    }

    # Invoke the generic run fold command
    ctx.invoke(
        run_fold,
        sql_query=sql_query,
        processor="world_model",
        config=json.dumps(config),
        dry_run=dry_run,
    )


@world_model.command("seed-prompts")
def world_model_seed_prompts() -> None:
    """Seed the initial world model extraction prompts."""

    async def _seed() -> None:
        async with async_session() as session:
            async with session.begin():
                await seed_all_prompts(session)
                click.echo("Seeded world model prompts (human, persona, world).")

    asyncio.run(_seed())


# =============================================================================
# BRANCH COMMANDS
# =============================================================================


@world_model.group("branch")
def branch() -> None:
    """Manage world model branches."""
    pass


@branch.command("create")
@click.argument("name")
@click.option("--description", "-d", help="Branch description")
@click.option("--main", "is_main", is_flag=True, help="Create as main/production branch")
def branch_create(name: str, description: str | None, is_main: bool) -> None:
    """Create a new world model branch (new lineage, empty refs).

    NAME should be in format 'prefix/branch' (e.g., 'corindel/HEAD').
    Use 'branch fork' to derive from an existing branch.

    \b
    Examples:
        kp3 world-model branch create corindel/HEAD --main
        kp3 world-model branch create myagent/HEAD --main -d "Main branch for myagent"
    """
    from kp3.services.branches import BranchExistsError, create_branch

    parts = name.split("/")
    if len(parts) != 2:
        raise click.ClickException(
            "Branch name must be in format 'prefix/branch' (e.g., 'agent/HEAD')"
        )

    ref_prefix, branch_name = parts

    async def _create() -> None:
        async with async_session() as session:
            async with session.begin():
                try:
                    new_branch = await create_branch(
                        session,
                        ref_prefix,
                        branch_name,
                        description=description,
                        is_main=is_main,
                        hooks_enabled=is_main,
                    )
                    Console().print(f"[green]Created branch[/] {new_branch.name}")
                    Console().print(f"  human_ref:   {new_branch.human_ref}")
                    Console().print(f"  persona_ref: {new_branch.persona_ref}")
                    Console().print(f"  world_ref:   {new_branch.world_ref}")
                    hooks_status = "enabled" if new_branch.hooks_enabled else "disabled"
                    Console().print(f"  hooks:       {hooks_status}")

                except BranchExistsError as e:
                    raise click.ClickException(str(e)) from e

    asyncio.run(_create())


@branch.command("fork")
@click.argument("source")
@click.argument("name")
@click.option("--description", "-d", help="Branch description")
def branch_fork(source: str, name: str, description: str | None) -> None:
    """Fork a new branch from an existing branch (copies refs).

    SOURCE is the branch to fork from (e.g., 'corindel/HEAD').
    NAME is the new branch name (e.g., 'corindel/experiment-1').

    \b
    Examples:
        kp3 world-model branch fork corindel/HEAD corindel/experiment-1
        kp3 world-model branch fork corindel/HEAD corindel/test -d "Testing new prompts"
    """
    from kp3.services.branches import BranchExistsError, BranchNotFoundError, fork_branch

    source_parts = source.split("/")
    name_parts = name.split("/")

    if len(source_parts) != 2 or len(name_parts) != 2:
        raise click.ClickException(
            "Both source and name must be in format 'prefix/branch'"
        )

    source_prefix, source_branch = source_parts
    name_prefix, new_branch_name = name_parts

    if source_prefix != name_prefix:
        raise click.ClickException(
            f"Cannot fork across prefixes: {source_prefix} != {name_prefix}"
        )

    async def _fork() -> None:
        async with async_session() as session:
            async with session.begin():
                try:
                    new_branch = await fork_branch(
                        session,
                        source_prefix,
                        source_branch,
                        new_branch_name,
                        description=description,
                    )
                    Console().print(
                        f"[green]Forked branch[/] {new_branch.name} "
                        f"(from {source})"
                    )
                    Console().print(f"  human_ref:   {new_branch.human_ref}")
                    Console().print(f"  persona_ref: {new_branch.persona_ref}")
                    Console().print(f"  world_ref:   {new_branch.world_ref}")
                    Console().print("  hooks:       disabled")

                except BranchNotFoundError as e:
                    raise click.ClickException(str(e)) from e
                except BranchExistsError as e:
                    raise click.ClickException(str(e)) from e

    asyncio.run(_fork())


@branch.command("list")
@click.option("--prefix", "-p", help="Filter by prefix (e.g., 'corindel')")
def branch_list(prefix: str | None) -> None:
    """List world model branches."""
    from kp3.services.branches import list_branches

    async def _list() -> None:
        async with async_session() as session:
            branches = await list_branches(session, ref_prefix=prefix)

            if not branches:
                click.echo("No branches found.")
                return

            console = Console()
            for b in branches:
                is_main_str = "[bold cyan]MAIN[/]" if b.is_main else ""
                hooks_str = "[green]hooks[/]" if b.hooks_enabled else "[dim]no-hooks[/]"
                console.print(
                    f"{b.name:<30} {hooks_str:<15} {is_main_str}  "
                    f"{b.created_at:%Y-%m-%d %H:%M}"
                )

    asyncio.run(_list())


@branch.command("show")
@click.argument("name")
def branch_show(name: str) -> None:
    """Show details of a world model branch."""
    from kp3.services.branches import get_branch_by_name
    from kp3.services.refs import get_ref, get_ref_passage

    async def _show() -> None:
        async with async_session() as session:
            branch_obj = await get_branch_by_name(session, name)

            if not branch_obj:
                raise click.ClickException(f"Branch '{name}' not found")

            console = Console()
            console.print(f"\n[bold]Branch:[/] {branch_obj.name}")
            console.print(f"[bold]Prefix:[/] {branch_obj.ref_prefix}")
            console.print(f"[bold]Branch Name:[/] {branch_obj.branch_name}")
            console.print(f"[bold]Main:[/] {'Yes' if branch_obj.is_main else 'No'}")
            console.print(f"[bold]Hooks Enabled:[/] {'Yes' if branch_obj.hooks_enabled else 'No'}")
            if branch_obj.description:
                console.print(f"[bold]Description:[/] {branch_obj.description}")
            console.print(f"[bold]Created:[/] {branch_obj.created_at}")
            console.print()

            # Show ref status
            console.print("[bold]Refs:[/]")
            for ref_name, label in [
                (branch_obj.human_ref, "human"),
                (branch_obj.persona_ref, "persona"),
                (branch_obj.world_ref, "world"),
            ]:
                passage_id = await get_ref(session, ref_name)
                if passage_id:
                    passage = await get_ref_passage(session, ref_name)
                    if passage and len(passage.content) > 50:
                        preview = passage.content[:50] + "..."
                    elif passage:
                        preview = passage.content
                    else:
                        preview = ""
                    console.print(f"  {label:<8} {ref_name:<35} -> {passage_id}")
                    if preview:
                        console.print(f"           [dim]{preview}[/]")
                else:
                    console.print(f"  {label:<8} {ref_name:<35} -> [yellow](not set)[/]")

    asyncio.run(_show())


@branch.command("promote")
@click.argument("source")
@click.option("--to", "target", default="HEAD", help="Target branch (default: HEAD)")
def branch_promote(source: str, target: str) -> None:
    """Promote a branch to another branch (typically HEAD).

    Copies the current passage IDs from source refs to target refs
    and fires hooks on the target refs.

    \b
    Example:
        kp3 world-model branch promote corindel/experiment-1
        kp3 world-model branch promote corindel/experiment-1 --to stable
    """
    from kp3.services.branches import BranchNotFoundError, promote_branch

    parts = source.split("/")
    if len(parts) != 2:
        raise click.ClickException("Source must be in format 'prefix/branch'")

    ref_prefix, source_branch = parts

    async def _promote() -> None:
        async with async_session() as session:
            async with session.begin():
                try:
                    target_branch = await promote_branch(session, ref_prefix, source_branch, target)

                    console = Console()
                    console.print(f"[green]Promoted[/] {source} -> {target_branch.name}")
                    if target_branch.hooks_enabled:
                        console.print("[dim]Hooks fired on target refs[/]")

                except BranchNotFoundError as e:
                    raise click.ClickException(str(e)) from e

    asyncio.run(_promote())


@branch.command("delete")
@click.argument("name")
@click.option("--delete-refs", is_flag=True, help="Also delete the underlying refs")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
def branch_delete(name: str, delete_refs: bool, force: bool) -> None:
    """Delete a world model branch.

    By default, only deletes the branch record. Use --delete-refs to also
    delete the underlying passage refs.
    """
    from kp3.services.branches import BranchError, delete_branch

    parts = name.split("/")
    if len(parts) != 2:
        raise click.ClickException("Name must be in format 'prefix/branch'")

    ref_prefix, branch_name = parts

    if not force:
        click.confirm(f"Delete branch '{name}'?", abort=True)

    async def _delete() -> None:
        async with async_session() as session:
            async with session.begin():
                try:
                    deleted = await delete_branch(
                        session, ref_prefix, branch_name, delete_refs=delete_refs
                    )

                    if deleted:
                        console = Console()
                        console.print(f"[green]Deleted branch[/] {name}")
                        if delete_refs:
                            console.print("[dim]Underlying refs also deleted[/]")
                    else:
                        click.echo(f"Branch '{name}' not found.")

                except BranchError as e:
                    raise click.ClickException(str(e)) from e

    asyncio.run(_delete())


if __name__ == "__main__":
    cli()
