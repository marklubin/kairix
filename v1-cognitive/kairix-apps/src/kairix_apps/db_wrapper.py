"""Database wrapper with read-only enforcement for shadow environments."""
import os
import sqlite3
from contextlib import contextmanager
from typing import Any

from kairix_core.runtime.logging import LoggingRuntime

logger = LoggingRuntime().logger


class ReadOnlyDatabaseError(Exception):
    """Raised when attempting write operation in read-only mode."""

    pass


class DatabaseWrapper:
    """Wraps database connections with optional read-only enforcement."""

    def __init__(self, db_path: str, read_only: bool = False):
        self.db_path = db_path
        # Check environment variable for read-only mode
        self.read_only = read_only or os.getenv("KAIRIX_DB_READ_ONLY", "false").lower() == "true"

        if self.read_only:
            logger.info(f"Database {db_path} opened in READ-ONLY mode (shadow environment)")
        else:
            logger.info(f"Database {db_path} opened in READ-WRITE mode")

    @contextmanager
    def connection(self):
        """Get a database connection with read-only enforcement."""
        if self.read_only:
            # Open in read-only mode using URI
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        else:
            conn = sqlite3.connect(self.db_path)

        try:
            yield conn
        finally:
            conn.close()

    def execute_query(self, query: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        """Execute a SELECT query."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()

    def execute_write(self, query: str, params: tuple[Any, ...] = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE query."""
        if self.read_only:
            raise ReadOnlyDatabaseError(
                f"Cannot execute write operation in read-only mode. "
                f"This is a shadow environment. Query: {query[:100]}"
            )

        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid

    def execute_many(self, query: str, params_list: list[tuple[Any, ...]]) -> None:
        """Execute multiple write operations."""
        if self.read_only:
            raise ReadOnlyDatabaseError(
                "Cannot execute write operations in read-only mode. "
                "This is a shadow environment."
            )

        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()

    def is_read_only(self) -> bool:
        """Check if database is in read-only mode."""
        return self.read_only


def get_environment_type() -> str:
    """Get the current environment type (production, shadow, development)."""
    env = os.getenv("KAIRIX_ENVIRONMENT", "production")
    return env


def is_shadow_environment() -> bool:
    """Check if running in shadow environment."""
    return get_environment_type() == "shadow"
