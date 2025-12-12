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

# Special key for the unconditional context note (hidden from normal search/list operations)
_UNCONDITIONAL_CONTEXT_KEY = "__agent_unconditional_context__"


@function_tool
def list_titles() -> list[str]:
    """List all note titles in the notebook."""
    logger.info("[AGENT_NOTEBOOK] Persona listed titles.")
    return [t for t in _notebook if t != _UNCONDITIONAL_CONTEXT_KEY]


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
        if title != _UNCONDITIONAL_CONTEXT_KEY and tag in note.tags:
            matching_titles.append(title)
    return matching_titles


# ===== Agent Unconditional Context Functions =====

@function_tool
def get_unconditional_context() -> str:
    """Get the current Agent Unconditional Context note content.

    This is a special note that contains key details about your persona, interaction style,
    and important context that should persist across conversations. This content is always
    included in your system prompt automatically.
    """
    logger.info("[AGENT_NOTEBOOK] Persona reading unconditional context")
    if _UNCONDITIONAL_CONTEXT_KEY in _notebook:
        return _notebook[_UNCONDITIONAL_CONTEXT_KEY].content
    return ""


@function_tool
def update_unconditional_context(content: str) -> str:
    """Replace the Agent Unconditional Context note with new content.

    Use this to completely rewrite your unconditional context. This content will always
    be included in your system prompt and should contain key details about your persona,
    communication style, and important ongoing context.

    Args:
        content: The new complete content for the unconditional context

    Returns:
        Confirmation message
    """
    logger.info("[AGENT_NOTEBOOK] Persona updating unconditional context")

    if _UNCONDITIONAL_CONTEXT_KEY in _notebook:
        note = _notebook[_UNCONDITIONAL_CONTEXT_KEY]
        note.content = content
        note.modified_at = datetime.now()
        _notebook[_UNCONDITIONAL_CONTEXT_KEY] = note  # Save back to notebook
    else:
        note = Note(
            title=_UNCONDITIONAL_CONTEXT_KEY,
            created_at=datetime.now(),
            modified_at=None,
            content=content,
            tags={"system", "unconditional"}
        )
        _notebook[_UNCONDITIONAL_CONTEXT_KEY] = note

    logger.info(f"[AGENT_NOTEBOOK] Updated unconditional context ({len(content)} chars)")
    return f"Successfully updated unconditional context ({len(content)} characters)"


@function_tool
def append_unconditional_context(additional_content: str) -> str:
    """Append content to the Agent Unconditional Context note.

    Use this to add new information to your existing unconditional context without
    losing what's already there. Content will be appended with proper spacing.

    Args:
        additional_content: Content to append to the unconditional context

    Returns:
        Confirmation message
    """
    logger.info("[AGENT_NOTEBOOK] Persona appending to unconditional context")

    # Get current content directly from notebook
    if _UNCONDITIONAL_CONTEXT_KEY in _notebook:
        current_content = _notebook[_UNCONDITIONAL_CONTEXT_KEY].content
    else:
        current_content = ""

    if current_content:
        new_content = current_content + "\n\n" + additional_content
    else:
        new_content = additional_content

    if _UNCONDITIONAL_CONTEXT_KEY in _notebook:
        note = _notebook[_UNCONDITIONAL_CONTEXT_KEY]
        note.content = new_content
        note.modified_at = datetime.now()
        _notebook[_UNCONDITIONAL_CONTEXT_KEY] = note  # Save back to notebook
    else:
        note = Note(
            title=_UNCONDITIONAL_CONTEXT_KEY,
            created_at=datetime.now(),
            modified_at=None,
            content=new_content,
            tags={"system", "unconditional"}
        )
        _notebook[_UNCONDITIONAL_CONTEXT_KEY] = note

    logger.info(f"[AGENT_NOTEBOOK] Appended to unconditional context (now {len(new_content)} chars)")
    return f"Successfully appended to unconditional context (now {len(new_content)} characters)"


def load_unconditional_context_for_system_prompt() -> str:
    """Internal function to load unconditional context for system prompt injection.

    This is not exposed as a tool - it's called by the engine to inject the context
    into the system prompt automatically.

    Returns:
        The unconditional context content, or empty string if not set
    """
    if _UNCONDITIONAL_CONTEXT_KEY in _notebook:
        content = _notebook[_UNCONDITIONAL_CONTEXT_KEY].content
        logger.info(f"[AGENT_NOTEBOOK] Loading unconditional context for system prompt ({len(content)} chars)")
        return content
    logger.info("[AGENT_NOTEBOOK] No unconditional context found")
    return ""
