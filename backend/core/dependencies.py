from fastapi import Depends, HTTPException, status
from models import User
from routers.auth import get_current_user

# Define feature access levels for each plan
PLAN_FEATURES = {
    "free": ["dashboard", "accounts", "settings", "help", "jobs_basic"],
    # Include both 'jobs' and 'jobs_basic' to satisfy endpoints that depend on either
    "pro": [
        "dashboard", "accounts", "settings", "help", "jobs", "jobs_basic", "scrape", "monitor",
        "mass_dm", "auto_promo", "proxies", "ban_prevention"
    ],
    "enterprise": [
        "dashboard", "accounts", "settings", "help", "jobs", "jobs_basic", "scrape", "monitor",
        "mass_dm", "auto_promo", "proxies", "ban_prevention", "ai_scoring"
    ],
    # Admins should have access to all features, including the admin panel
    "admin": [
        "dashboard", "accounts", "settings", "help", "jobs", "jobs_basic", "scrape",
        "monitor", "mass_dm", "auto_promo", "proxies", "ban_prevention", "ai_scoring",
        "admin_panel"
    ]
}

def plan_based_dependency(required_feature: str):
    def get_current_user_with_plan(
        current_user: User = Depends(get_current_user)
    ):
        """
        Dependency to get the current user and check if their plan allows
        access to a specific feature.
        """
        user_plan = current_user.subscription_plan

        # Admins have access to all features
        if user_plan == 'admin':
            return current_user

        # Check if the user's plan has the required feature
        allowed_features = PLAN_FEATURES.get(user_plan, [])
        if required_feature not in allowed_features:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Your '{user_plan}' plan does not include access to this feature. Please upgrade your plan."
            )

        return current_user
    return get_current_user_with_plan
