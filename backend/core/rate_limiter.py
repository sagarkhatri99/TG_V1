import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class AdvancedRateLimiter:
    def __init__(self):
        # Track rate limits per account
        self.account_limits: Dict[int, dict] = {}
        # Global rate limits
        self.global_message_count = 0
        self.global_reset_time = datetime.utcnow() + timedelta(seconds=60)
    
    async def can_send_message(self, account_id: int, target_type: str = "user") -> bool:
        """Check if account can send a message"""
        account_data = self.account_limits.get(account_id, {
            'messages_today': 0,
            'last_message': None,
            'consecutive_messages': 0,
            'last_reset': datetime.utcnow().date()
        })
        
        # Reset daily counters
        if account_data['last_reset'] != datetime.utcnow().date():
            account_data['messages_today'] = 0
            account_data['consecutive_messages'] = 0
            account_data['last_reset'] = datetime.utcnow().date()
        
        # Check daily limits
        daily_limit = self._get_daily_limit(target_type)
        if account_data['messages_today'] >= daily_limit:
            return False
        
        # Check global rate limit
        if self.global_message_count >= 30:  # 30 messages per minute globally
            if datetime.utcnow() < self.global_reset_time:
                return False
            else:
                self.global_message_count = 0
                self.global_reset_time = datetime.utcnow() + timedelta(seconds=60)
        
        return True
    
    async def calculate_delay(self, account_id: int, target_type: str = "user", trust_score: int = 50) -> float:
        """Calculate intelligent delay between messages (8-200 seconds as requested)"""
        
        # Get account data
        account_data = self.account_limits.get(account_id, {})
        
        # Base delay range (as requested: 8-200 seconds)
        min_delay = 8
        max_delay = 200
        
        # Calculate base delay
        base_delay = random.uniform(min_delay, max_delay)
        
        # Apply multipliers based on risk factors
        risk_multiplier = 1.0
        
        # Account trust score impact
        if trust_score < 30:
            risk_multiplier += 0.5  # 50% longer delays for low trust
        elif trust_score > 80:
            risk_multiplier -= 0.2  # 20% shorter delays for high trust
        
        # Recent activity impact
        if account_data.get('consecutive_messages', 0) > 5:
            risk_multiplier += 0.3  # Longer delays after many consecutive messages
        
        # Target type impact
        if target_type == "group":
            risk_multiplier += 0.2  # Groups are riskier
        
        # Time of day impact (avoid peak hours)
        current_hour = datetime.utcnow().hour
        if 9 <= current_hour <= 17:  # Peak hours
            risk_multiplier += 0.15
        
        # Calculate final delay
        final_delay = base_delay * risk_multiplier
        
        # Ensure within bounds but allow extension for safety
        final_delay = max(min_delay, min(final_delay, max_delay * 2))
        
        return final_delay
    
    async def record_message_sent(self, account_id: int, target_type: str = "user"):
        """Record that a message was sent"""
        if account_id not in self.account_limits:
            self.account_limits[account_id] = {
                'messages_today': 0,
                'last_message': None,
                'consecutive_messages': 0,
                'last_reset': datetime.utcnow().date()
            }
        
        account_data = self.account_limits[account_id]
        account_data['messages_today'] += 1
        account_data['last_message'] = datetime.utcnow()
        account_data['consecutive_messages'] += 1
        
        # Global counter
        self.global_message_count += 1
        
        logger.info(f"Account {account_id}: Sent message #{account_data['messages_today']} today")
    
    def _get_daily_limit(self, target_type: str) -> int:
        """Get daily message limit based on target type"""
        limits = {
            'user': 50,     # DMs per day
            'group': 100,   # Group messages per day
            'channel': 20   # Channel messages per day
        }
        return limits.get(target_type, 50)
    
    async def reset_consecutive_count(self, account_id: int):
        """Reset consecutive message count (call after long pause)"""
        if account_id in self.account_limits:
            self.account_limits[account_id]['consecutive_messages'] = 0

# Global rate limiter instance
rate_limiter = AdvancedRateLimiter()