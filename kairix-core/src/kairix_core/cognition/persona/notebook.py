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

# Initialize the notebook cache at module level
logger.info("[AGENT_NOTEBOOK] Initializing persona notebook.")
_notebook: Index = CacheRuntime().persona_notebook


@function_tool
def list_titles() -> list[str]:
    """List all note titles in the notebook."""
    logger.info("[AGENT_NOTEBOOK] Persona listed titles.")
    return [t for t in _notebook]


@function_tool
def get_note(title: str) -> Note:
    """Get a note by title, raises KeyError if not found."""
    logger.info(f"[AGENT_NOTEBOOK] Persona getting note: {title}")
    if title not in _notebook:
        raise KeyError(f"Note with title '{title}' not found")
    result = _notebook[title]
    return result


@function_tool
def maybe_note(title: str) -> Optional[Note]:
    """Get a note by title, returns None if not found."""
    logger.info(f"[AGENT_NOTEBOOK] Persona trying to get note: {title}")
    return _notebook.get(title, None)


@function_tool
def get_note_content(title: str) -> str:
    """Get just the content of a note by title."""
    logger.info(f"[AGENT_NOTEBOOK] Persona getting note content: {title}")
    if title not in _notebook:
        raise KeyError(f"Note with title '{title}' not found")
    return _notebook[title].content


@function_tool
def save(title: str, content: str, tags: Optional[set[str]] = None) -> str:
    """Save a note with given title, content, and tags."""
    logger.info(f"[AGENT_NOTEBOOK] Persona saving to notebook: {title}")
    tags = tags or set()

    if title in _notebook:
        logger.info("[AGENT_NOTEBOOK] Found existing title, amending.")
        note = _notebook[title]
        note.content = content
        note.tags.update(tags)
        note.modified_at = datetime.now()
        action = "updated"
    else:
        logger.info("[AGENT_NOTEBOOK] Creating new note.")
        note = Note(
            title=title,
            created_at=datetime.now(),
            modified_at=None,
            content=content,
            tags=tags
        )
        _notebook[title] = note
        action = "created"

    logger.info(f"[AGENT_NOTEBOOK] Saved note for {title}, Note was:\n {note}")
    return f"Successfully {action} note '{title}'"


@function_tool
def search_by_tag(tag: str) -> list[str]:
    """Find all note titles that have the specified tag."""
    logger.info(f"[AGENT_NOTEBOOK] Persona searching by tag: {tag}")
    matching_titles = []
    for title, note in _notebook.items():
        if tag in note.tags:
            matching_titles.append(title)
    return matching_titles
