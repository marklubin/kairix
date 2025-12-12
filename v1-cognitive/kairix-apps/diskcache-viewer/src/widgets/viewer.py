"""Viewer/editor widget for displaying and editing notes."""

from datetime import datetime
from typing import Optional

from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Button, Label, Markdown as MarkdownWidget, Static, TextArea

from ..cache_reader import Note, NotebookCache


class ViewerPane(Vertical):
    """Viewer pane for displaying and editing notes."""

    def __init__(self, cache: NotebookCache, *args, **kwargs) -> None:
        """Initialize viewer pane.

        Args:
            cache: NotebookCache instance
        """
        super().__init__(*args, **kwargs)
        self.cache = cache
        self.current_note: Optional[Note] = None
        self.edit_mode = False

        # Widgets
        self.header: Optional[Static] = None
        self.markdown_viewer: Optional[MarkdownWidget] = None
        self.text_editor: Optional[TextArea] = None
        self.button_container: Optional[Container] = None

    def compose(self) -> ComposeResult:
        """Compose the viewer pane."""
        # Header showing note metadata
        self.header = Static("", classes="note-header")
        yield self.header

        # Buttons for actions
        with Container(classes="button-bar"):
            yield Button("Edit", id="edit-btn", variant="primary")
            yield Button("View", id="view-btn", variant="default")
            yield Button("Save", id="save-btn", variant="success")

        # Markdown viewer (shown in view mode)
        self.markdown_viewer = MarkdownWidget("*Select a note from the list*")
        yield self.markdown_viewer

        # Text editor (shown in edit mode)
        self.text_editor = TextArea("", language="markdown")
        self.text_editor.display = False
        yield self.text_editor

    def load_note(self, title: str) -> None:
        """Load a note by title.

        Args:
            title: Note title to load
        """
        note = self.cache.get_note(title)
        if note is None:
            self._show_error(f"Note '{title}' not found")
            return

        self.current_note = note
        self.edit_mode = False
        self._update_display()

    def _update_display(self) -> None:
        """Update the display based on current note and mode."""
        if self.current_note is None:
            return

        # Update header
        if self.header:
            header_text = self._format_header()
            self.header.update(header_text)

        # Update content display based on mode
        if self.edit_mode:
            self._show_edit_mode()
        else:
            self._show_view_mode()

    def _format_header(self) -> Text:
        """Format the note header with metadata.

        Returns:
            Rich Text object with formatted header
        """
        if self.current_note is None:
            return Text("")

        header = Text()
        header.append("📝 ", style="bold")
        header.append(self.current_note.title, style="bold cyan")
        header.append("\n")

        # Created date
        created_str = self.current_note.created_at.strftime("%Y-%m-%d %H:%M")
        header.append(f"Created: {created_str}", style="dim")

        # Modified date if exists
        if self.current_note.modified_at:
            modified_str = self.current_note.modified_at.strftime("%Y-%m-%d %H:%M")
            header.append(f" | Modified: {modified_str}", style="dim")

        # Tags
        if self.current_note.tags:
            header.append("\n🏷️  ", style="dim")
            header.append(", ".join(sorted(self.current_note.tags)), style="yellow")

        return header

    def _show_view_mode(self) -> None:
        """Show note in view mode (rendered markdown)."""
        if self.markdown_viewer and self.text_editor and self.current_note:
            self.markdown_viewer.display = True
            self.text_editor.display = False

            # Update markdown content
            try:
                self.markdown_viewer.update(self.current_note.content)
            except Exception as e:
                # Fallback to plain text if markdown rendering fails
                self.markdown_viewer.update(f"```\n{self.current_note.content}\n```")

    def _show_edit_mode(self) -> None:
        """Show note in edit mode (text editor)."""
        if self.markdown_viewer and self.text_editor and self.current_note:
            self.markdown_viewer.display = False
            self.text_editor.display = True

            # Load content into editor
            self.text_editor.load_text(self.current_note.content)

    def _save_note(self) -> None:
        """Save the current note."""
        if self.current_note is None or self.text_editor is None:
            return

        # Get content from editor
        new_content = self.text_editor.text

        # Update note
        self.current_note.content = new_content
        self.current_note.modified_at = datetime.now()

        # Save to cache
        try:
            self.cache.save_note(self.current_note)
            self._show_view_mode()
            self.edit_mode = False
            self._update_display()
        except Exception as e:
            self._show_error(f"Error saving note: {e}")

    def _show_error(self, message: str) -> None:
        """Show an error message.

        Args:
            message: Error message to display
        """
        if self.markdown_viewer:
            self.markdown_viewer.display = True
            if self.text_editor:
                self.text_editor.display = False
            error_text = f"## ❌ Error\n\n{message}"
            self.markdown_viewer.update(error_text)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses.

        Args:
            event: Button press event
        """
        button_id = event.button.id

        if button_id == "edit-btn":
            self.edit_mode = True
            self._update_display()
        elif button_id == "view-btn":
            self.edit_mode = False
            self._update_display()
        elif button_id == "save-btn":
            self._save_note()
