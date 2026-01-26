from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime
import json

from database import get_db
from models import Campaign, CampaignUserInteraction, User, TelegramAccount, Job, CampaignLog
from routers.auth import get_current_user
from core.dependencies import plan_based_dependency
from celery_app import celery_app

router = APIRouter(
    prefix="/api/campaigns",
    tags=["Campaigns"]
)

@router.get("/", response_model=dict)
def list_campaigns(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("campaigns_read"))
):
    """
    List all campaigns for the current user.
    """
    query = db.query(Campaign).filter(Campaign.user_id == current_user.id)

    if status_filter:
        query = query.filter(Campaign.status == status_filter)

    campaigns = query.order_by(desc(Campaign.created_at)).all()

    # Format response
    results = []
    for c in campaigns:
        # Calculate stats
        total = c.total_targets
        sent = c.sent_count
        failed = c.failed_count
        replies = c.reply_count
        progress = (sent / total * 100) if total > 0 else 0

        results.append({
            "id": c.id,
            "name": c.name,
            "status": c.status,
            "account_nickname": c.account.nickname if c.account else "Unknown",
            "progress": round(progress, 1),
            "sent_count": sent,
            "total_targets": total,
            "failed_count": failed,
            "reply_count": replies,
            "created_at": c.created_at,
            "start_at": c.start_at,
            "end_at": c.end_at
        })

    return {"campaigns": results}

@router.post("/", response_model=dict)
def create_campaign(
    campaign_data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("campaigns_write"))
):
    """
    Create a new campaign.
    """
    # Validation
    account_id = campaign_data.get("telegram_account_id")
    account = db.query(TelegramAccount).filter(
        TelegramAccount.id == account_id,
        TelegramAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Telegram account not found")

    if account.status != "active":
        raise HTTPException(status_code=400, detail="Telegram account must be active")

    # Create Campaign
    new_campaign = Campaign(
        user_id=current_user.id,
        telegram_account_id=account_id,
        name=campaign_data.get("name"),
        message_templates=campaign_data.get("message_templates", []), # List of templates for phases
        target_group_id=campaign_data.get("target_group_id"),
        min_delay=campaign_data.get("min_delay", 30),
        max_delay=campaign_data.get("max_delay", 120),
        daily_limit=campaign_data.get("daily_limit"),
        status="draft"
    )

    db.add(new_campaign)
    db.commit()
    db.refresh(new_campaign)

    # Process initial targets if provided (e.g., from scraping)
    initial_targets = campaign_data.get("targets", [])
    if initial_targets:
        for target in initial_targets:
            interaction = CampaignUserInteraction(
                campaign_id=new_campaign.id,
                target_user_id=str(target.get("user_id")),
                target_username=target.get("username"),
                telegram_first_name=target.get("first_name"),
                status="pending",
                current_phase="A"
            )
            db.add(interaction)

        new_campaign.total_targets = len(initial_targets)
        db.commit()

    return {"id": new_campaign.id, "message": "Campaign created successfully"}

@router.get("/{campaign_id}", response_model=dict)
def get_campaign_details(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("campaigns_read"))
):
    """
    Get detailed info about a specific campaign.
    """
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.user_id == current_user.id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return {
        "id": campaign.id,
        "name": campaign.name,
        "status": campaign.status,
        "telegram_account_id": campaign.telegram_account_id,
        "account_nickname": campaign.account.nickname if campaign.account else "Unknown",
        "message_templates": campaign.message_templates,
        "settings": {
            "min_delay": campaign.min_delay,
            "max_delay": campaign.max_delay,
            "daily_limit": campaign.daily_limit,
            "target_group_id": campaign.target_group_id
        },
        "stats": {
            "total": campaign.total_targets,
            "sent": campaign.sent_count,
            "failed": campaign.failed_count,
            "replies": campaign.reply_count,
            "pending": campaign.total_targets - (campaign.sent_count + campaign.failed_count)
        },
        "created_at": campaign.created_at,
        "logs": [
            {
                "created_at": log.created_at,
                "action": log.action,
                "details": log.details
            } for log in db.query(CampaignLog).filter(
                CampaignLog.campaign_id == campaign.id
            ).order_by(desc(CampaignLog.created_at)).limit(50).all()
        ]
    }

