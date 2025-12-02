"""
Rate limiting system for API usage protection
Implements per-user request limits with time-based windows
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Tuple
import json

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter for protecting API usage"""
    
    def __init__(self):
        # Daily limits (can be configured per tier)
        self.free_tier_daily_limit = int(os.getenv("RATE_LIMIT_FREE_DAILY", "50"))
        self.paid_tier_daily_limit = int(os.getenv("RATE_LIMIT_PAID_DAILY", "500"))
        
        # Hourly limits (prevents burst abuse)
        self.free_tier_hourly_limit = int(os.getenv("RATE_LIMIT_FREE_HOURLY", "10"))
        self.paid_tier_hourly_limit = int(os.getenv("RATE_LIMIT_PAID_HOURLY", "100"))
        
    def check_rate_limit(self, db, user_id: int, is_paid: bool = False) -> Tuple[bool, str, dict]:
        """
        Check if user has exceeded rate limits
        Returns: (allowed: bool, message: str, usage_stats: dict)
        """
        try:
            from database import get_db, EducatorAnalytics
            from datetime import datetime, timedelta
            
            # Get user's tier
            daily_limit = self.paid_tier_daily_limit if is_paid else self.free_tier_daily_limit
            hourly_limit = self.paid_tier_hourly_limit if is_paid else self.free_tier_hourly_limit
            
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            hour_start = now.replace(minute=0, second=0, microsecond=0)
            
            # Count requests in current day
            daily_count = db.query(EducatorAnalytics).filter(
                EducatorAnalytics.user_id == user_id,
                EducatorAnalytics.created_at >= today_start
            ).count()
            
            # Count requests in current hour
            hourly_count = db.query(EducatorAnalytics).filter(
                EducatorAnalytics.user_id == user_id,
                EducatorAnalytics.created_at >= hour_start
            ).count()
            
            # Build usage stats
            usage_stats = {
                'daily_count': daily_count,
                'daily_limit': daily_limit,
                'hourly_count': hourly_count,
                'hourly_limit': hourly_limit,
                'tier': 'paid' if is_paid else 'free'
            }
            
            # Check daily limit
            if daily_count >= daily_limit:
                return False, f"Daily request limit ({daily_limit}) reached. Please try again tomorrow.", usage_stats
            
            # Check hourly limit
            if hourly_count >= hourly_limit:
                return False, f"Hourly request limit ({hourly_limit}) reached. Please wait {60 - now.minute} minutes.", usage_stats
            
            # Still within limits
            return True, None, usage_stats
            
        except Exception as e:
            logger.error(f"Rate limit check error: {str(e)}")
            # Fail open - allow request if check fails
            return True, None, {}
    
    def get_usage_stats(self, db, user_id: int, is_paid: bool = False) -> dict:
        """Get current usage statistics for a user"""
        try:
            from database import EducatorAnalytics
            
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            hour_start = now.replace(minute=0, second=0, microsecond=0)
            
            daily_limit = self.paid_tier_daily_limit if is_paid else self.free_tier_daily_limit
            hourly_limit = self.paid_tier_hourly_limit if is_paid else self.free_tier_hourly_limit
            
            daily_count = db.query(EducatorAnalytics).filter(
                EducatorAnalytics.user_id == user_id,
                EducatorAnalytics.created_at >= today_start
            ).count()
            
            hourly_count = db.query(EducatorAnalytics).filter(
                EducatorAnalytics.user_id == user_id,
                EducatorAnalytics.created_at >= hour_start
            ).count()
            
            return {
                'daily_used': daily_count,
                'daily_limit': daily_limit,
                'daily_remaining': max(0, daily_limit - daily_count),
                'hourly_used': hourly_count,
                'hourly_limit': hourly_limit,
                'hourly_remaining': max(0, hourly_limit - hourly_count),
                'tier': 'paid' if is_paid else 'free',
                'reset_tomorrow': (today_start + timedelta(days=1)).strftime('%H:%M UTC')
            }
        except Exception as e:
            logger.error(f"Error getting usage stats: {str(e)}")
            return {}


# Singleton instance
_rate_limiter = None

def get_rate_limiter() -> RateLimiter:
    """Get or create rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
