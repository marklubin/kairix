"""CLI for unified agent configuration management."""

from __future__ import annotations

import asyncio
import json
import sys
from typing import TYPE_CHECKING

from letta_client import AsyncLetta
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

if TYPE_CHECKING:
    from letta_client.types import AgentState

from kairix_agent.agents.schemas import AgentCreate, BlockSchema
from kairix_agent.agents.service import AgentService
from kairix_agent.config import Config
from kairix_agent.provisioning.blocks import DEFAULT_BLOCKS

console = Console()

# Minimum args required for commands that take a name argument
MIN_ARGS_WITH_NAME = 2


async def get_session() -> AsyncSession:
    """Create an async database session."""
    engine = create_async_engine(Config.DATABASE_URL.value)
    async with AsyncSession(engine) as session:
        return session


async def list_agents() -> None:
    """List all configured agents."""
    engine = create_async_engine(Config.DATABASE_URL.value)
    async with AsyncSession(engine) as session:
        service = AgentService(session)
        agents = await service.list_all()

    if not agents:
        console.print("[yellow]No agents configured.[/yellow]")
        console.print("Use 'agent-admin create' to create an agent.")
        return

    table = Table(title="Configured Agents")
    table.add_column("Name", style="cyan")
    table.add_column("Letta ID", style="dim")
    table.add_column("Model", style="green")
    table.add_column("Voice", style="magenta")
    table.add_column("Synced", style="yellow")

    for agent in agents:
        synced = "✓" if agent.letta_agent_id else "✗"
        table.add_row(
            agent.name,
            agent.letta_agent_id or "-",
            agent.inference_model,
            agent.voice_id or "-",
            synced,
        )

    console.print(table)


async def show_agent(name: str) -> None:
    """Show detailed agent configuration."""
    engine = create_async_engine(Config.DATABASE_URL.value)
    async with AsyncSession(engine) as session:
        service = AgentService(session)
        agent = await service.get_by_name(name)

    if not agent:
        console.print(f"[red]Agent '{name}' not found.[/red]")
        return

    console.print(f"\n[bold cyan]Agent: {agent.name}[/bold cyan]\n")
    console.print(f"[bold]ID:[/bold] {agent.id}")
    console.print(f"[bold]Description:[/bold] {agent.description or '(none)'}")

    console.print("\n[bold underline]Primary LLM Config[/bold underline]")
    console.print(f"  Model: {agent.inference_model}")
    console.print(f"  Provider URL: {agent.inference_provider_url or '(default)'}")
    console.print(f"  Embedding: {agent.embedding_model}")
    console.print(f"  Context Window: {agent.context_window}")
    console.print(f"  Max Tokens: {agent.max_tokens}")
    console.print(f"  Reasoner: {agent.enable_reasoner}")

    console.print("\n[bold underline]Background LLM Config[/bold underline]")
    console.print(f"  Model: {agent.background_llm_model}")
    console.print(f"  URL: {agent.background_llm_url}")

    console.print("\n[bold underline]Block Schema[/bold underline]")
    for block in agent.block_schema:
        ref_suffix = block.get("kp3_ref_suffix", "-")
        console.print(f"  {block['label']}: limit={block.get('limit', 5000)}, ref={ref_suffix}")

    console.print("\n[bold underline]Tools[/bold underline]")
    console.print(f"  Include Base: {agent.include_base_tools}")
    console.print(f"  Tools: {', '.join(agent.tools) if agent.tools else '(none)'}")

    console.print("\n[bold underline]Integration[/bold underline]")
    console.print(f"  Voice ID: {agent.voice_id or '(none)'}")
    console.print(f"  KP3 Prefix: {agent.kp3_ref_prefix or '(none)'}")
    console.print(f"  KP3 Hooks: {agent.kp3_hooks_enabled}")

    console.print("\n[bold underline]Letta Sync State[/bold underline]")
    console.print(f"  Letta Agent ID: {agent.letta_agent_id or '(not synced)'}")
    console.print(f"  Synced At: {agent.letta_synced_at or '-'}")
    console.print(f"  Sync Hash: {agent.letta_sync_hash or '-'}")


