# group_monitor/router.py
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from fastapi.responses import StreamingResponse
import csv
import io
import datetime
from .service import start_monitor_auth, verify_monitor_otp_and_monitor

router = APIRouter()

class StartMonitorAuthRequest(BaseModel):
    api_id: int
    api_hash: str
    phone_number: str

class VerifyMonitorRequest(BaseModel):
    api_id: int
    api_hash: str
    phone_number: str
    code: str
    group_usernames: List[str]
    keywords: List[str]
    monitored_users: List[str]
    limit: Optional[int] = 100

@router.post("/start-auth")
async def start_auth(request: StartMonitorAuthRequest):
    try:
        await start_monitor_auth(request.api_id, request.api_hash, request.phone_number)
        return {"success": True, "message": "OTP sent to your phone"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/verify-monitor")
async def verify_monitor(request: VerifyMonitorRequest):
    try:
        result = await verify_monitor_otp_and_monitor(
            request.api_id,
            request.api_hash,
            request.phone_number,
            request.code,
            request.group_usernames,
            request.keywords,
            request.monitored_users,
            request.limit or 100
        )
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download")
def download_csv(phone_number: str = Query(...)):
    filename = f"monitored_messages_{phone_number.replace('+', '')}.csv"

    def file_iterator(file_path, chunk_size=8192):
        try:
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        except FileNotFoundError:
            # This allows the outer try-except to handle the 404
            raise

    try:
        return StreamingResponse(
            file_iterator(filename),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
