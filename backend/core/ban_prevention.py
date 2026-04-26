from datetime import datetime, timedelta
from typing import Dict, List
import logging
import time

logger = logging.getLogger(__name__)

class BanPreventionSystem:
    def __init__(self):
        self.risk_thresholds = {
            'low': 0.3,
            'medium': 0.6,
            'high': 0.8,
            'critical': 0.95
        }
        # In-memory risk cache: {account_id: (score, timestamp)}
        self._risk_cache: Dict[int, tuple[float, float]] = {}
        self._cache_ttl = 60  # seconds
    
    async def get_cached_risk(self, account, db) -> float:
        """Get risk score from cache or trigger fresh assessment if expired."""
        now = time.time()
        if account.id in self._risk_cache:
            score, ts = self._risk_cache[account.id]
            if now - ts < self._cache_ttl:
                return score
        
        # Cache miss or expired
        score = await self.assess_account_risk(account, db)
        self._risk_cache[account.id] = (score, now)
        return score

    async def assess_account_risk(self, account, db) -> float:
        """Calculate comprehensive risk score for account"""
        
        risk_factors = {
            'rate_limit_violations': 0.0,
            'recent_activity_spike': 0.0,
            'duplicate_interactions': 0.0,
            'account_age': 0.0,
            'trust_score_factor': 0.0,
            'proxy_issues': 0.0
        }
        
        try:
            from models import MessageLog, UserInteraction
            
            # 1. Check rate limit violations in last 24 hours
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_failed = db.query(MessageLog).filter(
                MessageLog.telegram_account_id == account.id,
                MessageLog.timestamp >= yesterday,
                MessageLog.delivery_status == 'failed'
            ).count()
            
            if recent_failed > 10:
                risk_factors['rate_limit_violations'] = 0.4
            elif recent_failed > 5:
                risk_factors['rate_limit_violations'] = 0.2
            
            # 2. Check for activity spikes
            last_hour_messages = db.query(MessageLog).filter(
                MessageLog.telegram_account_id == account.id,
                MessageLog.timestamp >= datetime.utcnow() - timedelta(hours=1)
            ).count()
            
            if last_hour_messages > 20:
                risk_factors['recent_activity_spike'] = 0.3
            elif last_hour_messages > 10:
                risk_factors['recent_activity_spike'] = 0.15
            
            # 3. Check for duplicate interactions
            duplicate_interactions = db.query(UserInteraction).filter(
                UserInteraction.telegram_account_id == account.id,
                UserInteraction.interaction_count > 3,
                UserInteraction.last_interaction >= yesterday
            ).count()
            
            if duplicate_interactions > 5:
                risk_factors['duplicate_interactions'] = 0.25
            
            # 4. Account age factor
            if account.created_at:
                account_age_days = (datetime.utcnow() - account.created_at).days
                if account_age_days < 7:
                    risk_factors['account_age'] = 0.3
                elif account_age_days < 30:
                    risk_factors['account_age'] = 0.1
            
            # 5. Trust score factor
            if account.trust_score < 30:
                risk_factors['trust_score_factor'] = 0.2
            elif account.trust_score < 50:
                risk_factors['trust_score_factor'] = 0.1
            
            # 6. Proxy issues
            if account.proxy and account.proxy.status == 'failed':
                risk_factors['proxy_issues'] = 0.15
            
        except Exception as e:
            logger.error(f"Error assessing risk for account {account.id}: {e}")
            return 0.5  # Default medium risk
        
        # Calculate weighted risk score
        total_risk = sum(risk_factors.values())
        
        # Update account risk score in database
        account.ban_risk_score = min(total_risk, 1.0)
        db.commit()
        
        logger.info(f"Account {account.id} risk assessment: {total_risk:.2f}")
        
        return total_risk
    
    async def take_protective_action(self, account_id: int, risk_score: float, db):
        """Take protective action based on risk assessment"""
        
        from models import TelegramAccount, Job
        
        account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()
        if not account:
            return
        
        if risk_score >= self.risk_thresholds['critical']:
            await self._emergency_stop(account, db)
        elif risk_score >= self.risk_thresholds['high']:
            await self._pause_account(account, db)
        elif risk_score >= self.risk_thresholds['medium']:
            await self._reduce_activity(account, db)
        else:
            # Low risk - maybe increase trust score
            if account.trust_score < 100:
                account.trust_score = min(account.trust_score + 1, 100)
                db.commit()
    
    async def _emergency_stop(self, account, db):
        """Emergency stop all activities for account"""
        from models import Job
        
        account.status = 'paused'
        account.trust_score = max(account.trust_score - 20, 0)
        db.commit()
        
        # Cancel all running jobs for this account
        active_jobs = db.query(Job).filter(
            Job.telegram_account_id == account.id,
            Job.status.in_(['pending', 'running'])
        ).all()
        
        for job in active_jobs:
            job.status = 'paused'
            job.error_message = 'Emergency stop due to high ban risk'
        
        db.commit()
        logger.warning(f"EMERGENCY STOP: Account {account.id} paused due to critical risk")
    
    async def _pause_account(self, account, db):
        """Pause account temporarily"""
        account.status = 'paused'
        account.trust_score = max(account.trust_score - 10, 0)
        db.commit()
        
        logger.warning(f"Account {account.id} paused due to high risk")
    
    async def _reduce_activity(self, account, db):
        """Reduce account activity rate"""
        account.trust_score = max(account.trust_score - 5, 0)
        db.commit()
        
        logger.info(f"Account {account.id} activity reduced due to medium risk")
    
    async def check_cooldown_violation(self, account_id: int, target_user_id: str, db) -> bool:
        """Check if we're violating user interaction cooldowns"""
        
        from models import UserInteraction
        
        # Get last interaction with this user
        last_interaction = db.query(UserInteraction).filter(
            UserInteraction.telegram_account_id == account_id,
            UserInteraction.target_user_id == target_user_id
        ).first()
        
        if not last_interaction:
            return False  # No previous interaction, safe to proceed
        
        # Check if enough time has passed (2 hours default, like ReplyDaddy)
        cooldown_period = timedelta(hours=2)
        if datetime.utcnow() - last_interaction.last_interaction < cooldown_period:
            return True  # Cooldown violation
        
        return False  # Safe to interact

# Global ban prevention system
ban_prevention = BanPreventionSystem()