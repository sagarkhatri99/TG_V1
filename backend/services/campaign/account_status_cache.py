"""
Account status cache management for campaign system.
Provides cache invalidation when account settings change.
"""

# Simple in-memory cache for account status
# Key: account_id, Value: cached status data
_account_status_cache = {}


def invalidate_account_cache(account_id: int) -> None:
    """
    Invalidate cached account status when settings change.
    
    This ensures that when account operating hours or daily limits are updated,
    the campaign system will re-check the account's availability status
    instead of using stale cached data.
    
    Args:
        account_id: The ID of the account to invalidate cache for
    """
    if account_id in _account_status_cache:
        del _account_status_cache[account_id]


def get_cached_status(account_id: int):
    """
    Get cached account status if available.
    
    Args:
        account_id: The ID of the account
        
    Returns:
        Cached status dict or None if not cached
    """
    return _account_status_cache.get(account_id)


def set_cached_status(account_id: int, status_data: dict) -> None:
    """
    Cache account status data.
    
    Args:
        account_id: The ID of the account
        status_data: Dict containing status information to cache
    """
    _account_status_cache[account_id] = status_data


def clear_all_cache() -> None:
    """Clear all cached account status data."""
    _account_status_cache.clear()
