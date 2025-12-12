"""Explorer widget for browsing notebook entries."""

from typing import Callable, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.message import Message
from textual.widgets import Label, ListItem, ListView, Static

from ..cache_reader import Note, NotebookCache


class NoteSelected(Message):
    """Message sent when a note is selected."""

    def __init__(self, title: str) -> None:
        """Initialize message.

        Args:
            title: The selected note title
        """
        self.title = title
        super().__init__()


class NoteListItem(ListItem):
    """A list item representing a notebook entry."""

    def __init__(self, title: str, note: Note, *args, **kwargs) -> None:
        """Initialize note list item.

        Args:
            title: Note title
            note: Note object with metadata
        """
        super().__init__(*args, **kwargs)
        self.note_title = title
        self.note = note

    def compose(self) -> ComposeResult:
        """Compose the list item."""
        # Create a rich text representation
        title_text = Text(self.note_title, style="bold cyan")

        # Add date info
        date_str = self.note.created_at.strftime("%Y-%m-%d")
        date_text = Text(f"  📅 {date_str}", style="dim")

        # Add tag count
        if self.note.tags:
            tags_text = Text(f"  🏷️  {len(self.note.tags)}", style="dim yellow")
        else:
            tags_text = Text("")

        yield Static(title_text)
        yield Static(date_text + tags_text)


class ExplorerPane(VerticalScroll):
    """Explorer pane showing list of notebook entries."""

    def __init__(self, cache: NotebookCache, *args, **kwargs) -> None:
        """Initialize explorer pane.

        Args:
            cache: NotebookCache instance to read from
        """
        super().__init__(*args, **kwargs)
        self.cache = cache
        self.list_view: Optional[ListView] = None

    def compose(self) -> ComposeResult:
        """Compose the explorer pane."""
        yield Label("📓 Notebook Entries", classes="explorer-header")
        self.list_view = ListView()
        yield self.list_view

    def on_mount(self) -> None:
        """Load notes when widget is mounted."""
        self.refresh_notes()

    def refresh_notes(self) -> None:
        """Refresh the list of notes from cache."""
        if self.list_view is None:
            return

        # Clear existing items
        self.list_view.clear()

        # Load all notes
        titles = self.cache.list_titles()

        # Sort by title (could add more sort options later)
        titles.sort()

        # Add list items
        for title in titles:
            note = self.cache.get_note(title)
            if note:
                item = NoteListItem(title, note)
                self.list_view.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle note selection.

        Args:
            event: Selection event
        """
        if isinstance(event.item, NoteListItem):
            # Post a message to notify the app
            self.post_message(NoteSelected(event.item.note_title))
