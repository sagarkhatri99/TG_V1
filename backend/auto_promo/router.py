# auto_promo/router.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .service import start_auto_promo_auth, verify_and_start_promo

router = APIRouter()

class AutoPromoAuthRequest(BaseModel):
    api_id: int
    api_hash: str
    phone_number: str

class AutoPromoStartRequest(BaseModel):
    api_id: int
    api_hash: str
    phone_number: str
    otp: str
    target_group: str
    promo_message: str
    interval_seconds: int

@router.post("/start-auth")
async def start_auth(req: AutoPromoAuthRequest):
    try:
        await start_auto_promo_auth(req.api_id, req.api_hash, req.phone_number)
        return {"success": True, "message": "OTP sent to your phone"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/start")
async def start_promo(req: AutoPromoStartRequest):
    try:
        result = await verify_and_start_promo(
            req.api_id, req.api_hash, req.phone_number, req.otp,
            req.target_group, req.promo_message, req.interval_seconds
        )
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
