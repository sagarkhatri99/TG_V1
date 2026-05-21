"""
Telegram Account Protection & Rate Limiting System

This module prevents accounts from being banned by:
1. Enforcing Telegram's official rate limits
2. Detecting flood warnings early
3. Implementing smart backoff strategies
4. Monitoring account health
5. Auto-stopping jobs to prevent ban triggers

TELEGRAM OFFICIAL LIMITS (from API documentation):
- Maximum ~50 messages per second globally
- Per-user limit: ~3-5 messages per second (when sending to different users)
- Per-chat limit: ~1 message per second 
- Hourly: ~1000-2000 messages (business accounts can do more)
- FloodWait is a warning - exceeding it leads to account restrictions
- Repeated FloodWait = temporary restriction (hours/days)
- Suspicious patterns = permanent ban
"""
import enum
from sqlalchemy.orm import Session
import logging
from datetime import datetime, timedelta
from typing import Tuple, Optional
from sqlalchemy import func

from database import SessionLocal
from models import AccountHealth
from core.dm_health_policy import (
    get_tier_policy, 
    SAFE_MESSAGES_PER_HOUR_LIMIT, 
    SAFE_MESSAGES_PER_DAY_LIMIT,
    PAUSE_ON_FLOODWAIT_SECONDS,
    PAUSE_ON_CONSECUTIVE_FLOODS
)

logger = logging.getLogger(__name__)


class FloodSeverity(enum.Enum):
    """Categorize flood intensity to determine response"""
    LOW = "low"  # 1-10 second wait
    MEDIUM = "medium"  # 11-60 second wait
    HIGH = "high"  # 61-300 second wait (5+ minutes)
    CRITICAL = "critical"  # 300+ seconds (account at risk)


class AccountHealthStatus(enum.Enum):
    """Account health states"""
    HEALTHY = "healthy"
    WARNED = "warned"  # Received flood warning
    THROTTLED = "throttled"  # Speed reduced due to warnings
    SUSPENDED = "suspended"  # Auto-paused to prevent ban
    RESTRICTED = "restricted"  # Telegram-level restriction


