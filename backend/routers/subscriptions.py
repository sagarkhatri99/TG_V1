"""
Admin Subscription Management Router

This router is strictly for the internal Admin Panel to manage user subscription plans.
It allows administrators to:
1. Upgrade/Downgrade user plans (Free, Pro, Enterprise).
2. Adjust billing cycles (Monthly, Annual).
3. Reset trial periods.

It uses the `plan_based_dependency("admin_panel")` to ensure only authorized admins can access these endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta

from database import get_db
import models
from routers.auth import get_current_user

router = APIRouter()

class SubscriptionUpdate(BaseModel):
    plan: str
    billing_cycle: str # 'monthly' or 'annual'

from core.dependencies import plan_based_dependency

@router.put("/{user_id}/update-subscription")
def update_subscription(
    user_id: int,
    subscription_update: SubscriptionUpdate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(plan_based_dependency("admin_panel"))
):
    user_to_update = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_to_update:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate plan
    valid_plans = ['free', 'pro', 'enterprise', 'admin']
    if subscription_update.plan not in valid_plans:
        raise HTTPException(status_code=400, detail="Invalid subscription plan")

    # Validate billing cycle
    valid_billing_cycles = ['monthly', 'annual']
    if subscription_update.billing_cycle not in valid_billing_cycles:
        raise HTTPException(status_code=400, detail="Invalid billing cycle")

    # Update user's subscription
    user_to_update.subscription_plan = subscription_update.plan
    user_to_update.billing_cycle = subscription_update.billing_cycle

    # Set trial end date for new Pro and Enterprise users
    if subscription_update.plan in ['pro', 'enterprise'] and not user_to_update.trial_end_date:
        user_to_update.trial_end_date = datetime.utcnow() + timedelta(days=14)

    db.commit()
    db.refresh(user_to_update)

    return {"message": "Subscription updated successfully"}
