"""Database core: AsyncEngine and session management."""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from allergo_trace_bot.config import settings

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
    """Enable foreign keys for SQLite connections.

    This is critical for maintaining referential integrity in SQLite.
    Without this pragma, CASCADE deletes and foreign key constraints won't work.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Dependency for getting database sessions.

    Usage:
        async with get_session() as session:
            # Use session here
            pass
    """
    async with AsyncSessionLocal() as session:
        yield session
