"""Cache reader for kairix persona notebook entries."""

import pickle
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from diskcache import Index


@dataclass
class Note:
    """Note data model matching kairix Note class."""

    title: str
    created_at: datetime
    modified_at: Optional[datetime]
    content: str
    tags: set[str]

    def __str__(self) -> str:
        """String representation of note."""
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"Note(title='{self.title}', content='{content_preview}', tags={self.tags})"


class _CacheNote:
    """Simple Note class for cache storage (matches kairix structure)."""

    def __init__(self, title: str, created_at: datetime, modified_at: Optional[datetime], content: str, tags: set[str]):
        self.title = title
        self.created_at = created_at
        self.modified_at = modified_at
        self.content = content
        self.tags = tags


class CacheValidationError(Exception):
    """Raised when cache structure is invalid."""

    pass


class NotebookCache:
    """Reader/writer for kairix persona notebook cache."""

    def __init__(self, cache_path: Union[str, Path]):
        """Initialize notebook cache reader.

        Args:
            cache_path: Path to the .cache directory

        Raises:
            CacheValidationError: If cache structure is invalid
        """
        self.cache_path = Path(cache_path)
        self._validate_cache_structure()
        self.notebook_path = self.cache_path / "index" / "persona_notebook"
        self._index: Optional[Index] = None

    def _validate_cache_structure(self) -> None:
        """Validate that this is a valid kairix cache directory.

        Raises:
            CacheValidationError: If structure is invalid
        """
        if not self.cache_path.exists():
            raise CacheValidationError(f"Cache path does not exist: {self.cache_path}")

        if not self.cache_path.is_dir():
            raise CacheValidationError(f"Cache path is not a directory: {self.cache_path}")

        # Check for index directory
        index_dir = self.cache_path / "index"
        if not index_dir.exists():
            raise CacheValidationError(
                f"No 'index' directory found in cache. "
                f"This does not appear to be a valid kairix cache: {self.cache_path}"
            )

        # Check for persona_notebook subdirectory
        notebook_dir = index_dir / "persona_notebook"
        if not notebook_dir.exists():
            raise CacheValidationError(
                f"No 'persona_notebook' index found. "
                f"This cache does not contain notebook data: {self.cache_path}"
            )

        # Check for cache.db file
        db_file = notebook_dir / "cache.db"
        if not db_file.exists():
            raise CacheValidationError(
                f"No cache.db file found in persona_notebook: {notebook_dir}"
            )

    @property
    def index(self) -> Index:
        """Get the diskcache Index for persona_notebook."""
        if self._index is None:
            self._index = Index(str(self.notebook_path))
        return self._index

    def list_titles(self) -> list[str]:
        """List all note titles in the notebook.

        Returns:
            List of note titles (excluding special keys)
        """
        # Filter out special keys like __agent_unconditional_context__
        return [title for title in self.index if not title.startswith("__")]

    def get_note(self, title: str) -> Optional[Note]:
        """Get a note by title.

        Args:
            title: The note title

        Returns:
            Note object if found, None otherwise
        """
        if title not in self.index:
            return None

        note_obj = self.index[title]

        # Handle both the kairix Note class and our dataclass
        if hasattr(note_obj, "__dict__"):
            return Note(
                title=note_obj.title,
                created_at=note_obj.created_at,
                modified_at=note_obj.modified_at,
                content=note_obj.content,
                tags=note_obj.tags,
            )
        else:
            # Already a dict or dataclass
            return note_obj

    def save_note(self, note: Note) -> None:
        """Save a note to the cache.

        Args:
            note: Note object to save
        """
        # Create a simple object that matches the kairix Note structure
        note_obj = _CacheNote(
            title=note.title,
            created_at=note.created_at,
            modified_at=note.modified_at if note.modified_at else datetime.now(),
            content=note.content,
            tags=note.tags,
        )

        self.index[note.title] = note_obj

    def delete_note(self, title: str) -> bool:
        """Delete a note from the cache.

        Args:
            title: The note title to delete

        Returns:
            True if deleted, False if not found
        """
        if title in self.index:
            del self.index[title]
            return True
        return False

    def search_by_tag(self, tag: str) -> list[str]:
        """Find all note titles that have the specified tag.

        Args:
            tag: Tag to search for

        Returns:
            List of note titles with the tag
        """
        matching_titles = []
        for title in self.list_titles():
            note = self.get_note(title)
            if note and tag in note.tags:
                matching_titles.append(title)
        return matching_titles

    def close(self) -> None:
        """Close the cache index."""
        if self._index is not None:
            # Index doesn't have a close method, just set to None
            # The underlying cache will be closed when Python gc runs
            self._index = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
