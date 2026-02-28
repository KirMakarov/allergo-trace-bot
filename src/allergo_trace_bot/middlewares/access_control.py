"""Access control middleware to restrict bot usage."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from aiogram.types import User as TgUser

from allergo_trace_bot.config import settings
from allergo_trace_bot.database.models import User


class AccessControlMiddleware(BaseMiddleware):
    """Middleware to check if user has access to the bot.

    Access is granted if:
    1. No admin users configured (open access)
    2. User is in admin list
    3. User exists in DB and is_active=True
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Check user access before processing update."""
        tg_user: TgUser | None = data.get("event_from_user")
        db_user: User | None = data.get("db_user")

        if tg_user is None:
            # No user in update (channel post, etc.) - allow
            return await handler(event, data)

        admin_ids = settings.admin_ids_list

        # If no admins configured, allow all users
        if not admin_ids:
            return await handler(event, data)

        # Check if user is admin
        if tg_user.id in admin_ids:
            return await handler(event, data)

        # Check if user is active in database
        if db_user and db_user.is_active:
            return await handler(event, data)

        # Access denied - send message only for Message updates
        if isinstance(event, Update) and event.message:
            await event.message.answer(
                "❌ <b>Доступ запрещён</b>\n\n"
                "Этот бот доступен только авторизованным пользователям.\n"
                "Обратитесь к администратору для получения доступа."
            )

        # Block further processing
        return None
