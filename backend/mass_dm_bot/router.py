from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from .service import send_mass_dm_bot

router = APIRouter()

@router.post("/")
async def mass_dm_bot_endpoint(
    bot_token: str = Form(...),
    message: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        result = await send_mass_dm_bot(bot_token, file.file, message)
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