@router.put("/{campaign_id}")
def update_campaign(
    campaign_id: int,
    update_data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("campaigns_write"))
):
    """
    Update campaign settings. Only allowed if campaign is not running.
    """
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.user_id == current_user.id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status in ["running", "stopping"]:
        raise HTTPException(status_code=400, detail="Cannot update a running campaign. Pause it first.")

    # Update fields
    if "name" in update_data:
        campaign.name = update_data["name"]
    if "message_templates" in update_data:
        campaign.message_templates = update_data["message_templates"]
    if "min_delay" in update_data:
        campaign.min_delay = update_data["min_delay"]
    if "max_delay" in update_data:
        campaign.max_delay = update_data["max_delay"]
    if "daily_limit" in update_data:
        campaign.daily_limit = update_data["daily_limit"]

    db.commit()
    return {"message": "Campaign updated successfully"}

@router.delete("/{campaign_id}")
def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("campaigns_write"))
):
    """
    Delete a campaign and its associated data (logs, interactions).
    """
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.user_id == current_user.id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # If running, stop it first (logic to kill tasks would go here, simplified for now)
    if campaign.status == "running":
        # In a real scenario, we'd revoke Celery tasks here
        pass

    # Cascading delete is handled by database foreign keys usually,
    # but explicit delete ensures clean cleanup if not set up
    db.query(CampaignLog).filter(CampaignLog.campaign_id == campaign_id).delete()
    db.query(CampaignUserInteraction).filter(CampaignUserInteraction.campaign_id == campaign_id).delete()

    db.delete(campaign)
    db.commit()

    return {"message": "Campaign deleted successfully"}

@router.post("/{campaign_id}/start")
def start_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("campaigns_write"))
):
    """
    Start or resume a campaign.
    """
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.user_id == current_user.id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status == "running":
        return {"message": "Campaign is already running"}

    if not campaign.message_templates:
        raise HTTPException(status_code=400, detail="Campaign needs message templates configured")

    # Account check
    account = db.query(TelegramAccount).filter(TelegramAccount.id == campaign.telegram_account_id).first()
    if not account or account.status != "active":
         raise HTTPException(status_code=400, detail="Campaign account is not active")

    # Update status
    campaign.status = "running"
    if not campaign.start_at:
        campaign.start_at = datetime.utcnow()

    db.commit()

    # Dispatch Celery Task
    # Note: We import task name as string to avoid circular imports if strictly typed,
    # or ensure tasks are loaded. Here we use send_task or import.
    celery_app.send_task("tasks.campaign_tasks.start_campaign_task", args=[campaign.id])

    return {"message": "Campaign started", "status": "running"}

@router.post("/{campaign_id}/pause")
def pause_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("campaigns_write"))
):
    """
    Pause a running campaign.
    """
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.user_id == current_user.id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status != "running":
        return {"message": "Campaign is not running"}

    campaign.status = "paused"
    db.commit()

    return {"message": "Campaign paused", "status": "paused"}

@router.post("/{campaign_id}/resume")
def resume_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("campaigns_write"))
):
    """
    Resume a paused campaign.
    """
    return start_campaign(campaign_id, db, current_user)

@router.get("/{campaign_id}/interactions")
def get_campaign_interactions(
    campaign_id: int,
    status_filter: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(plan_based_dependency("campaigns_read"))
):
    """
    Get paginated interactions (targets) for a campaign.
    """
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.user_id == current_user.id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    query = db.query(CampaignUserInteraction).filter(
        CampaignUserInteraction.campaign_id == campaign_id
    )

    if status_filter:
        query = query.filter(CampaignUserInteraction.status == status_filter)

    total = query.count()
    interactions = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "interactions": interactions
    }
