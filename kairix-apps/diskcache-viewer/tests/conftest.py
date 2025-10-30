"""Shared pytest fixtures for tests."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from diskcache import FanoutCache, Index


class _Note:
    """Simple Note class for testing (matches kairix structure)."""

    def __init__(self, title: str, created_at: datetime, modified_at, content: str, tags: set[str]):
        self.title = title
        self.created_at = created_at
        self.modified_at = modified_at
        self.content = content
        self.tags = tags


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create a temporary cache directory structure.

    Returns:
        Path to the temporary .cache directory
    """
    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()

    # Create the FanoutCache structure
    fanout_cache = FanoutCache(str(cache_dir))

    # Create the persona_notebook index
    notebook_index = fanout_cache.index("persona_notebook")

    # Add some test notes
    test_notes = [
        _Note(
            title="Getting Started",
            created_at=datetime(2024, 1, 1, 10, 0, 0),
            modified_at=None,
            content="# Getting Started\n\nThis is a **test note** with *markdown*.\n\n- Item 1\n- Item 2\n- Item 3",
            tags={"tutorial", "guide"},
        ),
        _Note(
            title="Daily Journal 2024-01-02",
            created_at=datetime(2024, 1, 2, 9, 0, 0),
            modified_at=datetime(2024, 1, 2, 18, 30, 0),
            content="# Daily Journal\n\nToday was productive.\n\n## Tasks Completed\n- Task A\n- Task B",
            tags={"journal", "daily"},
        ),
        _Note(
            title="Project Ideas",
            created_at=datetime(2024, 1, 3, 14, 0, 0),
            modified_at=None,
            content="# Project Ideas\n\n1. Build a TUI app\n2. Create a note viewer\n3. Integrate with AI",
            tags={"ideas", "projects"},
        ),
        _Note(
            title="Meeting Notes",
            created_at=datetime(2024, 1, 4, 11, 0, 0),
            modified_at=datetime(2024, 1, 4, 12, 0, 0),
            content="# Meeting Notes\n\n**Date:** 2024-01-04\n**Attendees:** Alice, Bob\n\n## Discussion\n- Topic 1\n- Topic 2",
            tags={"meetings", "work"},
        ),
        _Note(
            title="Code Snippets",
            created_at=datetime(2024, 1, 5, 16, 0, 0),
            modified_at=None,
            content="# Code Snippets\n\n```python\ndef hello():\n    print('Hello, world!')\n```",
            tags={"code", "reference"},
        ),
    ]

    for note in test_notes:
        notebook_index[note.title] = note

    # Close the cache
    fanout_cache.close()

    return cache_dir


@pytest.fixture
def invalid_cache_dir(tmp_path):
    """Create an invalid cache directory for testing error handling.

    Returns:
        Path to an invalid cache directory
    """
    cache_dir = tmp_path / ".invalid_cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def empty_cache_dir(tmp_path):
    """Create an empty cache directory with no notebook index.

    Returns:
        Path to an empty cache directory
    """
    cache_dir = tmp_path / ".empty_cache"
    cache_dir.mkdir()

    # Create index directory but no persona_notebook
    index_dir = cache_dir / "index"
    index_dir.mkdir()

    return cache_dir
