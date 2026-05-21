"""
core/dm_health_policy.py

Single source of truth for Telegram mass-DM safety constants.
All rate limits, delays, and tier caps are defined here.
"""

import os
from dataclasses import dataclass
from typing import Dict

# ─── Feature Flag ────────────────────────────────────────────────────────────
USE_NEW_HEALTH_POLICY = os.getenv("USE_NEW_HEALTH_POLICY", "true").lower() == "true"

@dataclass(frozen=True)
class TierPolicy:
    """Policy for one trust tier."""
    day_cap: int
    hour_cap: int
    min_delay: int
    max_delay: int

@dataclass(frozen=True)
class RecipientModePolicy:
    """Delay/cap adjustments for recipient risk."""
    delay_multiplier: float
    day_cap_multiplier: float

# ─── Health-First Policy (New Default) ───────────────────────────────────────
HEALTH_FIRST_TIERS: Dict[str, TierPolicy] = {
    "new":      TierPolicy(day_cap=20,  hour_cap=8,   min_delay=90,  max_delay=180),
    "warming":  TierPolicy(day_cap=50,  hour_cap=15,  min_delay=60,  max_delay=150),
    "trusted":  TierPolicy(day_cap=100, hour_cap=30,  min_delay=45,  max_delay=120),
}

# ─── Legacy Policy (For Rollback) ────────────────────────────────────────────
LEGACY_TIERS: Dict[str, TierPolicy] = {
    "new":      TierPolicy(day_cap=5000, hour_cap=300, min_delay=30, max_delay=120),
    "warming":  TierPolicy(day_cap=5000, hour_cap=300, min_delay=30, max_delay=120),
    "trusted":  TierPolicy(day_cap=5000, hour_cap=300, min_delay=30, max_delay=120),
}

# ─── Recipient Modes ─────────────────────────────────────────────────────────
RECIPIENT_MODE_POLICIES: Dict[str, RecipientModePolicy] = {
    "cold": RecipientModePolicy(delay_multiplier=1.0, day_cap_multiplier=1.0),
    "warm": RecipientModePolicy(delay_multiplier=0.6, day_cap_multiplier=1.5),
}

# ─── Global Ceilings ────────────────────────────────────────────────────────
SAFE_MESSAGES_PER_HOUR_LIMIT = 30 if USE_NEW_HEALTH_POLICY else 300
SAFE_MESSAGES_PER_DAY_LIMIT = 100 if USE_NEW_HEALTH_POLICY else 5000

PAUSE_ON_FLOODWAIT_SECONDS = 300
PAUSE_ON_CONSECUTIVE_FLOODS = 2

def get_tier_policy(tier: str, custom_day_cap: int = None, custom_hour_cap: int = None) -> TierPolicy:
    """
    Return the TierPolicy for the given tier.
    """
    tiers = HEALTH_FIRST_TIERS if USE_NEW_HEALTH_POLICY else LEGACY_TIERS
    
    if tier == "custom":
        base = tiers["trusted"]
        return TierPolicy(
            day_cap=custom_day_cap or base.day_cap,
            hour_cap=custom_hour_cap or base.hour_cap,
            min_delay=base.min_delay,
            max_delay=base.max_delay,
        )
    
    return tiers.get(tier, tiers["warming"])

def get_recipient_mode_policy(mode: str) -> RecipientModePolicy:
    """Return policy for the given recipient mode."""
    return RECIPIENT_MODE_POLICIES.get(mode, RECIPIENT_MODE_POLICIES["cold"])