async def create_agent_interactive() -> None:
    """Interactively create a new agent."""
    console.print("[bold cyan]Create New Agent[/bold cyan]\n")

    # Basic info
    name = Prompt.ask("Agent name (e.g., 'Corindel')")
    description = Prompt.ask("Description (optional)", default="")

    # LLM config
    console.print("\n[bold]Primary LLM Configuration:[/bold]")
    inference_model = Prompt.ask(
        "Inference model",
        default="openai/Qwen2.5-7B-Instruct-AWQ",
    )
    inference_url = Prompt.ask(
        "Inference provider URL (blank for default)",
        default="",
    )

    # Background LLM
    console.print("\n[bold]Background LLM Configuration (for summarizer, insights):[/bold]")
    bg_model = Prompt.ask("Background model", default="deepseek-chat")
    bg_url = Prompt.ask("Background URL", default="https://api.deepseek.com")

    # KP3 integration
    console.print("\n[bold]KP3 Integration:[/bold]")
    kp3_prefix = Prompt.ask(
        "KP3 ref prefix (e.g., 'corindel')",
        default=name.lower(),
    )

    # Block schema - use defaults
    console.print("\n[bold]Block Schema:[/bold]")
    use_defaults = Confirm.ask("Use default block schema?", default=True)

    block_schema: list[BlockSchema] = []
    if use_defaults:
        for block_def in DEFAULT_BLOCKS:
            ref_suffix = f"{block_def.label}/HEAD"
            block_schema.append(
                BlockSchema(
                    label=block_def.label,
                    description=block_def.description,
                    limit=block_def.limit,
                    kp3_ref_suffix=ref_suffix,
                    initial_value=block_def.initial_value,
                )
            )
        console.print(f"  Using {len(block_schema)} default blocks")

    # Tools - default conversational tools
    default_tools = [
        "core_memory_append",
        "core_memory_replace",
        "memory_rethink",
        "memory_insert",
        "memory_replace",
        "memory_finish_edits",
        "archival_memory_insert",
        "archival_memory_search",
        "conversation_search",
        "store_memories",
        "fetch_webpage",
        "web_search",
    ]

    # System prompt - placeholder, would be loaded from DB or file in real usage
    console.print("\n[bold]System Prompt:[/bold]")
    console.print("  (Will use placeholder - edit after creation)")
    system_prompt = f"You are {name}, a helpful assistant."

    # Confirm
    console.print("\n[bold]Agent to create:[/bold]")
    console.print(f"  Name: {name}")
    console.print(f"  Model: {inference_model}")
    console.print(f"  KP3 Prefix: {kp3_prefix}")
    console.print(f"  Blocks: {len(block_schema)}")

    if not Confirm.ask("\nCreate this agent?", default=True):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    # Create agent
    data = AgentCreate(
        name=name,
        description=description or None,
        system_prompt=system_prompt,
        inference_model=inference_model,
        inference_provider_url=inference_url or None,
        background_llm_model=bg_model,
        background_llm_url=bg_url,
        block_schema=block_schema,
        tools=default_tools,
        kp3_ref_prefix=kp3_prefix,
    )

    engine = create_async_engine(Config.DATABASE_URL.value)
    async with AsyncSession(engine) as session:
        service = AgentService(session)
        agent = await service.create(data)

    console.print("\n[green]Agent created successfully![/green]")
    console.print(f"  ID: {agent.id}")
    console.print(f"  Name: {agent.name}")
    console.print("\nNext steps:")
    console.print("  1. Edit system_prompt as needed")
    console.print("  2. Run 'agent-admin sync <name>' to sync to Letta")


