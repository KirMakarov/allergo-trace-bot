"""Configuration management using pydantic-settings."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Telegram Bot
    bot_token: str = Field(default="", description="Telegram Bot API token")

    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///bot.db", description="Async database connection URL")

    # Application
    debug: bool = Field(default=False, description="Debug mode")

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
    "Овощи",
    "Фрукты",
    "Молочные продукты",
    "Мясо и рыба",
    "Крупы и злаки",
    "Напитки",
    "Сладости",
    "Другое",
]

# Dish categories (meal types)
DISH_CATEGORIES = [
    "Завтраки",
    "Салаты",
    "Супы",
    "Основные блюда",
    "Гарниры",
    "Напитки",
    "Десерты",
    "Закуски",
    "Другое",
]
