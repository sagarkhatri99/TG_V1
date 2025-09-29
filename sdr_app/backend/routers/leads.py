from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, desc
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from database import get_db
from models import Lead, LeadProfile, User
from routers.auth import get_current_user

router = APIRouter()


def check_lead_profile_access(user: User) -> None:
    allowed_plans = ['enterprise', 'admin']
    if user.subscription_plan not in allowed_plans:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Lead profiles feature is only available for Enterprise plan users. Current plan: {user.subscription_plan}"
        )

class LeadCreate(BaseModel):
    lead_profile_id: int
    telegram_user_id: Optional[str] = None
    telegram_username: Optional[str] = None
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = None
    profile_match_keywords: Optional[str] = None
    relevance_score: Optional[float] = Field(0.0, ge=0.0, le=100.0)
    source_group: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None

class LeadUpdate(BaseModel):
    telegram_user_id: Optional[str] = None
    telegram_username: Optional[str] = None
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = None
    profile_match_keywords: Optional[str] = None
    relevance_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    conversation_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    status: Optional[str] = Field(None, pattern="^(discovered|contacted|replied|qualified|converted|dead)$")
    last_contacted_at: Optional[datetime] = None
    last_reply_at: Optional[datetime] = None
    source_group: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None

class LeadResponse(BaseModel):
    id: int
    user_id: int
    lead_profile_id: int
    lead_profile_name: str
    telegram_user_id: Optional[str]
    telegram_username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    bio: Optional[str]
    profile_match_keywords: Optional[str]
    relevance_score: float
    conversation_score: float
    status: str
    last_contacted_at: Optional[datetime]
    last_reply_at: Optional[datetime]
    source_group: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class LeadBulkCreate(BaseModel):
    lead_profile_id: int
    leads: List[LeadCreate]

