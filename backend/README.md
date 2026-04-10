# TG Tools Backend

FastAPI application providing a REST API for managing Telegram accounts, jobs, and campaigns.

> **PostgreSQL only** — SQLite is not supported and will cause a hard startup failure.

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

---

## Required Environment Variables

Create `backend/.env` before starting. These three variables are validated at startup — missing any of them will abort the process immediately:

```env
DATABASE_URL=postgresql://user:password@db:5432/tg_tools
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
SECRET_KEY=your-super-secret-key-here
TELEGRAM_API_ID=your_telegram_api_id
TELEGRAM_API_HASH=your_telegram_api_hash
# Optional
OPENAI_API_KEY=sk-...
```

Copy `.env.example` as a starting point:

```bash
cp backend/.env.example backend/.env
```

---

## Deployment

### Fresh deploy (first time or after volume wipe)

```bash
docker-compose down -v          # destroy all volumes (clean slate)
docker-compose up --build -d    # build images and start all services
```

### Regular update (no data loss)

```bash
docker-compose up --build -d    # rebuild images, restart containers
```

### Apply migrations manually (inside running container)

```bash
docker-compose exec backend alembic upgrade head
```

Migrations also run automatically in `docker-entrypoint.sh` before the API starts.  
**If migrations fail, the container will not start** — fix the migration and retry.

### Create a new migration after changing models

```bash
docker-compose exec backend alembic revision --autogenerate -m "describe your change"
```

---

## Services

| Service | URL | Description |
|---|---|---|
| Backend API | http://localhost:8000 | FastAPI |
| Flower | http://localhost:5555 | Celery task monitor |
| PostgreSQL | localhost:5432 | Database |
| Redis | localhost:6379 | Broker + cache |

---

## Health Check

```
GET /health
```

Returns `200 OK` with `{ "status": "ok", "db": "ok", "redis": "ok" }` when fully healthy.  
Returns `503` with failure details if DB or Redis is unavailable.

```
GET /api/health/diagnose
```

Full diagnostic — includes DB, Redis, Celery broker, and active worker checks.

---

## Workers

The application runs multiple Celery worker containers:

| Container | Queue | Concurrency | Purpose |
|---|---|---|---|
| `worker` | `celery,default` | 4 | General tasks |
| `worker-long` | `long_tasks` | 1 | Mass DM, Auto Promo, Group Joiner |
| `worker-short` | `short_tasks` | 3 | Scraping, Group Monitor |
| `celery-beat` | — | — | Scheduler |

`worker-long` uses `concurrency=1` — each replica handles one long-running task at a time.  
Current config scales to **28 replicas** to handle parallel campaigns.

---

## Schema Management

- **Alembic only** — no raw SQL schema creation at runtime.
- `Base.metadata.create_all()` is not called in production.
- `init_db.sql` and legacy `final_migrate.py` / `migrate_proxies_v2.py` are deprecated.

---

## Database Connection Pool

Each service process connects via SQLAlchemy `QueuePool`:

| Setting | Value |
|---|---|
| `pool_size` | 5 |
| `max_overflow` | 10 |
| `pool_timeout` | 30 s |
| `pool_recycle` | 1800 s |
| `statement_timeout` | 30 s (PostgreSQL) |

PostgreSQL is configured with `max_connections=500` to handle all worker replicas.

---

## Running Tests

```bash
pytest backend/tests
```

---

## Troubleshooting

### `DATABASE_URL environment variable is not set`
Add `DATABASE_URL=postgresql://...` to `backend/.env`.

### `Alembic migration FAILED — aborting startup`
Run migrations manually to see the full error:
```bash
docker-compose exec backend alembic upgrade head
```

### `No tables found in the database`
Migrations have not been applied (or the volume was reset without re-migrating):
```bash
docker-compose exec backend alembic upgrade head
```

### Permission denied (Docker daemon)
```bash
sudo usermod -aG docker $USER && newgrp docker
```
