from datetime import datetime
from typing import Optional

from agents import function_tool
from diskcache import Index

from kairix_core.runtime.cache import CacheRuntime
from kairix_core.runtime.logging import LoggingRuntime

logger = LoggingRuntime().logger

class Note:
    def __init__(self, title: str, created_at: datetime, modified_at: Optional[datetime], content: str, tags: set[str]):
        self.title = title
        self.created_at = created_at
        self.modified_at = modified_at
        self.content = content
        self.tags = tags

    def __str__(self):
        return f"Note(title='{self.title}', content='{self.content[:50]}...', tags={self.tags})"

class Notebook:

    def __init__(self):
        logger.info("[AGENT_NOTEBOOK]initializing persona notebook.")
        self.notebook: Index = CacheRuntime().persona_notebook

    @function_tool
    def list_titles(self) -> list[str]:
        """List all note titles in the notebook."""
        logger.info("[AGENT_NOTEBOOK] Persona listed titles.")
        return [t for t in self.notebook]

    @function_tool
    def get_note(self, title: str) -> Note:
        """Get a note by title, raises KeyError if not found."""
        logger.info(f"Persona getting note: {title}")
        if title not in self.notebook:
            raise KeyError(f"Note with title '{title}' not found")
        result = self.notebook[title]
        return result

    @function_tool
    def maybe_note(self, title: str) -> Optional[Note]:
        """Get a note by title, returns None if not found."""
        logger.info(f"[AGENT_NOTEBOOK] Persona trying to get note: {title}")
        return self.notebook.get(title, None)

    @function_tool
    def get_note_content(self, title: str) -> str:
        """Get just the content of a note by title."""
        logger.info(f"Persona getting note content: {title}")
        if title not in self.notebook:
            raise KeyError(f"Note with title '{title}' not found")
        return self.notebook[title].content

    @function_tool
    def save(self, title: str, content: str, tags: Optional[set[str]] = None) -> None:
        """Save a note with given title, content, and tags."""
        logger.info(f"[AGENT_NOTEBOOK] Persona saving to notebook: {title}")
        tags = tags or set()

        if title in self.notebook:
            logger.info("[AGENT_NOTEBOOK] Found existing title, amending.")
            note = self.notebook[title]
            note.content = content
            note.tags.update(tags)  # Fixed: use update() to modify in place
            note.modified_at = datetime.now()
        else:
            logger.info("[AGENT_NOTEBOOK] Creating new note.")
            note = Note(
                title=title,
                created_at=datetime.now(),
                modified_at=None,
                content=content,
                tags=tags
            )
            self.notebook[title] = note  # Fixed: Actually save the new note!

        logger.info(f"[AGENT_NOTEBOOK] Saved note for {title}, Note was:\n {note}")



    @function_tool
    def search_by_tag(self, tag: str) -> list[str]:
        """Find all note titles that have the specified tag."""
        logger.info(f"[AGENT_NOTEBOOK] Persona searching by tag: {tag}")
        matching_titles = []
        for title, note in self.notebook.items():
            if tag in note.tags:
                matching_titles.append(title)
        return matching_titles

