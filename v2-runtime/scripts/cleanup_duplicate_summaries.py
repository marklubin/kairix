#!/usr/bin/env python3
"""One-time cleanup script for duplicate session summaries in Letta archival memory.

This script finds and deletes duplicate session summaries created due to
the Letta messages.reset() API behavior where message_ids are cleared but
messages remain in the database.

Usage:
    # Dry run first (default)
    uv run python scripts/cleanup_duplicate_summaries.py --archive-id <archive_id>

    # Actually delete duplicates
    uv run python scripts/cleanup_duplicate_summaries.py --archive-id <archive_id> --execute

Environment:
    LETTA_BASE_URL: Letta server URL (default: http://localhost:8283)
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
from collections import defaultdict

from letta_client import AsyncLetta


async def cleanup_duplicate_summaries(
    archive_id: str,
    letta_url: str,
    dry_run: bool = True,
) -> dict[str, object]:
    """Find and delete duplicate session summaries from Letta archival memory.

    Strategy:
    1. List all passages with "[Session Summary:" prefix
    2. Group by (period_start, period_end) from the text
    3. For each group with >1 passage:
       - Keep the oldest (by created_at)
       - Delete the rest

    Args:
        archive_id: The Letta archive ID to clean up.
        letta_url: The Letta server URL.
        dry_run: If True, only report what would be deleted.

    Returns:
        Summary dict with counts and deleted passage IDs.
    """
    client = AsyncLetta(base_url=letta_url)

    # Search for session summaries (Letta API max is 100 results)
    print(f"Searching for session summaries in archive {archive_id}...")
    search_results = await client.passages.search(
        archive_id=archive_id,
        query="Session Summary",
        limit=100,
    )
    # Extract passage objects from search results
    all_passages = [r.passage for r in search_results]
    print(f"Found {len(all_passages)} passages matching 'Session Summary'")

    # Group by period
    by_period: dict[tuple[str, str], list[object]] = defaultdict(list)
    pattern = re.compile(r"\[Session Summary: (.+?) to (.+?)\]")

    for p in all_passages:
        match = pattern.search(p.text)
        if match:
            period_key = (match.group(1), match.group(2))
            by_period[period_key].append(p)

    print(f"\nGrouped into {len(by_period)} unique session periods")

    # Find duplicates
    to_delete = []
    kept = []

    for period, passages_in_period in by_period.items():
        if len(passages_in_period) > 1:
            # Sort by created_at, keep oldest
            sorted_passages = sorted(passages_in_period, key=lambda p: p.created_at)
            kept.append(sorted_passages[0])
            to_delete.extend(sorted_passages[1:])
            print(
                f"\nPeriod {period[0]} to {period[1]}:"
                f"\n  {len(passages_in_period)} copies found"
                f"\n  Keeping: {sorted_passages[0].id} (created {sorted_passages[0].created_at})"
                f"\n  Deleting: {len(sorted_passages) - 1} duplicates"
            )
        else:
            kept.append(passages_in_period[0])

    print(f"\n{'=' * 60}")
    print(f"Total passages to keep: {len(kept)}")
    print(f"Total duplicates to delete: {len(to_delete)}")
    print(f"{'=' * 60}")

    if not to_delete:
        print("\nNo duplicates found. Nothing to clean up.")
        return {
            "status": "ok",
            "duplicates_found": 0,
            "deleted": [],
        }

    if dry_run:
        print("\n[DRY RUN] Would delete the following passages:")
        for p in to_delete:
            preview = p.text[:100].replace("\n", " ")
            print(f"  - {p.id}: {preview}...")
        print("\nRun with --execute to actually delete these passages.")
        return {
            "status": "dry_run",
            "duplicates_found": len(to_delete),
            "would_delete": [p.id for p in to_delete],
        }

    # Actually delete duplicates using the archives.passages.delete endpoint
    print("\nDeleting duplicates...")
    deleted = []
    for p in to_delete:
        try:
            await client.archives.passages.delete(
                archive_id=archive_id,
                passage_id=p.id,
            )
            deleted.append(p.id)
            preview = p.text[:60].replace("\n", " ")
            print(f"  Deleted: {p.id} - {preview}...")
        except Exception as e:
            print(f"  Failed to delete {p.id}: {e}")

    print(f"\nSuccessfully deleted {len(deleted)} duplicate passages.")

    return {
        "status": "ok",
        "duplicates_found": len(to_delete),
        "deleted": deleted,
    }


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Clean up duplicate session summaries from Letta archival memory."
    )
    parser.add_argument(
        "--archive-id",
        required=True,
        help="The Letta archive ID to clean up",
    )
    parser.add_argument(
        "--letta-url",
        default=os.environ.get("LETTA_BASE_URL", "http://localhost:8283"),
        help="Letta server URL (default: LETTA_BASE_URL env var or localhost:8283)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete duplicates (default is dry run)",
    )

    args = parser.parse_args()

    result = asyncio.run(
        cleanup_duplicate_summaries(
            archive_id=args.archive_id,
            letta_url=args.letta_url,
            dry_run=not args.execute,
        )
    )

    print(f"\nResult: {result}")


if __name__ == "__main__":
    main()
