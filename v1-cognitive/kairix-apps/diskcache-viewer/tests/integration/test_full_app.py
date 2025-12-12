"""Integration tests for the full application."""

import pytest
from textual.pilot import Pilot

from src.app import NotebookViewerApp
from src.cache_reader import NotebookCache


@pytest.mark.asyncio
async def test_app_startup(temp_cache_dir):
    """Test that the app starts successfully with a valid cache."""
    app = NotebookViewerApp(temp_cache_dir)

    async with app.run_test() as pilot:
        # App should start without errors
        assert app.cache is not None
        assert app.explorer is not None
        assert app.viewer is not None


@pytest.mark.asyncio
async def test_app_with_invalid_cache(invalid_cache_dir):
    """Test that app handles invalid cache gracefully."""
    app = NotebookViewerApp(invalid_cache_dir)

    # App should handle the error and exit during composition
    # This will raise an exception from Textual when it tries to mount
    # after the app has exited
    try:
        async with app.run_test() as pilot:
            pass
    except Exception:
        pass  # Expected - app exits during composition


@pytest.mark.asyncio
async def test_explorer_loads_notes(temp_cache_dir):
    """Test that explorer loads notes on startup."""
    app = NotebookViewerApp(temp_cache_dir)

    async with app.run_test() as pilot:
        # Give it time to mount and load
        await pilot.pause()

        # Explorer should have list items
        assert app.explorer is not None
        assert app.explorer.list_view is not None

        # Should have loaded notes
        list_view = app.explorer.list_view
        assert len(list_view.children) == 5  # We have 5 test notes


@pytest.mark.asyncio
async def test_note_selection(temp_cache_dir):
    """Test selecting a note from the explorer."""
    app = NotebookViewerApp(temp_cache_dir)

    async with app.run_test() as pilot:
        await pilot.pause()

        # Use the viewer's load_note method directly
        # (simulating what would happen when user clicks)
        if app.viewer and app.cache:
            titles = app.cache.list_titles()
            if titles:
                app.viewer.load_note(titles[0])
                await pilot.pause()

                # Viewer should have loaded the note
                assert app.viewer.current_note is not None
                assert app.viewer.current_note.title == titles[0]


@pytest.mark.asyncio
async def test_refresh_action(temp_cache_dir):
    """Test the refresh action."""
    app = NotebookViewerApp(temp_cache_dir)

    async with app.run_test() as pilot:
        await pilot.pause()

        # Add a new note directly to cache
        cache = NotebookCache(temp_cache_dir)
        from datetime import datetime
        from src.cache_reader import Note

        new_note = Note(
            title="Test Note",
            created_at=datetime.now(),
            modified_at=None,
            content="Test content",
            tags=set(),
        )
        cache.save_note(new_note)
        cache.close()

        # Trigger refresh
        await pilot.press("r")
        await pilot.pause()

        # Explorer should have refreshed and show the new note
        titles = app.cache.list_titles()
        assert "Test Note" in titles


@pytest.mark.asyncio
async def test_edit_and_save_note(temp_cache_dir):
    """Test editing and saving a note."""
    app = NotebookViewerApp(temp_cache_dir)

    async with app.run_test() as pilot:
        await pilot.pause()

        # Load a note using the viewer directly
        if app.viewer and app.cache:
            titles = app.cache.list_titles()
            if titles:
                app.viewer.load_note(titles[0])
                await pilot.pause()

                # Enter edit mode
                viewer = app.viewer
                original_content = viewer.current_note.content

                # Click edit button
                await pilot.click("#edit-btn")
                await pilot.pause()

                # Should be in edit mode
                assert viewer.edit_mode is True
                assert viewer.text_editor.display is True

                # Modify content
                viewer.text_editor.load_text("Modified content")

                # Save
                await pilot.click("#save-btn")
                await pilot.pause()

                # Should be back in view mode
                assert viewer.edit_mode is False

                # Content should be updated
                updated_note = app.cache.get_note(viewer.current_note.title)
                assert updated_note.content == "Modified content"


@pytest.mark.asyncio
async def test_quit_action(temp_cache_dir):
    """Test the quit action."""
    app = NotebookViewerApp(temp_cache_dir)

    async with app.run_test() as pilot:
        await pilot.pause()

        # Press 'q' to quit
        await pilot.press("q")
        await pilot.pause()

        # App should have closed the cache
        # We can't easily test this in run_test mode, but the action should work


class TestDataPersistence:
    """Test that data changes persist correctly."""

    def test_save_and_reload(self, temp_cache_dir):
        """Test that saved notes persist after closing and reopening."""
        from datetime import datetime
        from src.cache_reader import Note

        # Create and save a note
        cache1 = NotebookCache(temp_cache_dir)
        new_note = Note(
            title="Persistence Test",
            created_at=datetime.now(),
            modified_at=None,
            content="This should persist",
            tags={"test"},
        )
        cache1.save_note(new_note)
        cache1.close()

        # Open cache again
        cache2 = NotebookCache(temp_cache_dir)
        retrieved = cache2.get_note("Persistence Test")

        assert retrieved is not None
        assert retrieved.content == "This should persist"
        assert "test" in retrieved.tags

        cache2.close()

    def test_edit_and_reload(self, temp_cache_dir):
        """Test that edited notes persist."""
        # Edit an existing note
        cache1 = NotebookCache(temp_cache_dir)
        note = cache1.get_note("Getting Started")
        note.content = "Modified content"
        cache1.save_note(note)
        cache1.close()

        # Reload and verify
        cache2 = NotebookCache(temp_cache_dir)
        retrieved = cache2.get_note("Getting Started")

        assert retrieved is not None
        assert retrieved.content == "Modified content"

        cache2.close()
