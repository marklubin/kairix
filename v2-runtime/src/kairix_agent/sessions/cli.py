"""CLI for session management and recovery operations."""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from letta_client import AsyncLetta
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
from rich.table import Table
from sqlalchemy import delete, func, select

from kairix_agent.agent_config import get_agent_config
from kairix_agent.config import Config
from kairix_agent.sessions import (
    SessionStatus,
    create_session,
    get_session_message_ids,
)
from kairix_agent.sessions.models import Session, SessionMessage
from kairix_agent.sessions.service import _async_session
from kairix_agent.worker.jobs.summarize import summarize_session

console = Console()


@dataclass
class DetectedSession:
    """A session detected from message timestamps."""

    message_ids: list[str]
    period_start: datetime
    period_end: datetime

    @property
    def message_count(self) -> int:
        return len(self.message_ids)

    @property
    def duration(self) -> timedelta:
        return self.period_end - self.period_start


async def get_failed_sessions() -> list[Session]:
    """Get all sessions with failed status."""
    async with _async_session() as db:
        result = await db.execute(
            select(Session)
            .where(Session.status == SessionStatus.FAILED.value)
            .order_by(Session.period_start)
        )
        return list(result.scalars().all())


async def delete_session_and_messages(session_id: str) -> None:
    """Delete a session and its associated messages."""
    async with _async_session() as db:
        await db.execute(
            delete(SessionMessage).where(SessionMessage.session_id == session_id)
        )
        await db.execute(delete(Session).where(Session.id == session_id))
        await db.commit()


async def get_message_timestamps(
    agent_id: str,
    message_ids: list[str],
    letta_url: str,
) -> list[tuple[str, datetime]]:
    """Get message IDs with their timestamps from Letta.

    Returns list of (message_id, timestamp) sorted by timestamp.
    """
    client = AsyncLetta(base_url=letta_url)

    message_id_set = set(message_ids)
    seen_ids: set[str] = set()
    messages_with_dates: list[tuple[str, datetime]] = []

    async for msg in client.agents.messages.list(agent_id):
        # Deduplicate - Letta API may return same message multiple times
        if msg.id in message_id_set and msg.date and msg.id not in seen_ids:
            messages_with_dates.append((msg.id, msg.date))  # noqa: PERF401
            seen_ids.add(msg.id)

    # Sort by date
    messages_with_dates.sort(key=lambda x: x[1])
    return messages_with_dates


def chunk_messages_into_sessions(
    messages_with_dates: list[tuple[str, datetime]],
    gap_minutes: int,
) -> list[DetectedSession]:
    """Chunk messages into sessions based on time gaps.

    Args:
        messages_with_dates: List of (message_id, timestamp) sorted by time.
        gap_minutes: Minimum gap in minutes to start a new session.

    Returns:
        List of DetectedSession objects.
    """
    if not messages_with_dates:
        return []

    sessions: list[DetectedSession] = []
    current_ids: list[str] = []
    current_start: datetime | None = None

    for msg_id, msg_date in messages_with_dates:
        if not current_ids:
            current_ids.append(msg_id)
            current_start = msg_date
        else:
            # Get the last message's date
            last_date = messages_with_dates[
                next(
                    i
                    for i, (mid, _) in enumerate(messages_with_dates)
                    if mid == current_ids[-1]
                )
            ][1]

            gap = msg_date - last_date
            if gap >= timedelta(minutes=gap_minutes):
                # Gap detected - save current session
                sessions.append(
                    DetectedSession(
                        message_ids=current_ids.copy(),
                        period_start=current_start,  # type: ignore[arg-type]
                        period_end=last_date,
                    )
                )
                current_ids = [msg_id]
                current_start = msg_date
            else:
                current_ids.append(msg_id)

    # Don't forget the last session
    if current_ids and current_start:
        last_date = messages_with_dates[
            next(
                i
                for i, (mid, _) in enumerate(messages_with_dates)
                if mid == current_ids[-1]
            )
        ][1]
        sessions.append(
            DetectedSession(
                message_ids=current_ids,
                period_start=current_start,
                period_end=last_date,
            )
        )

    return sessions


