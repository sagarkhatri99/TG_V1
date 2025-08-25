# mass_dm_account/router.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from .service import start_dm_auth, send_mass_dm_account_with_otp
import io

router = APIRouter()

class StartDMAuthRequest(BaseModel):
    api_id: int
    api_hash: str
    phone_number: str

@router.post("/start-auth")
async def start_auth(request: StartDMAuthRequest):
    try:
        await start_dm_auth(request.api_id, request.api_hash, request.phone_number)
        return {"success": True, "message": "OTP sent to your phone"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/send")
async def send_dm_with_otp(
    api_id: int = Form(...),
    api_hash: str = Form(...),
    phone_number: str = Form(...),
    otp: str = Form(...),
    message: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        # Convert UploadFile to file-like object for pandas
        content = await file.read()
        csv_file = io.StringIO(content.decode('utf-8'))
        
        result = await send_mass_dm_account_with_otp(
            api_id, api_hash, phone_number, otp, csv_file, message
        )
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