class TelegramRateLimiter:
    """
    Intelligent rate limiter implementing Telegram's official policies.
    Prevents account bans through smart detection and backoff.
    """
    
    # Telegram's documented limits
    MESSAGES_PER_SECOND_GLOBAL = 50
    MESSAGES_PER_SECOND_PERSONAL = 3  # Conservative estimate
    MESSAGES_PER_HOUR_NORMAL = 1000  # Normal account
    MESSAGES_PER_HOUR_BUSINESS = 5000  # Business account
    
    # Safety thresholds (Default Legacy - Tiers will override)
    SAFE_MESSAGES_PER_HOUR = SAFE_MESSAGES_PER_HOUR_LIMIT
    SAFE_MESSAGES_PER_DAY = SAFE_MESSAGES_PER_DAY_LIMIT
    
    # Flood response strategy
    FLOOD_TOLERANCE = {
        FloodSeverity.LOW: {"max_consecutive": PAUSE_ON_CONSECUTIVE_FLOODS + 1, "backoff_multiplier": 1.5},
        FloodSeverity.MEDIUM: {"max_consecutive": PAUSE_ON_CONSECUTIVE_FLOODS, "backoff_multiplier": 2.0},
        FloodSeverity.HIGH: {"max_consecutive": 1, "backoff_multiplier": 4.0},
        FloodSeverity.CRITICAL: {"max_consecutive": 0, "backoff_multiplier": 0},  # Auto-stop
    }
    
    def __init__(self):
        self.account_stats = {}  # Track per-account statistics
    
    def categorize_flood_severity(self, flood_wait_seconds: int) -> FloodSeverity:
        """Convert FloodWait seconds to severity level"""
        if flood_wait_seconds <= 10:
            return FloodSeverity.LOW
        elif flood_wait_seconds <= 60:
            return FloodSeverity.MEDIUM
        elif flood_wait_seconds <= 300:
            return FloodSeverity.HIGH
        else:
            return FloodSeverity.CRITICAL
    
    def update_account_stats(self, account_id: int, messages_sent: int = 0, error_type: str = None):
        """Update account statistics for monitoring"""
        if account_id not in self.account_stats:
            self.account_stats[account_id] = {
                "messages_sent_hour": [],
                "messages_sent_day": [],
                "flood_incidents": [],
                "last_error": None,
                "consecutive_floods": 0,
                "health_status": AccountHealthStatus.HEALTHY,
                "min_delay_current": 30,  # Dynamic minimum delay
                "max_delay_current": 120,  # Dynamic maximum delay
            }
        
        stats = self.account_stats[account_id]
        now = datetime.utcnow()
        
        # Track message timing
        if messages_sent > 0:
            stats["messages_sent_hour"].append(now)
            stats["messages_sent_day"].append(now)
            
            # Clean old entries (older than 1 day)
            one_day_ago = now - timedelta(days=1)
            stats["messages_sent_day"] = [t for t in stats["messages_sent_day"] if t > one_day_ago]
        
        if error_type:
            stats["last_error"] = error_type
    
    def get_hour_message_count(self, account_id: int) -> int:
        """Get messages sent in last hour"""
        if account_id not in self.account_stats:
            return 0
        
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)
        stats = self.account_stats[account_id]
        
        # Clean old entries
        stats["messages_sent_hour"] = [t for t in stats["messages_sent_hour"] if t > one_hour_ago]
        return len(stats["messages_sent_hour"])
    
    def get_day_message_count(self, account_id: int) -> int:
        """Get messages sent in last 24 hours"""
        if account_id not in self.account_stats:
            return 0
        
        return len(self.account_stats[account_id]["messages_sent_day"])
    
    def check_rate_limits(self, account_id: int, db: Session = None) -> Tuple[bool, Optional[str]]:
        """
        Check if account is within safe limits using SQL aggregation.
        """
        if not db:
            db = SessionLocal()
            managed_session = True
        else:
            managed_session = False
            
        try:
            from models import MessageLog, TelegramAccount
            
            # 1. Get account tier
            acc = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()
            tier = getattr(acc, 'account_trust_tier', 'warming') or 'warming'
            policy = get_tier_policy(tier)
            
            # 2. Check Hourly (successful only)
            hour_ago = datetime.utcnow() - timedelta(hours=1)
            hour_count = db.query(func.count(MessageLog.id)).filter(
                MessageLog.telegram_account_id == account_id,
                MessageLog.timestamp >= hour_ago,
                MessageLog.delivery_status == 'sent'
            ).scalar() or 0
            
            # 3. Check Daily (successful only)
            day_ago = datetime.utcnow() - timedelta(days=1)
            day_count = db.query(func.count(MessageLog.id)).filter(
                MessageLog.telegram_account_id == account_id,
                MessageLog.timestamp >= day_ago,
                MessageLog.delivery_status == 'sent'
            ).scalar() or 0
            
            # Enforce stricter of (tier cap, global limit)
            hour_limit = min(policy.hour_cap, self.SAFE_MESSAGES_PER_HOUR)
            day_limit = min(policy.day_cap, self.SAFE_MESSAGES_PER_DAY)
            
            if hour_count >= hour_limit:
                return False, f"Hourly tier cap reached: {hour_count}/{hour_limit} (Tier: {tier})"
            
            if day_count >= day_limit:
                return False, f"Daily tier cap reached: {day_count}/{day_limit} (Tier: {tier})"
                
            return True, None
            
        finally:
            if managed_session:
                db.close()
    
    def handle_flood_incident(
        self, account_id: int, flood_wait_seconds: int, current_job_id: int
    ) -> Tuple[bool, str, dict]:
        """
        Handle a FloodWaitError incident.
        Returns (should_continue, action, details)
        
        Implements progressive backoff:
        - 1st flood: Wait it out + slow down
        - 2nd flood: Pause job + alert user
        - 3rd+ flood: Suspend account + critical alert
        """
        if account_id not in self.account_stats:
            self.update_account_stats(account_id)
        
        stats = self.account_stats[account_id]
        # Immediate pause for critical flood waits
        if flood_wait_seconds >= PAUSE_ON_FLOODWAIT_SECONDS:
            logger.warning(f"Critical FloodWait {flood_wait_seconds}s for account {account_id}. Triggering PAUSE.")
            return False, "PAUSE_JOB", {"severity": "critical", "seconds": flood_wait_seconds}
            
        severity = self.categorize_flood_severity(flood_wait_seconds)
        
        # Record incident
        stats["flood_incidents"].append({
            "timestamp": datetime.utcnow(),
            "wait_seconds": flood_wait_seconds,
            "severity": severity.value,
            "job_id": current_job_id,
        })
        stats["consecutive_floods"] += 1
        
        logger.warning(
            f"FLOOD WARNING: Account {account_id} got {severity.value} flood "
            f"({flood_wait_seconds}s wait). Job {current_job_id}. "
            f"Consecutive floods: {stats['consecutive_floods']}"
        )
        
        # Determine response based on severity and history
        tolerance = self.FLOOD_TOLERANCE[severity]
        consecutive = stats["consecutive_floods"]
        
        if consecutive > tolerance["max_consecutive"]:
            # CRITICAL: Stop immediately
            stats["health_status"] = AccountHealthStatus.SUSPENDED
            details = {
                "severity": severity.value,
                "consecutive_floods": consecutive,
                "hour_messages": self.get_hour_message_count(account_id),
                "day_messages": self.get_day_message_count(account_id),
                "last_wait_seconds": flood_wait_seconds,
            }
            
            if severity == FloodSeverity.CRITICAL:
                logger.critical(
                    f"ACCOUNT AT CRITICAL RISK: Account {account_id} suspended to prevent ban. "
                    f"Flood wait: {flood_wait_seconds}s. Details: {details}"
                )
                return False, "CRITICAL_STOP", details
            else:
                logger.error(
                    f"ACCOUNT SUSPENDED: Account {account_id} job {current_job_id} paused. "
                    f"Too many flood incidents. Details: {details}"
                )
                return False, "PAUSE_JOB", details
        
        # Moderate response: Adjust delays
        if consecutive >= 2:
            stats["health_status"] = AccountHealthStatus.THROTTLED
            # Increase delays to reduce sending rate
            stats["min_delay_current"] = int(stats["min_delay_current"] * tolerance["backoff_multiplier"])
            stats["max_delay_current"] = int(stats["max_delay_current"] * tolerance["backoff_multiplier"])
            
            logger.warning(
                f"Account {account_id} delays increased: "
                f"{stats['min_delay_current']}-{stats['max_delay_current']}s "
                f"to reduce flood risk"
            )
        elif consecutive == 1:
            stats["health_status"] = AccountHealthStatus.WARNED
            logger.warning(f"Account {account_id} received flood warning. Job will continue with caution.")
        
        details = {
            "severity": severity.value,
            "consecutive_floods": consecutive,
            "hour_messages": self.get_hour_message_count(account_id),
            "day_messages": self.get_day_message_count(account_id),
            "last_wait_seconds": flood_wait_seconds,
            "new_min_delay": stats["min_delay_current"],
            "new_max_delay": stats["max_delay_current"],
        }
        
        return True, "CONTINUE_WITH_BACKOFF", details
    
    def record_flood_recovery(self, account_id: int):
        """Reset flood counter when job completes successfully"""
        if account_id in self.account_stats:
            self.account_stats[account_id]["consecutive_floods"] = 0
            if self.account_stats[account_id]["health_status"] == AccountHealthStatus.WARNED:
                self.account_stats[account_id]["health_status"] = AccountHealthStatus.HEALTHY
            logger.info(f"Account {account_id} flood counter reset - job completed successfully")
    
    def get_account_health(self, account_id: int) -> dict:
        """Get full account health report"""
        if account_id not in self.account_stats:
            self.update_account_stats(account_id)
        
        stats = self.account_stats[account_id]
        return {
            "account_id": account_id,
            "health_status": stats["health_status"].value,
            "consecutive_floods": stats["consecutive_floods"],
            "hour_messages": self.get_hour_message_count(account_id),
            "day_messages": self.get_day_message_count(account_id),
            "last_error": stats["last_error"],
            "total_incidents": len(stats["flood_incidents"]),
            "current_min_delay": stats["min_delay_current"],
            "current_max_delay": stats["max_delay_current"],
            "recent_incidents": stats["flood_incidents"][-3:],  # Last 3 incidents
        }


