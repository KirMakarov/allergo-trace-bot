"""Handlers for the bot."""

from .analytics import router as analytics_router
from .dish import router as dish_router
from .food import router as food_router
from .food_log import router as food_log_router
from .menu import router as menu_router
from .menu import set_bot_commands
from .menu_buttons import router as menu_buttons_router
from .timezone import router as timezone_router

__all__ = [
    "food_router",
    "dish_router",
    "food_log_router",
    "timezone_router",
    "analytics_router",
    "menu_router",
    "menu_buttons_router",
    "set_bot_commands",
]
