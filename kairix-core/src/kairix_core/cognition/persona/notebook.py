from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from agents import function_tool

from kairix_core.runtime.cache import CacheRuntime
from kairix_core.runtime.logging import LoggingRuntime
from diskcache import Index

@dataclass
class Note:
    title: str
    created_at: datetime
    modified_at: Optional[datetime]
    content: str
    tags: set[str]



logger = LoggingRuntime().logger

class Notebook:

    def __init__(self):
        logger.info("initializing persona notebook.")
        self.notebook: Index = CacheRuntime().persona_notebook

    @function_tool
    def list_titles(self) -> list[str]:
        logger.info("Persona listed titles.")
        return [t for t in self.notebook]

    @function_tool
    def note_or_throw(self, title: str) -> list[str]:
        logger.info("Persona invoking note_or_none")
        result = self.notebook[title]
        assert isinstance(result, list)
        return result

    @function_tool
    def maybe_note(self, title: str) -> list[str] | None:
        logger.info("Persona invoking maybe_note")
        return self.notebook[title] if title in self.notebook else None

    @function_tool
    def save(self, title: str, content: str, tags: set[str]) -> None:
        logger.info("Persona saving to notebook.")
        note = None
        if title in self.notebook:
            logger.info("Found existing title, amending.")
            note = self.notebook[title]
            note.content = content
            note.tags.union(tags)
            note.modified_at = datetime.now()
        else:
            logger.info("Creating new note.")
            note = Note(title, datetime.now(), None, content, tags if tags else set())


        self.notebook[title] = note
        logger.info(f"Saved note for {title}, Note was:\n {note}")