def is_within_operating_hours(account_id: int, db: Session = None) -> Tuple[bool, str]:
    """
    Check if the account is within its defined operating (wake) hours.
    Returns (is_allowed, reason)
    """
    _owns_session = False
    if db is None:
        db = SessionLocal()
        _owns_session = True

    try:
        from models import TelegramAccount
        from datetime import datetime

        acc = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()
        if not acc:
            return False, "Account not found"

        start_h = getattr(acc, "sleep_hour_start", None)
        end_h = getattr(acc, "sleep_hour_end", None)

        if start_h is None or end_h is None:
            return True, ""  # No sleep hours defined

        from core.config import settings
        if not settings.ENABLE_OPERATING_HOURS_CHECK:
            return True, ""

        now = datetime.utcnow()
        current_h = now.hour

        # Check if current hour is within the SLEEP interval
        is_sleeping = False
        if start_h < end_h:
            # Simple case: e.g., sleep 23 to 07
            is_sleeping = (start_h <= current_h < end_h)
        else:
            # Wrap around midnight: e.g., sleep 23 to 07
            is_sleeping = (current_h >= start_h or current_h < end_h)

        if is_sleeping:
            return False, f"Account is in sleep mode ({start_h}:00 - {end_h}:00 UTC)"

        return True, ""
    except Exception as e:
        logger.error(f"Error checking operating hours for account {account_id}: {e}")
        return True, ""  # Fail open
    finally:
        if _owns_session:
            db.close()


