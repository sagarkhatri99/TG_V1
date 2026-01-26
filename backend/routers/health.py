from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
import psutil
import time

router = APIRouter(
    prefix="/health",
    tags=["Health"]
)

@router.get("/")
def health_check(db: Session = Depends(get_db)):
    """
    Basic health check endpoint.
    Verifies API is running and database connection is active.
    """
    start_time = time.time()
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "database": "unknown",
        "system": {
            "cpu_usage": psutil.cpu_percent(),
            "memory_usage": psutil.virtual_memory().percent
        }
    }

    try:
        # Simple query to check DB connection
        db.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["database"] = f"error: {str(e)}"

    health_status["latency"] = round((time.time() - start_time) * 1000, 2)
    return health_status

@router.get("/overview")
def health_overview(db: Session = Depends(get_db)):
    """
    Alias for /health/ for consistency with other endpoints
    """
    return health_check(db)
