# Stage 1: Build environment
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

WORKDIR /app

# Install uv and copy dependency files
COPY pyproject.toml .
COPY README.md .

# Copy source code
COPY src/ src/

# Install dependencies and build
RUN uv sync --frozen --no-dev

# Stage 2: Runtime environment
FROM python:3.14-slim-bookworm AS runtime

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source code and entry point
COPY --from=builder /app/src /app/src
COPY main.py /app/
COPY alembic.ini /app/
COPY migrations /app/migrations
COPY docker-entrypoint.sh /app/

# Make entrypoint executable
RUN chmod +x /app/docker-entrypoint.sh

# Create data directory for database
RUN mkdir -p /app/data

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Run the bot
ENTRYPOINT ["/app/docker-entrypoint.sh"]
