"""
Cache management for API responses
"""

import time
from typing import Dict, Any, Optional
from collections import defaultdict

class CacheManager:
    def __init__(self, ttl: int = 300, maxsize: int = 100):
        self.cache: Dict[str, Dict] = {}
        self.ttl = ttl  # Time to live in seconds
        self.maxsize = maxsize
        self.region_cache: Dict[str, str] = {}  # UID -> Region mapping
        
        # Statistics
        self.request_count = 0
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache if not expired"""
        if key in self.cache:
            item = self.cache[key]
            if time.time() < item['expires']:
                return item['data']
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """Set item in cache"""
        # If cache is full, remove oldest
        if len(self.cache) >= self.maxsize:
            oldest = min(self.cache.keys(), key=lambda k: self.cache[k]['created'])
            del self.cache[oldest]
        
        self.cache[key] = {
            'data': value,
            'created': time.time(),
            'expires': time.time() + self.ttl
        }
    
    def set_region(self, uid: str, region: str):
        """Remember which region a UID belongs to"""
        self.region_cache[uid] = region
    
    def get_region(self, uid: str) -> Optional[str]:
        """Get cached region for UID"""
        return self.region_cache.get(uid)
    
    def clear(self):
        """Clear all cache"""
        self.cache.clear()
        self.region_cache.clear()
    
    def size(self) -> int:
        """Get current cache size"""
        return len(self.cache)
    
    def record_request(self):
        """Record a request"""
        self.request_count += 1
    
    def record_hit(self):
        """Record a cache hit"""
        self.hits += 1
        self.record_request()
    
    def record_miss(self):
        """Record a cache miss"""
        self.misses += 1
        self.record_request()
    
    def get_request_count(self) -> int:
        return self.request_count
    
    def get_hits(self) -> int:
        return self.hits
    
    def get_misses(self) -> int:
        return self.misses