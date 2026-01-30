# AllergoTrace Bot

Telegram bot for allergy tracking and food diary management.

## Features


**Ingredient Management:**

- Search ingredients by name with autocomplete
- Browse ingredients by categories
- Add custom ingredients

**Dish Templates:**

- Create dish templates from multiple ingredients
- Save frequently eaten meals for quick logging
- Edit composition on the fly

**Food Logging:**

- Log meals using saved dish templates
- Modify ingredient composition before saving
- Snapshot mechanism for accurate history

**User Management:**

- Silent registration (automatic on first interaction)
- User timezone support (UTC by default)

## Quick Start

### Local Development

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd allergo-trace-bot
   ```

2. **Set up environment**

   ```bash
   # Copy environment template
   cp .env.example .env

   # Edit .env and add your BOT_TOKEN from @BotFather
   ```

3. **Install dependencies**

   ```bash
   uv sync --all-extras
   ```

4. **Run migrations**

   ```bash
   uv run alembic upgrade head
   ```

5. **Seed initial data (optional)**

   ```bash
   uv run python -m allergo_trace_bot.scripts.seed
   ```

6. **Run the bot**
   ```bash
   uv run python main.py
   ```

### Docker Deployment

1. **Configure environment**

   ```bash
   cp .env.example .env
   # Edit .env with your BOT_TOKEN
   ```

2. **Start the bot**

   ```bash
   docker compose up -d
   ```

3. **View logs**

   ```bash
   docker compose logs -f
   ```

4. **Stop the bot**
   ```bash
   docker compose down
   ```

## Project Structure

```
allergo-trace-bot/
├── src/
│   └── allergo_trace_bot/
│       ├── database/          # ORM models and DB core
│       ├── handlers/          # Bot command handlers
│       │   ├── food.py        # Ingredient search
│       │   ├── dish.py        # Dish creation (NEW Stage 3)
│       │   └── food_log.py    # Food logging (NEW Stage 3)
│       ├── keyboards/         # Inline keyboards
│       ├── middlewares/       # Registration middleware
│       └── scripts/           # Seed data and utilities
├── migrations/                # Alembic migrations
├── data/                      # SQLite database (auto-created)
├── STAGE3_SUMMARY.md         # Stage 3 completion summary
├── STAGE3_IMPLEMENTATION.md  # Stage 3 implementation details
├── STAGE3_TESTING.md         # Testing guide
└── pyproject.toml            # Dependencies
```

## 📖 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - 5-minute quick start guide
- **[STAGE3_SUMMARY.md](STAGE3_SUMMARY.md)** - Stage 3 completion summary
- **[STAGE3_TESTING.md](STAGE3_TESTING.md)** - Testing guide
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Project architecture
- **[DATA_LAYER_README.md](DATA_LAYER_README.md)** - Database schema

## Development

### Code Quality

```bash
# Run linter
uv run ruff check .

# Format code
uv run ruff format .

# Type checking
uv run mypy src/

# Run all checks (pre-commit)
uv run pre-commit run --all-files
```

### Testing

```bash
uv run pytest
```

## Tech Stack

- **Language:** Python 3.14
- **Bot Framework:** aiogram 3.x
- **Database:** SQLite with aiosqlite
- **ORM:** SQLAlchemy 2.0+
- **Migrations:** Alembic
- **Scheduler:** APScheduler
- **QA Tools:** ruff, mypy, pre-commit

## License

MIT / Personal Use
