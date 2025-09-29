from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import Base, engine
from routers.auth import router as auth_router
from routers.lead_profiles import router as lead_profiles_router
from routers.leads import router as leads_router

app = FastAPI(title="SDR Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    # Auto-create tables for simplicity in isolated app
    Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {"status": "ok", "service": "sdr", "version": "1.0.0"}

# Mount routers
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(lead_profiles_router, prefix="/api/lead-profiles", tags=["Lead Profiles"])
app.include_router(leads_router, prefix="/api/leads", tags=["Leads"])