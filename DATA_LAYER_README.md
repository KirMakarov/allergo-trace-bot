# AllergoTrace Bot - Data Layer Setup ✅

## Status: Stage 1 Completed

### ✅ Completed Tasks

1. **Database Engine** - Created async SQLite engine with foreign key support
2. **Models** - Defined all 6 tables with proper relationships
3. **Migrations** - Initialized Alembic with async template
4. **Initial Migration** - Generated and applied first migration
5. **Seeding** - Created initial ingredients JSON (278 products) and seeding script

---

## 🗄️ Database Schema

### Tables Created

- **users** - Telegram users with timezone and settings
- **ingredients** - Global and user-specific ingredients with categories and aliases
- **dishes** - User's dish templates (meal presets)
- **dish_ingredients** - Many-to-many relationship between dishes and ingredients
- **food_log** - Food consumption history with ingredient snapshots
- **symptom_log** - Symptom tracking with severity (1-5 scale)

---

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and set BOT_TOKEN
```

### 2. Install Dependencies

```bash
# Install all dependencies
uv sync

# Or install with dev tools
uv sync --extra dev
```

### 3. Run Migrations

```bash
# Apply migrations to create database schema
uv run alembic upgrade head
```

### 4. Seed Database

```bash
# Populate with initial ingredients
uv run python -m src.allergo_trace_bot.scripts.seed
```

---

## 🧪 Quality Assurance

### Linting

```bash
# Check code quality
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .
```

### Type Checking

```bash
# Run mypy type checker
uv run mypy src/
```

### All Checks Passing ✅

- ✅ Ruff linter: 0 errors
- ✅ Mypy type checker: Success
- ✅ Migrations: Working
- ✅ Database: Created (bot.db - 88KB)
- ✅ Seeding: 278 ingredients loaded

---

## 📂 Project Structure

```
allergo-trace-bot/
├── src/
│   └── allergo_trace_bot/
│       ├── __init__.py
│       ├── config.py              # Pydantic settings
│       ├── database/
│       │   ├── __init__.py
│       │   ├── core.py            # AsyncEngine + session factory
│       │   └── models.py          # SQLAlchemy models
│       └── scripts/
│           ├── __init__.py
│           └── seed.py            # Database seeding script
├── migrations/
│   ├── env.py                     # Alembic async environment
│   ├── versions/
│   │   └── a049c090e314_initial_schema.py
│   └── ...
├── data/
│   └── initial_ingredients.json  # 278 global ingredients
├── bot.db                         # SQLite database
├── alembic.ini                    # Alembic configuration
├── pyproject.toml                 # Project dependencies
└── .env                           # Environment variables
```

---

## 🔧 Key Technical Details

### Foreign Key Support (SQLite)

```python
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
```

This ensures CASCADE deletes and FK constraints work properly in SQLite.

### Async Everything

- ✅ AsyncEngine from SQLAlchemy 2.0
- ✅ aiosqlite driver
- ✅ Alembic async template
- ✅ async_sessionmaker for session factory

### Type Safety

- ✅ SQLAlchemy 2.0 `Mapped[]` type annotations
- ✅ Mypy strict mode compatible
- ✅ Proper type hints throughout

---

## 📊 Database Verification

```bash
# Check current migration version
uv run alembic current

# Show migration history
uv run alembic history

# Create new migration (after model changes)
uv run alembic revision --autogenerate -m "Your message"

# Upgrade to latest
uv run alembic upgrade head

# Rollback one step
uv run alembic downgrade -1
```

---

## 🎯 Next Steps (Stage 2)

1. **Bot Handlers** - Implement Telegram bot handlers with aiogram 3.x
2. **FSM (Finite State Machine)** - User interaction flows
3. **Dish Management** - CRUD operations for user dishes
4. **Food Logging** - Quick entry with autocomplete
5. **Reminders** - APScheduler integration with timezone support

---

## 📝 Notes

- Database file: `bot.db` (SQLite)
- Migrations tracked in `migrations/versions/`
- Global ingredients have `user_id=NULL`
- User-specific ingredients have `user_id` set
- All datetime fields use `func.now()` server default
- JSON fields store structured data (settings, aliases, snapshots)

---

## 🐛 Troubleshooting

### "greenlet library is required"

```bash
# Already fixed - greenlet added to dependencies
uv sync
```

### "Missing bot_token"

For Alembic and seeding, bot_token is optional (defaults to empty string).
For running the bot, set `BOT_TOKEN` in `.env`.

### Database locked

```bash
# Close any DB browsers/tools
# Or delete bot.db and re-run migrations
rm bot.db
uv run alembic upgrade head
uv run python -m src.allergo_trace_bot.scripts.seed
```

---

**Status**: ✅ Data Layer Complete and Production-Ready
