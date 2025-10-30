"""Main Textual application for the Kairix Notebook Viewer."""

import argparse
import sys
from pathlib import Path
from typing import Optional, Union

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Footer, Header

from .cache_reader import CacheValidationError, NotebookCache
from .widgets.explorer import ExplorerPane, NoteSelected
from .widgets.viewer import ViewerPane


class NotebookViewerApp(App):
    """A Textual app for viewing and editing kairix notebook entries."""

    CSS = """
    Screen {
        layout: vertical;
    }

    Header {
        dock: top;
    }

    Footer {
        dock: bottom;
    }

    #main-container {
        height: 1fr;
        layout: horizontal;
    }

    #explorer-pane {
        width: 30%;
        border-right: solid $primary;
        padding: 1;
    }

    #viewer-pane {
        width: 70%;
        padding: 1;
    }

    .explorer-header {
        background: $primary;
        color: $text;
        padding: 1;
        margin-bottom: 1;
        text-align: center;
    }

    .note-header {
        background: $surface;
        padding: 1;
        margin-bottom: 1;
        border: solid $primary;
    }

    .button-bar {
        layout: horizontal;
        height: auto;
        margin-bottom: 1;
    }

    Button {
        margin-right: 1;
    }

    ListView {
        height: 1fr;
    }

    ListItem {
        padding: 1;
    }

    ListItem > Static {
        width: 100%;
    }

    TextArea {
        height: 1fr;
    }

    Markdown {
        height: 1fr;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]

    def __init__(self, cache_path: Union[str, Path]):
        """Initialize the app.

        Args:
            cache_path: Path to the .cache directory
        """
        super().__init__()
        self.cache_path = Path(cache_path)
        self.cache: Optional[NotebookCache] = None
        self.explorer: Optional[ExplorerPane] = None
        self.viewer: Optional[ViewerPane] = None

    def compose(self) -> ComposeResult:
        """Compose the app layout."""
        yield Header()

        with Horizontal(id="main-container"):
            # Initialize cache
            try:
                self.cache = NotebookCache(self.cache_path)
            except CacheValidationError as e:
                self.exit(message=f"Error: {e}")
                return

            # Explorer pane (left)
            self.explorer = ExplorerPane(self.cache, id="explorer-pane")
            yield self.explorer

            # Viewer pane (right)
            self.viewer = ViewerPane(self.cache, id="viewer-pane")
            yield self.viewer

        yield Footer()

    def on_note_selected(self, message: NoteSelected) -> None:
        """Handle note selection from explorer.

        Args:
            message: Note selection message
        """
        if self.viewer:
            self.viewer.load_note(message.title)

    def action_refresh(self) -> None:
        """Refresh the note list."""
        if self.explorer:
            self.explorer.refresh_notes()

    def action_quit(self) -> None:
        """Quit the application."""
        if self.cache:
            self.cache.close()
        self.exit()

    def on_unmount(self) -> None:
        """Clean up when app unmounts."""
        if self.cache:
            self.cache.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Kairix Notebook Viewer - Browse and edit persona notebook entries"
    )
    parser.add_argument(
        "--cache-path",
        type=str,
        default="../.cache",
        help="Path to the .cache directory (default: ../cache relative to this directory)",
    )

    args = parser.parse_args()

    # Resolve cache path
    cache_path = Path(args.cache_path)
    if not cache_path.is_absolute():
        # Make relative to the diskcache-viewer directory
        app_dir = Path(__file__).parent.parent
        cache_path = (app_dir / cache_path).resolve()

    try:
        app = NotebookViewerApp(cache_path)
        app.run()
    except CacheValidationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
