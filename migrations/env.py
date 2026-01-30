import asyncio
import importlib
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Adjust Python path to include the src directory for consistent module imports
project_root = Path(__file__).resolve().parents[1]  # Go up to project root
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Import configuration and models using importlib to avoid E402
config_module = importlib.import_module("allergo_trace_bot.config")
settings = config_module.settings
models_module = importlib.import_module("allergo_trace_bot.database.models")
Base = models_module.Base

# Alembic Config object for accessing .ini file values
config = context.config

# Configure the database URL from settings
config.set_main_option("sqlalchemy.url", settings.database_url)

# Set up logging if config file is present
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogeneration support
target_metadata = Base.metadata

# Placeholder for additional config options if needed
# e.g., custom_option = config.get_main_option("custom_option")


def run_migrations_offline() -> None:
    """Execute migrations in offline mode without requiring a DBAPI."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Handle async migrations by creating an engine and connecting."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Execute migrations in online mode."""
    asyncio.run(run_async_migrations())


# Determine mode and run accordingly
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
