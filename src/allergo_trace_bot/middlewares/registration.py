"""Registration middleware for silent user registration."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.types import User as TgUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from allergo_trace_bot.database.models import User


class RegistrationMiddleware(BaseMiddleware):
    """Middleware to ensure user exists in database before processing updates.

    Performs silent registration - creates user on first interaction without
    explicit registration command.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Check if user exists in DB, create if not."""
        session: AsyncSession = data["session"]
        tg_user: TgUser | None = data.get("event_from_user")

        if tg_user is None:
            # No user in update (channel post, etc.)
            return await handler(event, data)

        # Check if user exists
        result = await session.execute(select(User).where(User.id == tg_user.id))
        db_user = result.scalar_one_or_none()

        if db_user is None:
            # Silent registration
            db_user = User(id=tg_user.id)
            session.add(db_user)
            await session.commit()
            await session.refresh(db_user)

        # Add user to data for handlers
        data["db_user"] = db_user

        return await handler(event, data)
