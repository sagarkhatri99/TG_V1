import asyncio
import time
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class AccountRateLimiter:
    """
    Per-account rate limiter: 1 Telegram API call per second per account.
    Multiple accounts can run simultaneously without interfering.
    Uses Redis for distributed rate limiting across workers.
    """
    def __init__(self, redis_url: str = "redis://redis:6379/0"):
        self.redis_url = redis_url
        self._redis = None
        self.redis_available = True
        self.local_cache = {}  # Fallback when Redis is down
        
    async def _get_redis(self):
        """Lazy initialization of Redis connection with fallback"""
        if not self.redis_available:
            return None
            
        if self._redis is None:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(self.redis_url, decode_responses=True)
                # Test connection
                await self._redis.ping()
                self.redis_available = True
                logger.info(f"Redis connection established for rate limiter: {self.redis_url}")
            except ImportError:
                logger.error("redis package not installed. Install with: pip install redis")
                self.redis_available = False
                return None
            except Exception as e:
                logger.error(f"Failed to connect to Redis at {self.redis_url}: {e}")
                logger.warning("Falling back to local in-memory rate limiting (less reliable in multi-worker setup)")
                self.redis_available = False
                return None
        return self._redis
        
    async def acquire(self, account_id: int, timeout: float = 5.0) -> bool:
        """
        Acquire permission for account to make Telegram API call.
        Blocks until 1 second has passed since last call for THIS account.
        Falls back to local cache if Redis is unavailable.
        
        Args:
            account_id: Unique account identifier
            timeout: Maximum seconds to wait for rate limit
            
        Returns:
            True if acquired, raises TimeoutError if timeout exceeded
        """
        redis = await self._get_redis()
        
        if redis and self.redis_available:
            try:
                return await self._acquire_redis(account_id, timeout, redis)
            except Exception as e:
                logger.warning(f"Redis error during acquire: {e}. Falling back to local.")
                self.redis_available = False
        
        # Local fallback (less reliable in multi-worker setup)
        return await self._acquire_local(account_id, timeout)
    
    async def _acquire_redis(self, account_id: int, timeout: float, redis) -> bool:
        """Acquire using Redis (distributed rate limiting)"""
        key = f"rate:account:{account_id}"
        start_time = time.time()
        
        while True:
            current_time = time.time()
            
            # Get last API call timestamp for this account
            last_call = await redis.get(key)
            
            if last_call is None:
                # First API call for this account
                await redis.setex(key, 10, str(current_time))
                logger.debug(f"Account {account_id}: First API call granted (Redis)")
                return True
            
            # Calculate time since last call
            elapsed = current_time - float(last_call)
            
            if elapsed >= 1.0:
                # 1 second passed, grant permission
                await redis.setex(key, 10, str(current_time))
                logger.debug(f"Account {account_id}: API call granted (Redis, waited {elapsed:.2f}s)")
                return True
            
            # Check if timeout exceeded
            if time.time() - start_time >= timeout:
                logger.error(f"Account {account_id}: Rate limit timeout after {timeout}s")
                raise TimeoutError(
                    f"Rate limit timeout for account {account_id}. "
                    f"Waited {timeout}s, needed {1.0 - elapsed:.2f}s more."
                )
            
            # Wait for remaining time (with small buffer)
            wait_time = max(0.01, 1.0 - elapsed)
            logger.debug(f"Account {account_id}: Waiting {wait_time:.2f}s for rate limit")
            await asyncio.sleep(wait_time)
    
    async def _acquire_local(self, account_id: int, timeout: float) -> bool:
        """
        Fallback: In-memory rate limiting when Redis is down.
        WARNING: Not reliable in multi-worker setups!
        """
        logger.warning(f"Account {account_id}: Using local fallback rate limiting")
        start_time = time.time()
        
        while True:
            current_time = time.time()
            
            # Get last API call timestamp from local cache
            last_call = self.local_cache.get(account_id)
            
            if last_call is None:
                # First API call for this account
                self.local_cache[account_id] = current_time
                logger.debug(f"Account {account_id}: First API call granted (local)")
                return True
            
            # Calculate time since last call
            elapsed = current_time - last_call
            
            if elapsed >= 1.0:
                # 1 second passed, grant permission
                self.local_cache[account_id] = current_time
                logger.debug(f"Account {account_id}: API call granted (local, waited {elapsed:.2f}s)")
                return True
            
            # Check if timeout exceeded
            if time.time() - start_time >= timeout:
                logger.error(f"Account {account_id}: Rate limit timeout after {timeout}s (local)")
                raise TimeoutError(
                    f"Rate limit timeout for account {account_id}. "
                    f"Waited {timeout}s, needed {1.0 - elapsed:.2f}s more."
                )
            
            # Wait for remaining time
            wait_time = max(0.01, 1.0 - elapsed)
            await asyncio.sleep(wait_time)
    
    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            self._redis = None

# Global instance
_rate_limiter: Optional[AccountRateLimiter] = None

def get_rate_limiter(redis_url: str = "redis://redis:6379/0") -> AccountRateLimiter:
    """Get or create global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = AccountRateLimiter(redis_url)
    return _rate_limiter