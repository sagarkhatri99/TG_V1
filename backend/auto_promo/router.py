# auto_promo/router.py
from fastapi import APIRouter, HTTPException, Form
from .service import start_auto_promo_auth, verify_and_start_promo

router = APIRouter()

@router.post("/start-auth")
async def start_auth(
    api_id: int = Form(...),
    api_hash: str = Form(...),
    phone_number: str = Form(...)
):
    try:
        await start_auto_promo_auth(api_id, api_hash, phone_number)
        return {"success": True, "message": "OTP sent to your phone"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/start")
async def start_promo(
    api_id: int = Form(...),
    api_hash: str = Form(...),
    phone_number: str = Form(...),
    otp: str = Form(...),
    target_group: str = Form(...),
    promo_message: str = Form(...),
    interval_seconds: int = Form(...)
):
    try:
        result = await verify_and_start_promo(
            api_id, api_hash, phone_number, otp,
            target_group, promo_message, interval_seconds
        )
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
