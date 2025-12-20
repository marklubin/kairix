"""CLI for voice management operations."""

import asyncio
import sys

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from kairix_agent.voices import service

console = Console()

PROVIDERS = ["cartesia"]


async def list_voices() -> None:
    """List all configured voices."""
    voices = await service.list_voices()

    if not voices:
        console.print("[yellow]No voices configured.[/yellow]")
        console.print("Use 'voice-admin add' to add a voice.")
        return

    table = Table(title="Configured Voices")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Provider", style="green")
    table.add_column("Provider Voice ID", style="dim")
    table.add_column("Description")

    for voice in voices:
        table.add_row(
            voice.id,
            voice.name,
            voice.provider,
            voice.provider_voice_id,
            voice.description or "",
        )

    console.print(table)


async def add_voice() -> None:
    """Interactively add a new voice."""
    console.print("[bold cyan]Add New Voice[/bold cyan]\n")

    # Select provider
    console.print("Available providers:")
    for i, provider in enumerate(PROVIDERS, 1):
        console.print(f"  {i}. {provider}")

    provider_idx = Prompt.ask(
        "Select provider",
        choices=[str(i) for i in range(1, len(PROVIDERS) + 1)],
        default="1",
    )
    provider = PROVIDERS[int(provider_idx) - 1]

    # Get voice details
    name = Prompt.ask("Voice name (e.g., 'Friendly Female')")
    provider_voice_id = Prompt.ask(f"Provider voice ID (from {provider})")
    description = Prompt.ask("Description (optional)", default="")

    # Confirm
    console.print("\n[bold]Voice to create:[/bold]")
    console.print(f"  Name: {name}")
    console.print(f"  Provider: {provider}")
    console.print(f"  Provider Voice ID: {provider_voice_id}")
    console.print(f"  Description: {description or '(none)'}")

    confirm = Prompt.ask("\nCreate this voice?", choices=["y", "n"], default="y")
    if confirm != "y":
        console.print("[yellow]Cancelled.[/yellow]")
        return

    # Create voice
    voice = await service.create_voice(
        name=name,
        provider_voice_id=provider_voice_id,
        provider=provider,
        description=description or None,
    )

    console.print("\n[green]Voice created successfully![/green]")
    console.print(f"  ID: {voice.id}")


async def assign_voice() -> None:
    """Assign a voice to an agent."""
    console.print("[bold cyan]Assign Voice to Agent[/bold cyan]\n")

    # List available voices
    voices = await service.list_voices()
    if not voices:
        console.print("[red]No voices available. Add a voice first.[/red]")
        return

    console.print("Available voices:")
    for i, voice in enumerate(voices, 1):
        console.print(f"  {i}. {voice.name} ({voice.provider})")

    voice_idx = Prompt.ask(
        "Select voice",
        choices=[str(i) for i in range(1, len(voices) + 1)],
    )
    voice = voices[int(voice_idx) - 1]

    agent_id = Prompt.ask("Agent ID (e.g., 'agent-xxx')")

    # Confirm
    console.print(f"\n[bold]Assign voice '{voice.name}' to agent '{agent_id}'?[/bold]")
    confirm = Prompt.ask("Confirm?", choices=["y", "n"], default="y")
    if confirm != "y":
        console.print("[yellow]Cancelled.[/yellow]")
        return

    await service.set_agent_voice(agent_id, voice.id)
    console.print("\n[green]Voice assigned successfully![/green]")


async def main_async(args: list[str]) -> int:
    """Main async entry point."""
    if len(args) < 1:
        console.print("Usage: voice-admin <command>")
        console.print("")
        console.print("Commands:")
        console.print("  list      List all configured voices")
        console.print("  add       Add a new voice (interactive)")
        console.print("  assign    Assign a voice to an agent")
        return 1

    command = args[0]

    if command == "list":
        await list_voices()
    elif command == "add":
        await add_voice()
    elif command == "assign":
        await assign_voice()
    else:
        console.print(f"[red]Unknown command: {command}[/red]")
        return 1

    return 0


def main() -> None:
    """CLI entry point."""
    sys.exit(asyncio.run(main_async(sys.argv[1:])))


if __name__ == "__main__":
    main()