def is_account_safe_for_job(account_id: int, db: Session = None) -> Tuple[bool, str]:
    """
    Safety Circuit Breaker: Check if an account is healthy enough to start/continue a job.

    Returns (is_safe, reason)
    """
    _owns_session = False
    if db is None:
        db = SessionLocal()
        _owns_session = True

    try:
        from models import AccountHealth, TelegramAccount

        # 1. Check account existence and status
        acc = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()
        if not acc:
            return False, "Account not found"

        if acc.status != "active":
            return False, f"Account status is '{acc.status}', expected 'active'"

        # 2. Check health record
        health = db.query(AccountHealth).filter(AccountHealth.account_id == account_id).first()
        if not health:
            # If no health record exists, it's a new account, assume safe but log it
            logger.info(f"Account {account_id} has no health record yet. Allowing first job.")
            return True, ""

        if health.status in ("restricted", "banned"):
            return False, f"Account health status is '{health.status}'"

        from core.config import settings
        if health.health_score < settings.SAFETY_SCORE_THRESHOLD:
            return False, f"Account health score too low: {health.health_score:.1f}/100"

        return True, ""

    except Exception as e:
        logger.error(f"Error in safety circuit breaker for account {account_id}: {e}")
        return False, f"Safety check error: {str(e)}"
    finally:
        if _owns_session:
            db.close()


def sync_health_to_db(
    account_id: int,
    db: Session = None,
    extra_stats: dict = None,
) -> None:
    """
    Persist the in-memory rate limiter stats to the AccountHealth database table.

    Call this:
    - After each flood incident (handle_flood_incident)
    - At job completion / failure
    - After a batch of messages is sent

    :param account_id:  TelegramAccount.id
    :param db:          SQLAlchemy session (optional). When None, this function
                        opens, commits, and closes its own session. When a session
                        is provided (legacy callers), it is used as-is and NOT
                        closed by this function.
    :param extra_stats: Optional dict with keys:
        - messages_sent_today (int)
        - groups_joined_today (int)
        - api_calls_today (int)
    """
    _owns_session = False
    if db is None:
        db = SessionLocal()
        _owns_session = True

    try:
        if account_id not in rate_limiter.account_stats:
            return  # No stats to sync yet

        stats = rate_limiter.account_stats[account_id]
        health = db.query(AccountHealth).filter(AccountHealth.account_id == account_id).first()

        if not health:
            health = AccountHealth(account_id=account_id)
            db.add(health)

        # Derive error counts from incidents
        flood_wait_count = stats.get("consecutive_floods", 0)
        spam_error_count = sum(
            1 for i in stats.get("flood_incidents", [])
            if i.get("severity") in ("high", "critical")
        )

        # Status mapping
        health_status_map = {
            AccountHealthStatus.HEALTHY: "healthy",
            AccountHealthStatus.WARNED: "warning",
            AccountHealthStatus.THROTTLED: "warning",
            AccountHealthStatus.SUSPENDED: "restricted",
            AccountHealthStatus.RESTRICTED: "restricted",
        }
        in_memory_status = stats.get("health_status", AccountHealthStatus.HEALTHY)
        new_status = health_status_map.get(in_memory_status, "healthy")

        # Calculate health score (starts at 100 and penalises errors)
        score = 100.0
        score -= flood_wait_count * 5      # -5 per consecutive flood
        score -= spam_error_count * 15     # -15 per high/critical flood (spam behaviour)
        if new_status in ("restricted", "banned"):
            score -= 30
        score = max(0.0, min(100.0, score))

        # Apply updates to DB record
        health.health_score = score
        health.status = new_status
        health.flood_wait_count = flood_wait_count
        health.spam_error_count = spam_error_count
        health.last_activity = datetime.utcnow()
        health.updated_at = datetime.utcnow()

        if extra_stats:
            if "messages_sent_today" in extra_stats:
                health.messages_sent_today = extra_stats["messages_sent_today"]
            if "groups_joined_today" in extra_stats:
                health.groups_joined_today = extra_stats["groups_joined_today"]
            if "api_calls_today" in extra_stats:
                health.api_calls_today = extra_stats["api_calls_today"]

        # Append to error_history if there was a recent incident
        if stats.get("flood_incidents"):
            latest_incident = stats["flood_incidents"][-1]
            entry = {
                "time": (
                    latest_incident["timestamp"].isoformat()
                    if isinstance(latest_incident["timestamp"], datetime)
                    else str(latest_incident["timestamp"])
                ),
                "type": "flood_wait",
                "severity": latest_incident.get("severity", "unknown"),
                "wait_seconds": latest_incident.get("wait_seconds", 0),
                "job_id": latest_incident.get("job_id"),
            }
            history = health.error_history or []
            history = history[-49:] + [entry]  # keep last 50 entries
            health.error_history = history

        db.commit()
        logger.debug(
            f"sync_health_to_db: account {account_id} → score={score:.1f}, status={new_status}"
        )
    except Exception as e:
        logger.error(f"sync_health_to_db failed for account {account_id}: {e}")
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        if _owns_session:
            db.close()


# Global instance
rate_limiter = TelegramRateLimiter()
