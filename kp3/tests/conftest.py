"""Test fixtures using compose-managed Postgres + pgvector.

Requires: Test database must exist before running tests.
Run once: psql -h localhost -U kp3 -c "CREATE DATABASE kp3_test"
"""

import os
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from kp3.db.models import Base

# Test database configuration - connects to compose-managed postgres
TEST_DB_HOST = os.getenv("KP3_TEST_DB_HOST", "localhost")
TEST_DB_PORT = os.getenv("KP3_TEST_DB_PORT", "5432")
TEST_DB_USER = os.getenv("KP3_TEST_DB_USER", "kp3")
TEST_DB_PASSWORD = os.getenv("KP3_TEST_DB_PASSWORD", "kp3")
TEST_DB_NAME = os.getenv("KP3_TEST_DB_NAME", "kp3_test")

TEST_DB_URL = (
    f"postgresql+asyncpg://{TEST_DB_USER}:{TEST_DB_PASSWORD}"
    f"@{TEST_DB_HOST}:{TEST_DB_PORT}/{TEST_DB_NAME}"
)


@pytest.fixture
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create async engine and set up schema."""
    eng = create_async_engine(TEST_DB_URL, echo=False)

    async with eng.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield eng

    await eng.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh session for each test."""
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_maker() as sess:
        yield sess
        await sess.rollback()
