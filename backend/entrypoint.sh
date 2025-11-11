#!/bin/bash

echo "🔄 Checking database connection..."
for i in {1..30}; do
    if pg_isready -h db -p 5432 -U user >/dev/null 2>&1; then
        echo "✅ Database is ready!"
        break
    fi
    echo "Attempt $i/30..."
    sleep 1
done

echo "Running migrations..."
alembic upgrade head || true

echo "Initializing users..."
python init_users.py || true

echo "🚀 Starting Uvicorn..."
echo "About to run uvicorn..." >&2
PYTHONUNBUFFERED=1 /usr/local/bin/python -u -m uvicorn main:app --host 0.0.0.0 --port 8000
echo "Uvicorn exited with code: $?" >&2