async def list_failed() -> None:
    """List all failed sessions."""
    failed = await get_failed_sessions()

    if not failed:
        console.print("[green]No failed sessions found.[/green]")
        return

    table = Table(title="Failed Sessions")
    table.add_column("Session ID", style="dim")
    table.add_column("Agent ID", style="cyan")
    table.add_column("Messages", justify="right")
    table.add_column("Period Start")
    table.add_column("Period End")
    table.add_column("Error", style="red")

    for session in failed:
        table.add_row(
            session.id[:8] + "...",
            session.agent_id[-12:],
            str(session.message_count),
            session.period_start.strftime("%Y-%m-%d %H:%M"),
            session.period_end.strftime("%Y-%m-%d %H:%M"),
            (session.error_message or "")[:40],
        )

    console.print(table)
    console.print(f"\n[yellow]Total: {len(failed)} failed session(s)[/yellow]")


async def recover_sessions(*, dry_run: bool = False, auto_yes: bool = False) -> None:  # noqa: PLR0915
    """Recover failed sessions by re-chunking and re-running summarization."""
    letta_url = Config.LETTA_BASE_URL.value
    gap_minutes = Config.SESSION_GAP_MINUTES.value

    console.print(
        Panel(
            f"[bold]Session Recovery[/bold]\n\n"
            f"Letta URL: {letta_url}\n"
            f"Session Gap: {gap_minutes} minutes\n"
            f"Dry Run: {dry_run}",
            title="Configuration",
        )
    )

    # Get failed sessions
    failed = await get_failed_sessions()

    if not failed:
        console.print("\n[green]No failed sessions to recover.[/green]")
        return

    console.print(f"\n[yellow]Found {len(failed)} failed session(s) to recover[/yellow]\n")

    # Process each failed session
    for session in failed:
        console.print(f"\n[bold cyan]Processing session {session.id[:8]}...[/bold cyan]")
        console.print(f"  Agent: {session.agent_id}")
        console.print(f"  Messages: {session.message_count}")
        console.print(f"  Period: {session.period_start} to {session.period_end}")

        # Get agent config
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Loading agent config...", total=None)
            agent_config = await get_agent_config(
                agent_id=session.agent_id, letta_url=letta_url
            )

        if not agent_config.archive_id:
            console.print("  [red]ERROR: Agent has no archive attached, skipping[/red]")
            continue

        # Get message IDs from our database
        message_ids = await get_session_message_ids(session.id)
        console.print(f"  Retrieved {len(message_ids)} message IDs from database")

        # Get timestamps from Letta
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Fetching message timestamps from Letta...", total=None)
            messages_with_dates = await get_message_timestamps(
                agent_id=session.agent_id,
                message_ids=message_ids,
                letta_url=letta_url,
            )

        if len(messages_with_dates) != len(message_ids):
            console.print(
                f"  [yellow]WARNING: Only found {len(messages_with_dates)}/{len(message_ids)} "
                f"messages in Letta[/yellow]"
            )

        # Chunk into sessions
        detected = chunk_messages_into_sessions(messages_with_dates, gap_minutes)
        console.print(f"  [green]Detected {len(detected)} session(s) to create[/green]")

        # Display detected sessions
        session_table = Table(title="Detected Sessions", show_header=True)
        session_table.add_column("#", justify="right")
        session_table.add_column("Messages", justify="right")
        session_table.add_column("Start")
        session_table.add_column("End")
        session_table.add_column("Duration")

        for i, det in enumerate(detected, 1):
            session_table.add_row(
                str(i),
                str(det.message_count),
                det.period_start.strftime("%Y-%m-%d %H:%M:%S"),
                det.period_end.strftime("%Y-%m-%d %H:%M:%S"),
                str(det.duration),
            )

        console.print(session_table)

        if dry_run:
            console.print("\n  [yellow]DRY RUN - skipping actual changes[/yellow]")
            continue

        # Confirm before proceeding (skip if auto_yes)
        if not auto_yes and not Confirm.ask("\n  Proceed with recovery?", default=True):
            console.print("  [yellow]Skipped[/yellow]")
            continue

        # Delete the failed session
        console.print("  Deleting failed session record...")
        await delete_session_and_messages(session.id)

        # Create and process new sessions sequentially
        for i, det in enumerate(detected, 1):
            console.print(f"\n  [bold]Session {i}/{len(detected)}[/bold]")

            # Create session record
            new_session = await create_session(
                agent_id=session.agent_id,
                message_ids=det.message_ids,
                period_start=det.period_start,
                period_end=det.period_end,
            )
            console.print(f"    Created session {new_session.id[:8]}...")

            # Run summarization directly (not via queue)
            console.print("    Running summarization...")

            try:
                # Create a mock context (summarize_session expects it but doesn't use it much)
                result = await summarize_session(
                    {},  # type: ignore[arg-type]
                    session_id=new_session.id,
                    agent_id=session.agent_id,
                    letta_url=letta_url,
                    archive_id=agent_config.archive_id,
                )

                if result.get("status") == "ok":
                    summary_len = result.get("summary_length", 0)
                    passage_id = str(result.get("passage_id", "N/A"))[:8]
                    console.print(
                        f"    [green]SUCCESS[/green] - "
                        f"Summary: {summary_len} chars, "
                        f"Passage: {passage_id}..."
                    )
                else:
                    console.print(f"    [red]FAILED[/red] - {result}")

            except Exception as e:  # noqa: BLE001
                console.print(f"    [red]ERROR[/red] - {type(e).__name__}: {e}")
                # Session is already marked failed by summarize_session
                continue

    console.print("\n[bold green]Recovery complete![/bold green]")