async def delete_agent(name: str) -> None:
    """Delete an agent."""
    engine = create_async_engine(Config.DATABASE_URL.value)
    async with AsyncSession(engine) as session:
        service = AgentService(session)
        agent = await service.get_by_name(name)

        if not agent:
            console.print(f"[red]Agent '{name}' not found.[/red]")
            return

        console.print(f"\n[bold red]Delete agent '{agent.name}'?[/bold red]")
        console.print(f"  ID: {agent.id}")
        console.print(f"  Letta ID: {agent.letta_agent_id or '(not synced)'}")
        console.print("\n[yellow]Warning: This does NOT delete the agent from Letta.[/yellow]")

        if not Confirm.ask("Delete?", default=False):
            console.print("[yellow]Cancelled.[/yellow]")
            return

        await service.delete(agent)

    console.print("\n[green]Agent deleted from config database.[/green]")


async def export_agent(name: str) -> None:
    """Export agent config as JSON."""
    engine = create_async_engine(Config.DATABASE_URL.value)
    async with AsyncSession(engine) as session:
        service = AgentService(session)
        agent = await service.get_by_name(name)

    if not agent:
        console.print(f"[red]Agent '{name}' not found.[/red]")
        return

    # Export as dict
    export_data = {
        "name": agent.name,
        "description": agent.description,
        "system_prompt": agent.system_prompt,
        "inference_model": agent.inference_model,
        "inference_provider_url": agent.inference_provider_url,
        "embedding_model": agent.embedding_model,
        "context_window": agent.context_window,
        "max_tokens": agent.max_tokens,
        "enable_reasoner": agent.enable_reasoner,
        "max_reasoning_tokens": agent.max_reasoning_tokens,
        "background_llm_model": agent.background_llm_model,
        "background_llm_url": agent.background_llm_url,
        "block_schema": agent.block_schema,
        "tools": agent.tools,
        "include_base_tools": agent.include_base_tools,
        "voice_id": agent.voice_id,
        "kp3_ref_prefix": agent.kp3_ref_prefix,
        "kp3_hooks_enabled": agent.kp3_hooks_enabled,
    }

    # Output to stdout for piping (not console.print which adds formatting)
    sys.stdout.write(json.dumps(export_data, indent=2) + "\n")


async def main_async(args: list[str]) -> int:
    """Main async entry point."""
    if len(args) < 1:
        console.print("Usage: agent-admin <command> [args]")
        console.print("")
        console.print("Commands:")
        console.print("  list              List all configured agents")
        console.print("  show <name>       Show detailed agent configuration")
        console.print("  create            Create a new agent (interactive)")
        console.print("  delete <name>     Delete an agent from config DB")
        console.print("  export <name>     Export agent config as JSON")
        console.print("")
        console.print("Migration commands:")
        console.print("  migrate           Migrate existing agents to unified config")
        console.print("  migrate --dry-run Preview migration without changes")
        return 1

    command = args[0]

    if command == "list":
        await list_agents()
    elif command == "show":
        if len(args) < MIN_ARGS_WITH_NAME:
            console.print("[red]Usage: agent-admin show <name>[/red]")
            return 1
        await show_agent(args[1])
    elif command == "create":
        await create_agent_interactive()
    elif command == "delete":
        if len(args) < MIN_ARGS_WITH_NAME:
            console.print("[red]Usage: agent-admin delete <name>[/red]")
            return 1
        await delete_agent(args[1])
    elif command == "export":
        if len(args) < MIN_ARGS_WITH_NAME:
            console.print("[red]Usage: agent-admin export <name>[/red]")
            return 1
        await export_agent(args[1])
    elif command == "migrate":
        dry_run = "--dry-run" in args
        await migrate_agents(dry_run=dry_run)
    else:
        console.print(f"[red]Unknown command: {command}[/red]")
        return 1

    return 0


