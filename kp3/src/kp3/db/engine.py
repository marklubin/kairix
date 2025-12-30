"""Database engine setup."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from kp3.config import get_settings

engine = create_async_engine(
    get_settings().database_url,
    echo=False,
    pool_pre_ping=True,  # Validate connections before use (prevents stale connection errors)
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session."""
    async with async_session() as session:
        yield session
