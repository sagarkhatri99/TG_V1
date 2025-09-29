from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from database import get_db
import models
from routers.auth import get_current_user
from pydantic import BaseModel
from core.dependencies import plan_based_dependency

router = APIRouter()

class AdminStats(BaseModel):
    total_users: int
    active_users: int
    total_accounts: int
    total_jobs: int
    plan_distribution: dict

class UserUpdate(BaseModel):
    email: str
    subscription_plan: str

class UserResponse(BaseModel):
    id: int
    email: str
    subscription_plan: str
    created_at: str
    telegram_accounts_count: int = 0
    jobs_count: int = 0
    
    class Config:
        orm_mode = True

@router.get("/stats", response_model=AdminStats)
def get_admin_stats(
    current_admin: models.User = Depends(plan_based_dependency("admin_panel")),
    db: Session = Depends(get_db)
):
    """Get admin statistics"""
    total_users = db.query(models.User).count()
    active_users = db.query(models.User).filter(
        models.User.subscription_plan != 'free'
    ).count()
    total_accounts = db.query(models.TelegramAccount).count()
    total_jobs = db.query(models.Job).count()
    
    # Plan distribution
    plan_counts = db.query(
        models.User.subscription_plan,
        func.count(models.User.id)
    ).group_by(models.User.subscription_plan).all()
    
    plan_distribution = {'free': 0, 'pro': 0, 'enterprise': 0}
    for plan, count in plan_counts:
        if plan in plan_distribution:
            plan_distribution[plan] = count
    
    return AdminStats(
        total_users=total_users,
        active_users=active_users,
        total_accounts=total_accounts,
        total_jobs=total_jobs,
        plan_distribution=plan_distribution
    )

@router.get("/users")
def get_all_users(
    current_admin: models.User = Depends(plan_based_dependency("admin_panel")),
    db: Session = Depends(get_db)
):
    """Get all users with their counts"""
    users = db.query(models.User).all()
    
    user_list = []
    for user in users:
        accounts_count = db.query(models.TelegramAccount).filter(
            models.TelegramAccount.user_id == user.id
        ).count()
        
        jobs_count = db.query(models.Job).filter(
            models.Job.user_id == user.id
        ).count()
        
        user_data = {
            "id": user.id,
            "email": user.email,
            "subscription_plan": user.subscription_plan,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "telegram_accounts_count": accounts_count,
            "jobs_count": jobs_count,
        }
        user_list.append(user_data)
    
    return {"users": user_list}

@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_admin: models.User = Depends(plan_based_dependency("admin_panel")),
    db: Session = Depends(get_db)
):
    """Update user subscription plan"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate subscription plan
    valid_plans = ['free', 'pro', 'enterprise', 'admin']
    if user_update.subscription_plan not in valid_plans:
        raise HTTPException(status_code=400, detail="Invalid subscription plan")
    
    user.email = user_update.email
    user.subscription_plan = user_update.subscription_plan
    db.commit()
    
    return {"message": "User updated successfully"}

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    current_admin: models.User = Depends(plan_based_dependency("admin_panel")),
    db: Session = Depends(get_db)
):
    """Delete a user and all associated data"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent admin from deleting themselves
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    # Delete associated data first
    db.query(models.Job).filter(models.Job.user_id == user_id).delete()
    db.query(models.TelegramAccount).filter(models.TelegramAccount.user_id == user_id).delete()
    
    # Delete user
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted successfully"}

@router.post("/users")
def create_user(
    user_data: UserUpdate,
    current_admin: models.User = Depends(plan_based_dependency("admin_panel")),
    db: Session = Depends(get_db)
):
    """Create a new user"""
    # Check if email already exists
    existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user with default password (they'll need to reset)
    from core.security import get_password_hash
    hashed_password = get_password_hash("defaultpassword123")
    
    new_user = models.User(
        email=user_data.email,
        password_hash=hashed_password,
        subscription_plan=user_data.subscription_plan
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "User created successfully", "user_id": new_user.id}