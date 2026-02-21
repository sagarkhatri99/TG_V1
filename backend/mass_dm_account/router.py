from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from models import Job, TelegramAccount, User
from database import get_db
from routers.auth import get_current_user
from core.dependencies import plan_based_dependency
from core.logging import get_logger
from slowapi import Limiter
from slowapi.util import get_remote_address
import json
from pydantic import BaseModel
from typing import Optional
import shutil
import os
from .tasks import mass_dm_account_task
from .distribution_service import distribute_users_across_accounts
from datetime import datetime, timedelta
import csv
import io

logger = get_logger(__name__)
limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

class MassDMAccountRequest(BaseModel):
    account_id: int
    message: str
    stop_after_hours: Optional[int] = None

class DistributedMassDMRequest(BaseModel):
    message: str
    account_ids: list[int]
    stop_after_hours: Optional[int] = None
    rate_limit_per_hour: Optional[int] = None
    delay_seconds: Optional[int] = None
    min_delay_seconds: Optional[int] = None
    max_delay_seconds: Optional[int] = None
    user_description: Optional[str] = None

@router.post("/create-distributed-job")
@limiter.limit("10/minute")
async def create_distributed_mass_dm_job(
    request: Request,
    message: str = Form(...),
    account_ids: str = Form(...),  # JSON string of account IDs
    user_description: Optional[str] = Form(None),
    stop_after_hours: Optional[int] = Form(None),
    rate_limit_per_hour: Optional[int] = Form(None),
    delay_seconds: Optional[int] = Form(None),
    min_delay_seconds: Optional[int] = Form(None),
    max_delay_seconds: Optional[int] = Form(None),
    csv_file: UploadFile = File(...),
    image_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("mass_dm"))
):
    """
    Create distributed mass DM jobs across multiple accounts.
    Automatically splits the user list evenly across selected accounts.
    """
    try:
        # Parse account IDs from JSON string
        selected_account_ids = json.loads(account_ids)
        if not isinstance(selected_account_ids, list) or len(selected_account_ids) < 2:
            raise HTTPException(status_code=400, detail="Please select at least 2 accounts for distribution")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid account_ids format")

    # Check subscription limits
    if current_user.subscription_plan == 'pro':
        if current_user.job_counter_last_reset < datetime.utcnow() - timedelta(days=30):
            current_user.jobs_created_this_month = 0
            current_user.job_counter_last_reset = datetime.utcnow()
            db.commit()
        # Each batch counts as a job
        if current_user.jobs_created_this_month + len(selected_account_ids) > 500:
            raise HTTPException(status_code=403, detail="You would exceed your monthly job limit of 500.")

    # Parse CSV to get user IDs
    try:
        csv_content = await csv_file.read()
        csv_file.file.seek(0)
        csv_text = csv_content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_text))
        
        user_ids = []
        for row in csv_reader:
            # Handle both old (capitalized) and new (lowercase) formats
            if 'user_id' in row and row['user_id']:
                user_ids.append(row['user_id'].strip())
            elif 'User ID' in row and row['User ID']:
                user_ids.append(row['User ID'].strip())
            elif 'username' in row and row['username']:
                user_ids.append(row['username'].strip())
            elif 'Username' in row and row['Username']:
                user_ids.append(row['Username'].strip())
        
        if not user_ids:
            raise HTTPException(status_code=400, detail="CSV file must contain user_id or username column with data")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")

    try:
        # Distribute users across accounts
        created_job_ids, total_users, users_per_batch = distribute_users_across_accounts(
            user_ids, selected_account_ids, current_user, db
        )
        
        # Now update each created job with the full config and save files
        upload_dir = "/app/uploads"
        os.makedirs(upload_dir, exist_ok=True)

        job_config = {
            "message": message,
            "stop_after_hours": stop_after_hours,
            "rate_limit_per_hour": rate_limit_per_hour,
            "delay_seconds": delay_seconds,
            "min_delay_seconds": min_delay_seconds,
            "max_delay_seconds": max_delay_seconds,
            "distributed": True,  # Mark as distributed
        }

        # Handle image file if provided
        image_file_path = None
        if image_file:
            image_file_path = os.path.join(upload_dir, f"mass_dm_distributed_image_{image_file.filename}")
            try:
                with open(image_file_path, "wb") as buffer:
                    shutil.copyfileobj(image_file.file, buffer)
                job_config["image_file_path"] = image_file_path
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to save image file: {e}")

        # Update each batch job with config and dispatch tasks
        for job_id in created_job_ids:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.config = json.dumps(job_config)
                db.commit()
                # Dispatch the task to workers
                mass_dm_account_task.delay(job_id)

        # Update job counter for pro users
        if current_user.subscription_plan == 'pro':
            current_user.jobs_created_this_month += len(created_job_ids)
            db.commit()

        return {
            "success": True,
            "message": f"Created {len(created_job_ids)} distributed Mass DM jobs",
            "job_ids": created_job_ids,
            "total_users": total_users,
            "num_accounts": len(selected_account_ids),
            "users_per_batch": users_per_batch,
            "distribution_summary": {
                "total_users": total_users,
                "total_accounts": len(selected_account_ids),
                "users_per_account": users_per_batch,
                "last_account_users": total_users - (users_per_batch * (len(selected_account_ids) - 1)),
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create distributed jobs: {str(e)}")

@router.post("/create-job")
@limiter.limit("10/minute")
async def create_mass_dm_account_job(
    request: Request,
    account_id: int = Form(...),
    message: Optional[str] = Form(None),  # Now optional if template_id is provided
    template_id: Optional[int] = Form(None),  # NEW: Template ID for message generation
    user_description: Optional[str] = Form(None),
    stop_after_hours: Optional[int] = Form(None),
    rate_limit_per_hour: Optional[int] = Form(None),
    delay_seconds: Optional[int] = Form(None),
    min_delay_seconds: Optional[int] = Form(None),
    max_delay_seconds: Optional[int] = Form(None),
    csv_file: UploadFile = File(...),
    image_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("mass_dm"))
):
    # Validate either message or template_id is provided
    if not message and not template_id:
        raise HTTPException(
            status_code=400, 
            detail="Either 'message' or 'template_id' must be provided"
        )
    if current_user.subscription_plan == 'pro':
        if current_user.job_counter_last_reset < datetime.utcnow() - timedelta(days=30):
            current_user.jobs_created_this_month = 0
            current_user.job_counter_last_reset = datetime.utcnow()
            db.commit()
        if current_user.jobs_created_this_month >= 500:
            raise HTTPException(status_code=403, detail="You have reached your monthly job limit of 500.")

    account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id, TelegramAccount.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found or not owned by user")
    
    # If template_id is provided, fetch and validate it
    if template_id:
        from models import MessageTemplate
        template = db.query(MessageTemplate).filter(
            MessageTemplate.id == template_id,
            MessageTemplate.user_id == current_user.id
        ).first()
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found or not owned by user")
        
        # Store template content for use in job config
        message = template.content  # Fallback for job config (will be regenerated per message)

    job_config = {
        "message": message,
        "template_id": template_id,  # NEW: Store template_id for message generation
        "stop_after_hours": stop_after_hours,
        "rate_limit_per_hour": rate_limit_per_hour,
        "delay_seconds": delay_seconds,
        "min_delay_seconds": min_delay_seconds,
        "max_delay_seconds": max_delay_seconds,
    }

    new_job = Job(
        user_id=current_user.id,
        telegram_account_id=account_id,
        job_type='mass_dm_account',
        config=json.dumps(job_config),
        status='pending',
        user_description=user_description
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    upload_dir = "/app/uploads"
    os.makedirs(upload_dir, exist_ok=True)

    # Handle CSV file
    csv_file_path = os.path.join(upload_dir, f"mass_dm_{new_job.id}.csv")
    try:
        with open(csv_file_path, "wb") as buffer:
            shutil.copyfileobj(csv_file.file, buffer)
        job_config["csv_file_path"] = csv_file_path
    except Exception as e:
        new_job.status = 'failed'
        new_job.error_message = f"Failed to save CSV file: {e}"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to save CSV file: {e}")

    # Handle optional image file
    if image_file:
        image_file_path = os.path.join(upload_dir, f"mass_dm_image_{new_job.id}_{image_file.filename}")
        try:
            with open(image_file_path, "wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)
            job_config["image_file_path"] = image_file_path
        except Exception as e:
            new_job.status = 'failed'
            new_job.error_message = f"Failed to save image file: {e}"
            db.commit()
            raise HTTPException(status_code=500, detail=f"Failed to save image file: {e}")

    # Update job config with file paths
    new_job.config = json.dumps(job_config)
    db.commit()

    # Step 4: Dispatch the task
    mass_dm_account_task.delay(new_job.id)

    return {"job_id": new_job.id, "message": "Mass DM Account job created successfully."}
