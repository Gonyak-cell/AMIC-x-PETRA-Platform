#!/bin/bash
set -e

echo "=== Auto FDD Docker Entrypoint ==="

# Run database migrations
echo "Running database migrations..."
alembic upgrade head
echo "Database migrations completed."

# Start the application server
echo "Starting Auto FDD application server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WORKERS:-4}
