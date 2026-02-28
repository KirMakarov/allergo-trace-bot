"""Configuration management using pydantic-settings."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Telegram Bot
    bot_token: str = Field(default="", description="Telegram Bot API token")

    # Access Control
    admin_user_ids: str = Field(default="", description="Comma-separated list of admin Telegram user IDs")

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///bot.db",
        description="Async database connection URL",
    )

    # Application
    debug: bool = Field(default=False, description="Debug mode")

    @property
    def admin_ids_list(self) -> list[int]:
        """Parse admin_user_ids string into list of integers."""
        if not self.admin_user_ids:
            return []
        return [int(uid.strip()) for uid in self.admin_user_ids.split(",") if uid.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Global settings instance
settings = Settings()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Food categories for ingredients
FOOD_CATEGORIES = [
    "Vegetables",
    "Fruits",
    "Dairy",
    "Meat & Fish",
    "Grains",
    "Drinks",
    "Sweets",
    "Other",
]

# Dish categories (meal types)
DISH_CATEGORIES = [
    "Breakfast",
    "Salad",
    "Soup",
    "Main Course",
    "Side Dish",
    "Drink",
    "Dessert",
    "Snack",
    "Other",
]