@router.post("/", response_model=LeadResponse)
def create_lead(
    lead_data: LeadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_lead_profile_access(current_user)
    lead_profile = db.query(LeadProfile).filter(
        LeadProfile.id == lead_data.lead_profile_id,
        LeadProfile.user_id == current_user.id
    ).first()
    if not lead_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead profile not found")
    existing_conditions = []
    if lead_data.telegram_user_id:
        existing_conditions.append(Lead.telegram_user_id == lead_data.telegram_user_id)
    if lead_data.telegram_username:
        existing_conditions.append(Lead.telegram_username == lead_data.telegram_username)
    if existing_conditions:
        existing = db.query(Lead).filter(
            Lead.lead_profile_id == lead_data.lead_profile_id,
            or_(*existing_conditions)
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A lead with this Telegram user ID or username already exists in this profile")
    lead = Lead(user_id=current_user.id, **lead_data.dict())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    lead.lead_profile_name = lead_profile.name
    return lead

@router.post("/bulk")
def create_leads_bulk(
    bulk_data: LeadBulkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_lead_profile_access(current_user)
    lead_profile = db.query(LeadProfile).filter(
        LeadProfile.id == bulk_data.lead_profile_id,
        LeadProfile.user_id == current_user.id
    ).first()
    if not lead_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead profile not found")
    created_leads = []
    errors = []
    for i, lead_data in enumerate(bulk_data.leads):
        try:
            duplicate_in_batch = any(
                (lead_data.telegram_user_id and lead_data.telegram_user_id == other.telegram_user_id) or
                (lead_data.telegram_username and lead_data.telegram_username == other.telegram_username)
                for other in bulk_data.leads[:i]
            )
            if duplicate_in_batch:
                errors.append(f"Lead {i+1}: Duplicate within batch")
                continue
            existing_conditions = []
            if lead_data.telegram_user_id:
                existing_conditions.append(Lead.telegram_user_id == lead_data.telegram_user_id)
            if lead_data.telegram_username:
                existing_conditions.append(Lead.telegram_username == lead_data.telegram_username)
            if existing_conditions:
                existing = db.query(Lead).filter(
                    Lead.lead_profile_id == bulk_data.lead_profile_id,
                    or_(*existing_conditions)
                ).first()
                if existing:
                    errors.append(f"Lead {i+1}: Already exists")
                    continue
            lead = Lead(user_id=current_user.id, lead_profile_id=bulk_data.lead_profile_id, **lead_data.dict())
            db.add(lead)
            db.flush()
            lead.lead_profile_name = lead_profile.name
            created_leads.append(lead)
        except Exception as e:
            errors.append(f"Lead {i+1}: {str(e)}")
    if created_leads:
        db.commit()
        for lead in created_leads:
            db.refresh(lead)
    if errors:
        return {"created_leads": created_leads, "errors": errors, "total_attempted": len(bulk_data.leads), "total_created": len(created_leads)}
    return created_leads

@router.get("/", response_model=List[LeadResponse])
def list_leads(
    skip: int = 0,
    limit: int = 100,
    lead_profile_id: Optional[int] = None,
    status: Optional[str] = Query(None, pattern="^(discovered|contacted|replied|qualified|converted|dead)$"),
    min_relevance_score: Optional[float] = Query(None, ge=0.0, le=100.0),
    search: Optional[str] = None,
    sort_by: str = Query("created_at", pattern="^(created_at|updated_at|relevance_score|conversation_score)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_lead_profile_access(current_user)
    query = db.query(Lead, LeadProfile.name.label("lead_profile_name")).join(
        LeadProfile, Lead.lead_profile_id == LeadProfile.id
    ).filter(Lead.user_id == current_user.id)
    if lead_profile_id:
        query = query.filter(Lead.lead_profile_id == lead_profile_id)
    if status:
        query = query.filter(Lead.status == status)
    if min_relevance_score is not None:
        query = query.filter(Lead.relevance_score >= min_relevance_score)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Lead.first_name.ilike(search_term),
                Lead.last_name.ilike(search_term),
                Lead.telegram_username.ilike(search_term),
                Lead.bio.ilike(search_term),
                Lead.notes.ilike(search_term),
                LeadProfile.name.ilike(search_term)
            )
        )
    sort_column = getattr(Lead, sort_by)
    query = query.order_by(desc(sort_column) if sort_order == "desc" else sort_column)
    results = query.offset(skip).limit(limit).all()
    leads = []
    for lead, profile_name in results:
        lead.lead_profile_name = profile_name
        leads.append(lead)
    return leads

@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_lead_profile_access(current_user)
    lead = db.query(Lead, LeadProfile.name.label("lead_profile_name")).join(
        LeadProfile, Lead.lead_profile_id == LeadProfile.id
    ).filter(Lead.id == lead_id, Lead.user_id == current_user.id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    lead_obj, profile_name = lead
    lead_obj.lead_profile_name = profile_name
    return lead_obj

@router.put("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: int,
    lead_update: LeadUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_lead_profile_access(current_user)
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.user_id == current_user.id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    if lead_update.telegram_user_id or lead_update.telegram_username:
        existing_conditions = []
        if lead_update.telegram_user_id:
            existing_conditions.append(Lead.telegram_user_id == lead_update.telegram_user_id)
        if lead_update.telegram_username:
            existing_conditions.append(Lead.telegram_username == lead_update.telegram_username)
        existing = db.query(Lead).filter(
            Lead.lead_profile_id == lead.lead_profile_id,
            Lead.id != lead_id,
            or_(*existing_conditions)
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A lead with this Telegram user ID or username already exists in this profile")
    update_data = lead_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lead, field, value)
    lead.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(lead)
    lead_profile = db.query(LeadProfile).filter(LeadProfile.id == lead.lead_profile_id).first()
    lead.lead_profile_name = lead_profile.name
    return lead

@router.delete("/{lead_id}")
def delete_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_lead_profile_access(current_user)
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.user_id == current_user.id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    db.delete(lead)
    db.commit()
    return {"message": "Lead deleted successfully"}

@router.get("/profile/{profile_id}/stats")
def get_leads_stats_by_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_lead_profile_access(current_user)
    lead_profile = db.query(LeadProfile).filter(LeadProfile.id == profile_id, LeadProfile.user_id == current_user.id).first()
    if not lead_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead profile not found")
    stats = db.query(
        func.count(Lead.id).label('total_leads'),
        func.count().filter(Lead.status == 'discovered').label('discovered'),
        func.count().filter(Lead.status == 'contacted').label('contacted'),
        func.count().filter(Lead.status == 'replied').label('replied'),
        func.count().filter(Lead.status == 'qualified').label('qualified'),
        func.count().filter(Lead.status == 'converted').label('converted'),
        func.count().filter(Lead.status == 'dead').label('dead'),
        func.avg(Lead.relevance_score).label('avg_relevance_score'),
        func.avg(Lead.conversation_score).label('avg_conversation_score'),
        func.max(Lead.relevance_score).label('max_relevance_score'),
        func.min(Lead.relevance_score).label('min_relevance_score')
    ).filter(Lead.lead_profile_id == profile_id).first()
    from datetime import timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_stats = db.query(
        func.count(Lead.id).label('recent_leads'),
        func.count().filter(Lead.last_contacted_at >= thirty_days_ago).label('recently_contacted'),
        func.count().filter(Lead.last_reply_at >= thirty_days_ago).label('recent_replies')
    ).filter(Lead.lead_profile_id == profile_id, Lead.created_at >= thirty_days_ago).first()
    total = stats.total_leads or 0
    conversion_funnel = {
        "discovered_to_contacted": round((stats.contacted / total * 100), 2) if total > 0 else 0,
        "contacted_to_replied": round((stats.replied / stats.contacted * 100), 2) if stats.contacted > 0 else 0,
        "replied_to_qualified": round((stats.qualified / stats.replied * 100), 2) if stats.replied > 0 else 0,
        "qualified_to_converted": round((stats.converted / stats.qualified * 100), 2) if stats.qualified > 0 else 0,
        "overall_conversion": round((stats.converted / total * 100), 2) if total > 0 else 0
    }
    return {
        "profile_id": profile_id,
        "profile_name": lead_profile.name,
        "total_leads": total,
        "leads_by_status": {
            "discovered": stats.discovered or 0,
            "contacted": stats.contacted or 0,
            "replied": stats.replied or 0,
            "qualified": stats.qualified or 0,
            "converted": stats.converted or 0,
            "dead": stats.dead or 0
        },
        "relevance_scores": {
            "average": round(float(stats.avg_relevance_score or 0), 2),
            "maximum": float(stats.max_relevance_score or 0),
            "minimum": float(stats.min_relevance_score or 0)
        },
        "average_conversation_score": round(float(stats.avg_conversation_score or 0), 2),
        "conversion_funnel": conversion_funnel,
        "recent_activity": {
            "new_leads_30d": recent_stats.recent_leads or 0,
            "contacted_30d": recent_stats.recently_contacted or 0,
            "replies_30d": recent_stats.recent_replies or 0
        },
        "profile_created_at": lead_profile.created_at,
        "last_updated": lead_profile.updated_at
    }
