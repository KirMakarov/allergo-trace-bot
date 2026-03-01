#!/bin/bash
set -e

echo "🔧 Running database migrations..."
alembic upgrade head

echo "🚀 Starting AllergoTrace Bot..."
exec python main.py
