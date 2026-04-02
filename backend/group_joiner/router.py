"""Group Joiner router - accepts account selection + CSV of group links and creates a group_join job."""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from models import Job, TelegramAccount, User
from database import get_db
from routers.auth import get_current_user
from core.dependencies import plan_based_dependency
from slowapi import Limiter
from slowapi.util import get_remote_address
import json
import os
import shutil
from typing import Optional
from datetime import datetime
from .tasks import group_join_task

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def parse_group_links_from_csv(file_path: str) -> list[str]:
    """
    Extract and normalize Telegram group identifiers from a CSV.

    Accepts columns: group_link, group_url, username, link, group
    Normalizes:
      - https://t.me/groupname    → @groupname
      - t.me/groupname            → @groupname
      - @groupname                → @groupname (kept as-is)
      - groupname                 → @groupname

    Returns a deduplicated list of group handles.
    """
    import csv
    results = []
    seen = set()

    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        # Find the relevant column (case-insensitive first-match)
        col_priority = ['group_link', 'group_url', 'link', 'username', 'group', 'url']
        matched_col = None
        if reader.fieldnames:
            lower_fields = {c.lower(): c for c in reader.fieldnames}
            for c in col_priority:
                if c in lower_fields:
                    matched_col = lower_fields[c]
                    break

        if not matched_col:
            raise ValueError(
                f"CSV must have one of these columns: {', '.join(col_priority)}. "
                f"Found: {', '.join(reader.fieldnames or [])}"
            )

        for row in reader:
            raw = (row.get(matched_col) or '').strip()
            if not raw:
                continue

            # Normalize to bare @handle or numeric ID
            # Strip t.me/ or https://t.me/
            for prefix in ['https://t.me/', 'http://t.me/', 't.me/', 'https://telegram.me/', 'http://telegram.me/', 'telegram.me/']:
                if raw.lower().startswith(prefix):
                    raw = raw[len(prefix):]
                    break

            # Remove trailing slashes and query params
            raw = raw.split('?')[0].strip()
            if raw.endswith('/'):
                raw = raw[:-1]

            if raw.lower().startswith('joinchat/'):
                identifier = raw
            elif raw.startswith('+'):
                identifier = raw
            elif raw.lstrip('-').isdigit():
                identifier = raw  # keep numeric chat ID as-is
            elif raw.startswith('@'):
                identifier = raw
            else:
                # If there's a '/', it's not a simple username, but let's assume last part
                raw = raw.split('/')[-1]
                identifier = f'@{raw}'

            if identifier and identifier not in seen:
                seen.add(identifier)
                results.append(identifier)

    if not results:
        raise ValueError("No valid group links found in the CSV file.")

    return results


@router.post("/create-job")
@limiter.limit("10/minute")
async def create_group_join_job(
    request: Request,
    account_id: int = Form(...),
    user_description: Optional[str] = Form(None),
    min_delay_seconds: int = Form(30),
    max_delay_seconds: int = Form(60),
    csv_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("jobs_basic"))
):
    """
    Create a group join job from a CSV of group links/usernames.
    The CSV should have one group link per row in a column named:
    group_link, group_url, link, username, or group.
    """
    # Validate account ownership
    account = db.query(TelegramAccount).filter(
        TelegramAccount.id == account_id,
        TelegramAccount.user_id == current_user.id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found or not owned by user")

    # Save uploaded CSV
    upload_dir = "/app/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    csv_path = os.path.join(upload_dir, f"group_join_{current_user.id}_{int(datetime.utcnow().timestamp())}.csv")

    try:
        with open(csv_path, "wb") as f:
            shutil.copyfileobj(csv_file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save CSV: {e}")

    # Parse and validate the group links
    try:
        groups = parse_group_links_from_csv(csv_path)
    except ValueError as e:
        os.remove(csv_path)
        raise HTTPException(status_code=400, detail=str(e))

    job_config = {
        "csv_file_path": csv_path,
        "groups": groups,
        "min_delay_seconds": max(10, min_delay_seconds),
        "max_delay_seconds": max(10, max_delay_seconds),
    }

    new_job = Job(
        user_id=current_user.id,
        telegram_account_id=account_id,
        job_type='group_join',
        config=json.dumps(job_config),
        status='pending',
        messages_planned=len(groups),
        user_description=user_description or f"Join {len(groups)} groups"
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    group_join_task.delay(new_job.id)

    return {
        "job_id": new_job.id,
        "message": f"Group join job created for {len(groups)} group(s).",
        "groups_count": len(groups),
        "groups_preview": groups[:5]  # Show first 5 parsed groups for confirmation
    }
