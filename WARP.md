# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

Project summary
- Monorepo with a FastAPI backend and a Vite React (TypeScript) frontend, orchestrated via Docker Compose. Redis (broker) and PostgreSQL back the backend; Celery handles background jobs.

Key services and entry points
- Frontend: Vite React app served via Nginx in container (frontend/Dockerfile). Dev mode via Vite.
- Backend: FastAPI app (backend/main.py) exposes REST and OpenAPI docs; Celery worker (backend/celery_app.py) processes long-running tasks.
- Data/Infra: PostgreSQL (db), Redis (redis). Alembic migrations are applied automatically on container start (see backend/entrypoint.sh and backend/alembic/*).

Essential commands

Docker workflow (recommended)
- Build and start all services (detached):
  - docker compose up --build -d
- Tail logs (all or specific):
  - docker compose logs -f
  - docker compose logs -f backend
- Check service status:
  - docker compose ps
- Restart services (all or specific):
  - docker compose restart
  - docker compose restart backend
- Stop and remove:
  - docker compose down
- Clean reset (remove volumes and images), then rebuild:
  - docker compose down -v --rmi all
  - docker compose up --build -d

Backend (FastAPI + Celery)
- Local dependencies (outside Docker):
  - python -m venv .venv && .venv\Scripts\Activate.ps1
  - pip install -r backend/requirements.txt
- Run API locally (outside Docker; uses DATABASE_URL from env or falls back to SQLite):
  - uvicorn backend.main:app --host 0.0.0.0 --port 8000
- Run Celery worker locally (outside Docker):
  - cd backend; celery -A celery_app worker -l info
- Run tests (inside Docker):
  - docker compose exec backend pytest backend/tests -q
- Run tests (locally):
  - pytest backend/tests -q
- Run a single test (example):
  - docker compose exec backend pytest backend/tests/test_main.py::test_health_check -q
  - pytest backend/tests/test_main.py::test_health_check -q
- Alembic (inside backend container):
  - docker compose exec backend alembic current
  - docker compose exec backend alembic revision --autogenerate -m "your message"
  - docker compose exec backend alembic upgrade head

Frontend (Vite React + ESLint)
- Install deps:
  - cd frontend; npm ci
- Dev server:
  - npm run dev
- Build:
  - npm run build
- Preview production build:
  - npm run preview
- Lint:
  - npm run lint

Important environment and access notes
- Backend environment lives in backend/.env. Typical keys (see backend/README.md): DATABASE_URL, OPENAI_API_KEY, REDIS_URL, SECRET_KEY.
- When run locally without Docker, backend/database.py will default to SQLite (sqlite:///./tg_tools.db) if DATABASE_URL is not set.
- OpenAPI docs/health:
  - API: http://localhost:8000
  - Docs: http://localhost:8000/docs
  - Health: http://localhost:8000/health
- Test users for local Docker runs may be available if initialization scripts are enabled.

High-level architecture (big picture)
- API composition (backend/main.py):
  - Assembles feature routers under /api/*, including:
    - Accounts (/api/accounts), Jobs (/api/jobs), Auth (/api/auth), Admin, Proxies, Subscriptions
    - Feature modules with their own routers and Celery tasks: auto_promo, group_monitor, mass_dm_account, mass_dm_bot, scrape_user_id
  - Cross-cutting endpoints: /health, /stats, /api/me/stats
  - CORS allows localhost origins used by the Vite dev server and UI
- Persistence and data model:
  - SQLAlchemy models defined in backend/models.py (User, TelegramAccount, Proxy, UserInteraction, Job, MessageLog)
  - DB session dependency via backend/database.py:get_db; engine driven by DATABASE_URL
  - Alembic migrations in backend/alembic/versions; entrypoint applies migrations at container start
- Auth and authorization:
  - OAuth2 password flow at /api/auth/login returning JWT (routers/auth.py), user creation at /api/auth/register
  - Request-time plan checks via core.dependencies.plan_based_dependency and explicit checks in SDR routers
  - Subscription gating examples: account limits in accounts.create; SDR routes enforce enterprise/admin plans
- Background processing:
  - Celery app (backend/celery_app.py) includes tasks from feature modules (auto_promo, group_monitor, mass_dm_account, mass_dm_bot); Redis is broker/result backend
  - Worker container started by docker-compose; shares volumes with backend for sessions/uploads/job_results
- Session and Telegram integration:
  - Telethon clients managed via core/session_manager with per-account session files mounted under backend/sessions
  - Actions that require Telegram connectivity (e.g., verification, DM) obtain and cleanly disconnect clients per request
- Frontend integration:
  - Vite React app (frontend) talks to backend at http://localhost:8000; routes/pages exist for Accounts, Jobs, Mass DM, Group Monitor, Settings, etc.

Testing notes
- Pytest configuration at repo root (pytest.ini) sets asyncio_mode=auto. Backend tests live under backend/tests; use pytest backend/tests ... to target them explicitly.
- API health test example exists (backend/tests/test_main.py::test_health_check) expecting {"status": "ok", "version": "2.0.0"}.
- Additional backend test scripts exist at backend/test_*.py that can be run directly via python or pytest if needed.

CI/CD reference
- See cicd-plan.md for a GitHub Actions-oriented pipeline outline: build (multi-arch images), test (docker-compose + pytest), and manual deploys to staging/production.

Gotchas and tips for agents
- If containers appear healthy but the UI fails, confirm backend health (curl http://localhost:8000/health) and check docker compose logs -f frontend/backend.
- When developing locally without Docker, remember to set DATABASE_URL/REDIS_URL to match your local services, or accept SQLite fallback for quick iteration.
- Note: The SDR feature has been extracted into a separate app under sdr_app/. This repository's main app no longer exposes SDR endpoints.
