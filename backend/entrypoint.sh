#!/bin/bash
set -e

# Wait for the DB to be ready by retrying alembic upgrade until it succeeds.
# This handles "connection refused" during container startup when DB isn't ready yet.
MAX_RETRIES=30
RETRY_DELAY=2
count=0
echo "Waiting for database to be ready (up to $((MAX_RETRIES * RETRY_DELAY))s)..."
until alembic upgrade head >/dev/null 2>&1; do
  count=$((count + 1))
  if [ "$count" -ge "$MAX_RETRIES" ]; then
    echo "ERROR: Database not ready after $((MAX_RETRIES * RETRY_DELAY))s. Exiting."
    # Show last backend + db logs for quick debugging
    echo "----- last backend logs -----"
    docker-compose logs --tail=50 backend || true
    echo "----- last db logs -----"
    docker-compose logs --tail=50 db || true
    exit 1
  fi
  echo "Database not ready yet. Retrying in ${RETRY_DELAY}s... ($count/$MAX_RETRIES)"
  sleep $RETRY_DELAY
done

echo "Database ready, migrations applied."

# Execute the command passed to the container (e.g. uvicorn)
exec "$@"
