# AllergoTrace Bot

Telegram bot for allergy tracking and food diary management.

## Features

**Ingredient Management:**

- Search ingredients by name with autocomplete
- Browse ingredients by categories
- Add custom ingredients to personal list
- Mark ingredients as safe (allergen-free)
- Support for "Big 8" allergen marking

**Dish Templates:**

- Create dish templates from multiple ingredients
- Save frequently eaten meals for quick logging
- Clone and modify existing dishes
- Edit composition on the fly when logging food

**Food Logging:**

- Log meals using saved dish templates or individual ingredients
- Modify ingredient composition before saving
- Snapshot mechanism for accurate history tracking
- View food history with timestamps

**Analytics & Correlation:**

- Analyze correlations between food and symptoms
- Configurable time window for symptom correlation (1-24 hours)
- Risk scoring based on symptom frequency
- Mark safe ingredients based on analysis results

**Smart Reminders:**

- Automated food and symptom reminders
- Timezone-aware scheduling (respects user's local time)
- GPS-based timezone detection or manual selection
- Configurable reminder times for food and symptoms

**User Management:**

- Silent registration (automatic on first interaction)
- Access control with allowlist (optional)
- User timezone support with automatic detection
- Customizable reminder settings per user

## Quick Start

### Prerequisites

- Python 3.14+
- `uv` package manager ([installation guide](https://github.com/astral-sh/uv))
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)

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

   Or with virtual environment activated:

   ```bash
   python main.py
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

   The container will automatically:

   - Run database migrations
   - Start the bot

3. **View logs**

   ```bash
   docker compose logs -f
   ```

4. **Stop the bot**
   ```bash
   docker compose down
   ```

## Configuration

The bot uses environment variables for configuration. Copy `.env.example` to `.env` and configure:

### Required Settings

- `BOT_TOKEN` - Your Telegram Bot API token from [@BotFather](https://t.me/BotFather)

### Optional Settings

- `DATABASE_URL` - Database connection string (default: `sqlite+aiosqlite:///bot.db`)
- `ADMIN_USER_IDS` - Comma-separated list of admin Telegram user IDs for access control (default: empty, allows all users)
- `DEBUG` - Enable debug mode with verbose logging (default: `False`)
- `LOG_LEVEL` - Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`)

### Example .env file

```env
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_USER_IDS=123456789,987654321
DEBUG=False
LOG_LEVEL=INFO
```

## Project Structure

```
allergo-trace-bot/
├── src/
│   └── allergo_trace_bot/
│       ├── database/          # ORM models and DB core
│       │   ├── models/        # SQLAlchemy models
│       │   │   ├── user.py
│       │   │   ├── ingredient.py
│       │   │   ├── dish.py
│       │   │   ├── dish_ingredient.py
│       │   │   ├── food_log.py
│       │   │   ├── symptom_log.py
│       │   │   └── user_safe_ingredient.py
│       │   └── core.py        # Database engine & initialization
│       ├── handlers/          # Bot command handlers
│       │   ├── food.py        # Ingredient search & management
│       │   ├── dish.py        # Dish creation & editing
│       │   ├── food_log.py    # Food logging
│       │   ├── analytics.py   # Correlation analysis
│       │   ├── timezone.py    # Timezone & reminder settings
│       │   ├── menu.py        # Main menu & help
│       │   └── menu_buttons.py # Menu button handlers
│       ├── keyboards/         # Inline keyboards
│       │   ├── food.py
│       │   ├── dish.py
│       │   ├── food_log.py
│       │   ├── analytics.py
│       │   ├── timezone.py
│       │   └── menu.py
│       ├── middlewares/       # Middleware components
│       │   ├── registration.py  # Auto user registration
│       │   └── access_control.py # User allowlist
│       ├── services/          # Business logic services
│       │   └── analytics.py   # Correlation analysis service
│       ├── utils/             # Utility functions
│       │   └── datetime_utils.py  # UTC datetime helpers
│       ├── scripts/           # Data management scripts
│       │   ├── seed.py        # Seed global ingredients
│       │   └── mark_big8.py   # Mark Big 8 allergens
│       ├── config.py          # Pydantic settings
│       └── scheduler.py       # APScheduler for reminders
├── migrations/                # Alembic migrations
├── data/                      # SQLite database (auto-created)
├── main.py                    # Bot entry point
├── pyproject.toml             # Dependencies & tool config
└── docker-compose.yml         # Docker deployment
```

## 📖 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - 5-minute quick start guide
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Project
- **[DATA_LAYER_README.md](DATA_LAYER_README.md)** - Database schema

## Available Commands

**Main Commands:**

- `/start` - Welcome message and main menu
- `/log_food` - 🍽 Log a meal (from dishes or ingredients)
- `/my_dishes` - 📋 View and manage your dish templates
- `/food` - 🥗 Search and add ingredients to your list
- `/new_dish` - 🍳 Create a new dish template
- `/analyze` - 📊 Analyze food-symptom correlations
- `/settings` - ⚙️ Configure timezone and reminders
- `/help` - ❓ Show help and available commands
- `/stop` - 🛑 Cancel current operation

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
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=src/allergo_trace_bot --cov-report=html

# Run specific test file
uv run pytest tests/test_analytics.py -v

# View coverage report
open htmlcov/index.html
```

**Test Suite Includes:**

- Unit tests for handlers, keyboards, and services
- Integration tests for end-to-end workflows
- Model and database tests
- Middleware tests
- Analytics service tests

## Troubleshooting

### Common Issues

**Bot doesn't start:**

- Check that `BOT_TOKEN` is set correctly in `.env`
- Verify database migrations are applied: `uv run alembic upgrade head`
- Check logs for specific errors

**Database errors:**

- Ensure `data/` directory exists and is writable
- Try deleting `bot.db` and re-running migrations (⚠️ will delete all data)
- Check SQLite version: `sqlite3 --version` (requires 3.35+)

**Timezone issues:**

- Verify `pytz` and `timezonefinder` are installed
- Check user timezone setting with `/settings` command
- Ensure system timezone data is up to date

**Docker issues:**

- Ensure `data/` volume is mounted correctly
- Check container logs: `docker compose logs -f`
- Verify `.env` file is in the same directory as `docker-compose.yml`

## Contributing

This is a personal project for allergy tracking. Contributions are welcome but please open an issue first to discuss proposed changes.

## Tech Stack

- **Language:** Python 3.14
- **Package Manager:** uv (Fast Python package installer)
- **Bot Framework:** aiogram 3.x (Async)
- **Database:** SQLite with aiosqlite
- **ORM:** SQLAlchemy 2.0+ (Async)
- **Migrations:** Alembic (Async template)
- **Scheduler:** APScheduler (AsyncIOScheduler)
- **Timezones:** pytz, zoneinfo, timezonefinder
- **Config:** pydantic-settings
- **QA Tools:** ruff (linter/formatter), mypy (type checker), pre-commit

## License

MIT / Personal Use
