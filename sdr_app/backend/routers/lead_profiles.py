from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from database import get_db
from models import LeadProfile, User
from routers.auth import get_current_user

router = APIRouter()

class LeadProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    keywords: Optional[str] = Field(None, description="Comma-separated keywords to match in bios/posts")
    industry: Optional[str] = Field(None, max_length=100)
    interests: Optional[str] = Field(None, description="Comma-separated interests")
    regions: Optional[str] = Field(None, max_length=255, description="Comma-separated regions")
    description: Optional[str] = Field(None, description="Description of target audience")
    target_groups: Optional[str] = Field(None, description="Telegram group/channel IDs or usernames")

class LeadProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    keywords: Optional[str] = None
    industry: Optional[str] = Field(None, max_length=100)
    interests: Optional[str] = None
    regions: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    target_groups: Optional[str] = None
    is_active: Optional[bool] = None

class LeadProfileResponse(BaseModel):
    id: int
    user_id: int
    name: str
    keywords: Optional[str]
    industry: Optional[str]
    interests: Optional[str]
    regions: Optional[str]
    description: Optional[str]
    target_groups: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


def check_lead_profile_access(user: User) -> None:
    allowed_plans = ['enterprise', 'admin']
    if user.subscription_plan not in allowed_plans:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Lead profiles feature is only available for Enterprise plan users. Current plan: {user.subscription_plan}"
        )

@router.post("/", response_model=LeadProfileResponse)
def create_lead_profile(
    profile_data: LeadProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_lead_profile_access(current_user)
    existing = db.query(LeadProfile).filter(
        LeadProfile.user_id == current_user.id,
        LeadProfile.name == profile_data.name
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A lead profile with this name already exists")
    lead_profile = LeadProfile(user_id=current_user.id, **profile_data.dict())
    db.add(lead_profile)
    db.commit()
    db.refresh(lead_profile)
    return lead_profile

@router.get("/", response_model=List[LeadProfileResponse])
def list_lead_profiles(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_lead_profile_access(current_user)
    query = db.query(LeadProfile).filter(LeadProfile.user_id == current_user.id)
    if active_only:
        query = query.filter(LeadProfile.is_active == True)
    lead_profiles = query.offset(skip).limit(limit).all()
    return lead_profiles

@router.get("/{profile_id}", response_model=LeadProfileResponse)
def get_lead_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_lead_profile_access(current_user)
    lead_profile = db.query(LeadProfile).filter(
        LeadProfile.id == profile_id,
        LeadProfile.user_id == current_user.id
    ).first()
    if not lead_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead profile not found")
    return lead_profile

@router.put("/{profile_id}", response_model=LeadProfileResponse)
def update_lead_profile(
    profile_id: int,
    profile_update: LeadProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_lead_profile_access(current_user)
    lead_profile = db.query(LeadProfile).filter(
        LeadProfile.id == profile_id,
        LeadProfile.user_id == current_user.id
    ).first()
    if not lead_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead profile not found")
    if profile_update.name and profile_update.name != lead_profile.name:
        existing = db.query(LeadProfile).filter(
            LeadProfile.user_id == current_user.id,
            LeadProfile.name == profile_update.name,
            LeadProfile.id != profile_id
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A lead profile with this name already exists")
    update_data = profile_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lead_profile, field, value)
    lead_profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(lead_profile)
    return lead_profile

@router.delete("/{profile_id}")
def delete_lead_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_lead_profile_access(current_user)
    lead_profile = db.query(LeadProfile).filter(
        LeadProfile.id == profile_id,
        LeadProfile.user_id == current_user.id
    ).first()
    if not lead_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead profile not found")
    db.delete(lead_profile)
    db.commit()
    return {"message": "Lead profile deleted successfully"}

@router.get("/{profile_id}/stats")
def get_lead_profile_stats(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_lead_profile_access(current_user)
    from models import Lead
    from sqlalchemy import func
    lead_profile = db.query(LeadProfile).filter(
        LeadProfile.id == profile_id,
        LeadProfile.user_id == current_user.id
    ).first()
    if not lead_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead profile not found")
    lead_stats = db.query(
        func.count(Lead.id).label('total_leads'),
        func.count().filter(Lead.status == 'discovered').label('discovered'),
        func.count().filter(Lead.status == 'contacted').label('contacted'),
        func.count().filter(Lead.status == 'replied').label('replied'),
        func.count().filter(Lead.status == 'qualified').label('qualified'),
        func.count().filter(Lead.status == 'converted').label('converted'),
        func.avg(Lead.relevance_score).label('avg_relevance_score')
    ).filter(Lead.lead_profile_id == profile_id).first()
    return {
        "profile_id": profile_id,
        "profile_name": lead_profile.name,
        "total_leads": lead_stats.total_leads or 0,
        "leads_by_status": {
            "discovered": lead_stats.discovered or 0,
            "contacted": lead_stats.contacted or 0,
            "replied": lead_stats.replied or 0,
            "qualified": lead_stats.qualified or 0,
            "converted": lead_stats.converted or 0
        },
        "average_relevance_score": round(float(lead_stats.avg_relevance_score or 0), 2),
        "created_at": lead_profile.created_at,
        "last_updated": lead_profile.updated_at
    }
