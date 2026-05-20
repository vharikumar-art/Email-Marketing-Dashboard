import os
import json
from typing import Any, Optional
from cachetools import TTLCache
import redis
from datetime import datetime, timedelta

# Cache configuration
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", 300))  # 5 minutes default
REDIS_URL = os.getenv("REDIS_URL")

class CacheManager:
    def __init__(self):
        self.use_redis = bool(REDIS_URL)
        if self.use_redis:
            try:
                self.redis_client = redis.from_url(REDIS_URL)
                self.redis_client.ping()  # Test connection
                print("✅ Redis cache enabled")
            except Exception as e:
                print(f"❌ Redis connection failed: {e}, falling back to memory cache")
                self.use_redis = False

        if not self.use_redis:
            # Fallback to in-memory cache
            self.memory_cache = TTLCache(maxsize=100, ttl=CACHE_TTL_SECONDS)
            print("✅ Memory cache enabled")

    def _make_key(self, *args) -> str:
        """Create a cache key from arguments"""
        return ":".join(str(arg) for arg in args)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if self.use_redis:
                data = self.redis_client.get(key)
                return json.loads(data) if data else None
            else:
                return self.memory_cache.get(key)
        except Exception as e:
            print(f"Cache get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        try:
            ttl = ttl or CACHE_TTL_SECONDS
            if self.use_redis:
                self.redis_client.setex(key, ttl, json.dumps(value))
            else:
                self.memory_cache[key] = value
        except Exception as e:
            print(f"Cache set error: {e}")

    def delete(self, key: str) -> None:
        """Delete value from cache"""
        try:
            if self.use_redis:
                self.redis_client.delete(key)
            else:
                self.memory_cache.pop(key, None)
        except Exception as e:
            print(f"Cache delete error: {e}")

    def clear_pattern(self, pattern: str) -> None:
        """Clear cache keys matching pattern"""
        try:
            if self.use_redis:
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            else:
                # Convert glob pattern (e.g. "dashboard:orders:*") to a prefix match
                prefix = pattern.rstrip("*")
                keys_to_delete = [k for k in list(self.memory_cache.keys()) if str(k).startswith(prefix)]
                for k in keys_to_delete:
                    self.memory_cache.pop(k, None)
        except Exception as e:
            print(f"Cache clear pattern error: {e}")

# Global cache instance
cache_manager = CacheManager()

# Cache key generators
def dashboard_cache_key(user_email: str, role: str) -> str:
    """Generate cache key for dashboard data"""
    return f"dashboard:orders:{user_email}:{role}"

def user_cache_key(email: str) -> str:
    """Generate cache key for user data"""
    return f"user:data:{email}"

# Cache invalidation helpers
def invalidate_dashboard_cache():
    """Invalidate all dashboard caches"""
    cache_manager.clear_pattern("dashboard:orders:*")

def invalidate_user_cache(email: Optional[str] = None):
    """Invalidate user cache. If email is None, invalidates all user caches."""
    if email:
        cache_manager.delete(user_cache_key(email))
    else:
        cache_manager.clear_pattern("user:data:*")