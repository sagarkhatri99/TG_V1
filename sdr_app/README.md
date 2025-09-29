# SDR App (Isolated)

This is a standalone backend service exposing the SDR (Sales Development Representative) API that was split from the main TG Tools app.

Run locally (SQLite)
- Create and activate a virtual environment
  - python -m venv .venv && .venv\Scripts\Activate.ps1
- Install dependencies
  - pip install -r backend/requirements.txt
- Start the API
  - uvicorn backend.main:app --host 0.0.0.0 --port 8080
- Health
  - http://localhost:8080/health

Environment
- DATABASE_URL (default: sqlite:///./sdr_app.db)
- SECRET_KEY (for JWT)

Auth
- Register: POST /api/auth/register
- Login (OAuth2 password): POST /api/auth/login
  - Use the returned bearer token for SDR endpoints

SDR Endpoints
- Lead Profiles
  - POST   /api/lead-profiles/
  - GET    /api/lead-profiles/
  - GET    /api/lead-profiles/{id}
  - PUT    /api/lead-profiles/{id}
  - DELETE /api/lead-profiles/{id}
  - GET    /api/lead-profiles/{id}/stats
- Leads
  - POST   /api/leads/
  - POST   /api/leads/bulk
  - GET    /api/leads/
  - GET    /api/leads/{id}
  - PUT    /api/leads/{id}
  - PATCH  /api/leads/{id}/status (not implemented here; add if needed)
  - DELETE /api/leads/{id}
  - GET    /api/leads/profile/{id}/stats

Plans and access
- SDR access is restricted to Enterprise/Admin users. Update subscription_plan on users to 'enterprise' or 'admin' to enable access.
