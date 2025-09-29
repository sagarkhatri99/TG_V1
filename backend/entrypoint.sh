#!/bin/bash
set -e

# Wait for database to be ready
echo "Waiting for database connection..."
while ! pg_isready -h db -p 5432 -U user; do
    echo "Database not ready, waiting..."
    sleep 2
done
echo "Database is ready!"

# Wait for Redis to be ready  
echo "Waiting for Redis connection..."
while ! redis-cli -h redis ping > /dev/null 2>&1; do
    echo "Redis not ready, waiting..."
    sleep 2
done
echo "Redis is ready!"

# Run database migrations
echo "Running database migrations..."

# First check if we need to merge heads
if ! alembic upgrade head 2>/dev/null; then
    echo "Migration failed, checking for multiple heads..."
    HEADS_COUNT=$(alembic heads | wc -l)
    if [ "$HEADS_COUNT" -gt 1 ]; then
        echo "Multiple heads detected, running merge script..."
        python merge_migrations.py
        echo "Attempting migration again after merge..."
        alembic upgrade head
    else
        echo "Single head detected but migration failed. Exiting."
        exit 1
    fi
fi

echo "Database migrations completed!"

# Initialize sample data (optional, non-blocking)
if [ -f "init_docker_data.py" ]; then
    echo "Initializing sample data..."
    python init_docker_data.py || echo "Warning: Sample data initialization failed, continuing..."
fi

echo "Starting FastAPI application..."
exec "$@"
