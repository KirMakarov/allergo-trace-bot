# AllergoTrace Bot

Telegram bot for allergy tracking and food diary management.

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
│   └── allergo_trace_bot/     # Main package
├── data/                       # Database storage (created automatically)
├── .env.example               # Environment template
├── docker-compose.yml         # Docker orchestration
├── Dockerfile                 # Container build configuration
└── pyproject.toml            # Project dependencies and config
```

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
