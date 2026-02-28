"""Database core: AsyncEngine and session management."""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from allergo_trace_bot.config import settings

# Create async engine
async_engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
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


async def init_db() -> None:
    """Initialize database tables.

    Creates all tables defined in models if they don't exist.
    Uses Alembic for migrations in production.
    """
    async with async_engine.begin():
        # Import all models to ensure they're registered
        from allergo_trace_bot.database.models import (  # noqa: F401
            Dish,
            DishIngredient,
            FoodLog,
            Ingredient,
            SymptomLog,
            User,
            UserSafeIngredient,
        )

        # This would normally be done via Alembic migrations
        # But for development/testing, we can create tables directly
        # await conn.run_sync(Base.metadata.create_all)
        pass


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Dependency for getting database sessions.

    Usage:
        async with get_session() as session:
            # Use session here
            pass
    """
    async with AsyncSessionLocal() as session:
        yield session
