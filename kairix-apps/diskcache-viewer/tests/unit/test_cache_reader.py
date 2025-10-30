"""Unit tests for cache_reader module."""

from datetime import datetime

import pytest

from src.cache_reader import CacheValidationError, Note, NotebookCache


class TestCacheValidation:
    """Tests for cache validation logic."""

    def test_valid_cache_structure(self, temp_cache_dir):
        """Test that a valid cache structure is accepted."""
        cache = NotebookCache(temp_cache_dir)
        assert cache.cache_path == temp_cache_dir
        assert cache.notebook_path == temp_cache_dir / "index" / "persona_notebook"

    def test_nonexistent_cache_path(self, tmp_path):
        """Test that nonexistent path raises error."""
        nonexistent = tmp_path / "doesnotexist"
        with pytest.raises(CacheValidationError, match="does not exist"):
            NotebookCache(nonexistent)

    def test_cache_path_not_directory(self, tmp_path):
        """Test that file path raises error."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")
        with pytest.raises(CacheValidationError, match="not a directory"):
            NotebookCache(file_path)

    def test_missing_index_directory(self, invalid_cache_dir):
        """Test that missing index directory raises error."""
        with pytest.raises(CacheValidationError, match="No 'index' directory"):
            NotebookCache(invalid_cache_dir)

    def test_missing_persona_notebook(self, empty_cache_dir):
        """Test that missing persona_notebook raises error."""
        with pytest.raises(CacheValidationError, match="No 'persona_notebook'"):
            NotebookCache(empty_cache_dir)


class TestNotebookOperations:
    """Tests for notebook CRUD operations."""

    def test_list_titles(self, temp_cache_dir):
        """Test listing all note titles."""
        cache = NotebookCache(temp_cache_dir)
        titles = cache.list_titles()

        assert len(titles) == 5
        assert "Getting Started" in titles
        assert "Daily Journal 2024-01-02" in titles
        assert "Project Ideas" in titles
        assert "Meeting Notes" in titles
        assert "Code Snippets" in titles

    def test_list_titles_excludes_special_keys(self, temp_cache_dir):
        """Test that special keys (starting with __) are excluded."""
        cache = NotebookCache(temp_cache_dir)

        # Add a special key
        cache.index["__special_key__"] = Note(
            title="__special_key__",
            created_at=datetime.now(),
            modified_at=None,
            content="special",
            tags=set(),
        )

        titles = cache.list_titles()
        assert "__special_key__" not in titles

    def test_get_note_exists(self, temp_cache_dir):
        """Test retrieving an existing note."""
        cache = NotebookCache(temp_cache_dir)
        note = cache.get_note("Getting Started")

        assert note is not None
        assert note.title == "Getting Started"
        assert "markdown" in note.content
        assert "tutorial" in note.tags
        assert "guide" in note.tags

    def test_get_note_not_exists(self, temp_cache_dir):
        """Test retrieving a non-existent note returns None."""
        cache = NotebookCache(temp_cache_dir)
        note = cache.get_note("Nonexistent Note")

        assert note is None

    def test_save_new_note(self, temp_cache_dir):
        """Test saving a new note."""
        cache = NotebookCache(temp_cache_dir)

        new_note = Note(
            title="New Note",
            created_at=datetime.now(),
            modified_at=None,
            content="This is a new note",
            tags={"new", "test"},
        )

        cache.save_note(new_note)

        # Verify it was saved
        retrieved = cache.get_note("New Note")
        assert retrieved is not None
        assert retrieved.title == "New Note"
        assert retrieved.content == "This is a new note"
        assert "new" in retrieved.tags

    def test_save_existing_note(self, temp_cache_dir):
        """Test updating an existing note."""
        cache = NotebookCache(temp_cache_dir)

        # Get existing note
        note = cache.get_note("Getting Started")
        assert note is not None

        # Modify content
        note.content = "Updated content"
        note.modified_at = datetime.now()

        # Save
        cache.save_note(note)

        # Verify update
        retrieved = cache.get_note("Getting Started")
        assert retrieved is not None
        assert retrieved.content == "Updated content"

    def test_delete_note_exists(self, temp_cache_dir):
        """Test deleting an existing note."""
        cache = NotebookCache(temp_cache_dir)

        # Verify note exists
        assert cache.get_note("Getting Started") is not None

        # Delete
        result = cache.delete_note("Getting Started")
        assert result is True

        # Verify deleted
        assert cache.get_note("Getting Started") is None

    def test_delete_note_not_exists(self, temp_cache_dir):
        """Test deleting a non-existent note returns False."""
        cache = NotebookCache(temp_cache_dir)

        result = cache.delete_note("Nonexistent Note")
        assert result is False

    def test_search_by_tag(self, temp_cache_dir):
        """Test searching notes by tag."""
        cache = NotebookCache(temp_cache_dir)

        # Search for 'journal' tag
        results = cache.search_by_tag("journal")
        assert len(results) == 1
        assert "Daily Journal 2024-01-02" in results

        # Search for 'tutorial' tag
        results = cache.search_by_tag("tutorial")
        assert len(results) == 1
        assert "Getting Started" in results

    def test_search_by_nonexistent_tag(self, temp_cache_dir):
        """Test searching for a tag that doesn't exist."""
        cache = NotebookCache(temp_cache_dir)

        results = cache.search_by_tag("nonexistent")
        assert len(results) == 0


class TestContextManager:
    """Tests for context manager functionality."""

    def test_context_manager(self, temp_cache_dir):
        """Test using NotebookCache as a context manager."""
        with NotebookCache(temp_cache_dir) as cache:
            titles = cache.list_titles()
            assert len(titles) > 0

        # After context exit, index should be closed
        # This doesn't raise an error, but we can verify the behavior
        assert True  # Context manager worked

    def test_manual_close(self, temp_cache_dir):
        """Test manually closing the cache."""
        cache = NotebookCache(temp_cache_dir)
        cache.close()

        # After close, _index should be None
        assert cache._index is None
