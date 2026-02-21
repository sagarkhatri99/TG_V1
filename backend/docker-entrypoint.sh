#!/bin/bash
# Docker entrypoint script for backend service
# Handles database initialization and migrations

set -e

echo "🚀 Starting TG_V1 Backend..."

# Wait for database to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "db" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; do
  echo "   PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "✅ PostgreSQL is up and running!"

# Check if database is empty (first run)
TABLE_COUNT=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h "db" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" | tr -d ' ')

if [ "$TABLE_COUNT" = "0" ]; then
    echo "📋 Empty database detected - Running initialization script..."
    PGPASSWORD=$POSTGRES_PASSWORD psql -h "db" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /app/init_db.sql
    echo "✅ Database initialized successfully!"
else
    echo "✅ Database already initialized ($TABLE_COUNT tables found)"
fi

# Run Alembic migrations (for incremental changes)
echo "🔄 Running Alembic migrations..."
alembic upgrade head || echo "⚠️  Migration warning (may be expected if schema is already up to date)"

echo "🎉 Backend ready to start!"

# Execute the main command (FastAPI server)
exec "$@"