async def status() -> None:
    """Show overall session status summary."""
    async with _async_session() as db:
        # Count by status
        result = await db.execute(
            select(Session.status, func.count(Session.id)).group_by(Session.status)
        )
        rows = result.all()
        status_counts: dict[str, Any] = {str(row[0]): row[1] for row in rows}

    table = Table(title="Session Status Summary")
    table.add_column("Status", style="bold")
    table.add_column("Count", justify="right")

    for status_val in ["pending", "summarized", "failed"]:
        count = status_counts.get(status_val, 0)
        style = {"pending": "yellow", "summarized": "green", "failed": "red"}.get(
            status_val, ""
        )
        table.add_row(status_val.upper(), f"[{style}]{count}[/{style}]")

    console.print(table)

    # Show failed sessions if any
    failed_count = status_counts.get("failed", 0)
    if failed_count > 0:
        console.print(
            f"\n[yellow]Run 'sessions-admin recover' to attempt recovery of "
            f"{failed_count} failed session(s)[/yellow]"
        )


async def main_async(args: list[str]) -> int:
    """Main async entry point."""
    if len(args) < 1:
        console.print("[bold]sessions-admin[/bold] - Session management CLI\n")
        console.print("Usage: sessions-admin <command> [options]\n")
        console.print("Commands:")
        console.print("  status          Show session status summary")
        console.print("  list-failed     List all failed sessions")
        console.print("  recover         Recover failed sessions (re-chunk and re-summarize)")
        console.print("  recover --dry   Preview recovery without making changes")
        console.print("  recover --yes   Skip confirmation prompts")
        return 1

    command = args[0]

    if command == "status":
        await status()
    elif command == "list-failed":
        await list_failed()
    elif command == "recover":
        dry_run = "--dry" in args or "--dry-run" in args
        auto_yes = "--yes" in args or "-y" in args
        await recover_sessions(dry_run=dry_run, auto_yes=auto_yes)
    else:
        console.print(f"[red]Unknown command: {command}[/red]")
        return 1

    return 0


def main() -> None:
    """CLI entry point."""
    sys.exit(asyncio.run(main_async(sys.argv[1:])))


if __name__ == "__main__":
    main()
