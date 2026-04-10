#!/bin/bash
# Docker entrypoint script for backend service
# Handles database readiness check and Alembic migrations before starting FastAPI.
# Migrations MUST succeed — the container will not start if they fail.

set -e

echo "🚀 Starting TG_V1 Backend..."

# Verify required env vars are present before doing anything else
: "${DATABASE_URL:?DATABASE_URL is not set — cannot start}"
: "${REDIS_URL:?REDIS_URL is not set — cannot start}"
: "${CELERY_BROKER_URL:?CELERY_BROKER_URL is not set — cannot start}"

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "db" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; do
  echo "   PostgreSQL is unavailable - sleeping"
  sleep 2
done
echo "✅ PostgreSQL is up and running!"

# Run Alembic migrations — HARD FAILURE if they don't apply cleanly
echo "🔄 Running Alembic migrations..."
if ! alembic upgrade head; then
    echo "❌ Alembic migration FAILED — aborting startup."
    echo "   Fix the migration error, then retry: docker-compose up --build -d"
    exit 1
fi
echo "✅ Migrations applied successfully."

echo "🎉 Backend ready to start!"

# Execute the main command (FastAPI server)
exec "$@"
