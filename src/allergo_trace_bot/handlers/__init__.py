"""Handlers for the bot."""

from .dish import router as dish_router
from .food import router as food_router
from .food_log import router as food_log_router
from .timezone import router as timezone_router

__all__ = [
    "food_router",
    "dish_router",
    "food_log_router",
    "timezone_router",
    "analytics_router",
]