async def migrate_agents(*, dry_run: bool = False) -> None:
    """Migrate existing agents from old tables to unified config.

    This reads from:
    - agent_definitions (system prompts)
    - agent_voice_settings (voice assignments)
    - Letta API (existing agents)

    And creates entries in the new agents table.
    """
    console.print("[bold cyan]Agent Migration[/bold cyan]\n")

    if dry_run:
        console.print("[yellow]DRY RUN - no changes will be made[/yellow]\n")

    # Connect to Letta to discover existing agents
    letta = AsyncLetta(base_url=Config.LETTA_BASE_URL.value)

    console.print("Discovering agents from Letta...")
    letta_agents_page = await letta.agents.list()
    # AsyncArrayPage is iterable, convert to list
    letta_agents: list[AgentState] = list(letta_agents_page)  # type: ignore[arg-type]

    if not letta_agents:
        console.print("[yellow]No agents found in Letta.[/yellow]")
        return

    console.print(f"Found {len(letta_agents)} agent(s) in Letta\n")

    engine = create_async_engine(Config.DATABASE_URL.value)

    for letta_agent in letta_agents:
        console.print(f"\n[bold]Agent: {letta_agent.name}[/bold]")
        console.print(f"  Letta ID: {letta_agent.id}")

        async with AsyncSession(engine) as session:
            service = AgentService(session)

            # Check if already migrated
            existing = await service.get_by_letta_id(letta_agent.id)
            if existing:
                console.print(f"  [dim]Already migrated as '{existing.name}'[/dim]")
                continue

            # Also check by name
            existing = await service.get_by_name(letta_agent.name)
            if existing:
                console.print("  [dim]Name already exists in agents table[/dim]")
                continue

            # Build block schema from defaults + KP3 refs
            kp3_prefix = letta_agent.name.lower().replace(" ", "_")
            block_schema = [
                BlockSchema(
                    label=block_def.label,
                    description=block_def.description,
                    limit=block_def.limit,
                    kp3_ref_suffix=f"{block_def.label}/HEAD",
                    initial_value=block_def.initial_value,
                )
                for block_def in DEFAULT_BLOCKS
            ]

            # Look up voice from old agent_voice_settings table
            voice_id = await _get_voice_for_agent(session, letta_agent.id)

            # Extract LLM config from Letta agent
            llm_model = letta_agent.model or "anthropic/claude-sonnet-4-20250514"
            llm_config = letta_agent.llm_config
            context_window = llm_config.context_window if llm_config else 25000
            embedding = letta_agent.embedding or "openai/text-embedding-3-small"

            if dry_run:
                console.print(f"  [yellow]Would create agent '{letta_agent.name}'[/yellow]")
                console.print(f"    Model: {llm_model}")
                console.print(f"    Voice ID: {voice_id or '(none)'}")
                console.print(f"    KP3 Prefix: {kp3_prefix}")
                continue

            # Create the unified agent config
            data = AgentCreate(
                name=letta_agent.name,
                description=letta_agent.description,
                system_prompt=letta_agent.system or "",
                inference_model=llm_model,
                inference_provider_url=None,  # Will use default
                embedding_model=embedding,
                context_window=context_window or 25000,
                max_tokens=4096,
                enable_reasoner=True,
                block_schema=block_schema,
                tools=[],  # Tools will be loaded from Letta
                voice_id=voice_id,
                kp3_ref_prefix=kp3_prefix,
            )

            agent = await service.create(data)

            # Mark as already synced (since we got it from Letta)
            await service.mark_synced(agent, letta_agent.id)

            console.print(f"  [green]Created '{agent.name}' (ID: {agent.id})[/green]")

    console.print("\n[bold green]Migration complete![/bold green]")


async def _get_voice_for_agent(session: AsyncSession, agent_id: str) -> str | None:
    """Look up voice_id from old agent_voice_settings table."""
    # Check if table exists first
    result = await session.execute(
        text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_name = 'agent_voice_settings')"
        )
    )
    exists = result.scalar()

    if not exists:
        return None

    result = await session.execute(
        text("SELECT voice_id FROM agent_voice_settings WHERE agent_id = :agent_id"),
        {"agent_id": agent_id},
    )
    row = result.first()
    return row[0] if row else None


def main() -> None:
    """CLI entry point."""
    sys.exit(asyncio.run(main_async(sys.argv[1:])))


if __name__ == "__main__":
    main()
