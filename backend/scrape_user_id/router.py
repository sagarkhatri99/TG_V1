from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from fastapi.responses import FileResponse
from .service import start_scrape_auth, verify_and_scrape
from database import get_db
from models import User
from routers.auth import get_current_user

router = APIRouter()

class StartAuthRequest(BaseModel):
    api_id: int
    api_hash: str
    phone_number: str

class VerifyScrapeRequest(BaseModel):
    api_id: int
    api_hash: str
    phone_number: str
    code: str
    group_username: str

@router.post("/start-auth")
async def start_auth(request: StartAuthRequest, current_user: User = Depends(get_current_user)):
    if current_user.subscription_plan != 'premium':
        raise HTTPException(status_code=403, detail="Scraping is a premium feature.")
    try:
        await start_scrape_auth(request.api_id, request.api_hash, request.phone_number)
        return {"success": True, "message": "OTP sent to your phone"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/verify-scrape")
async def verify_scrape(request: VerifyScrapeRequest, current_user: User = Depends(get_current_user)):
    if current_user.subscription_plan != 'premium':
        raise HTTPException(status_code=403, detail="Scraping is a premium feature.")
    try:
        count = await verify_and_scrape(
            request.api_id,
            request.api_hash,
            request.phone_number,
            request.code,
            request.group_username
        )
        return {"message": f"Scraped {count} users from {request.group_username}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download")
def download_csv(phone_number: str, current_user: User = Depends(get_current_user)):
    if current_user.subscription_plan != 'premium':
        raise HTTPException(status_code=403, detail="Scraping is a premium feature.")
    filename = f"participants_{phone_number}.csv"
    return FileResponse(filename, media_type="text/csv", filename=filename)
