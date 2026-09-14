import asyncio
import logging
import time
from typing import Dict, Any, Optional, Callable
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)


class Cache:
    """简单内存缓存"""

    def __init__(self, ttl: int = 300):  # 默认 5 分钟
        self.ttl = ttl
        self._cache: Dict[str, tuple] = {}

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key in self._cache:
            value, expires_at = self._cache[key]
            if time.time() < expires_at:
                return value
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """设置缓存值"""
        ttl = ttl if ttl else self.ttl
        self._cache[key] = (value, time.time() + ttl)

    def delete(self, key: str) -> None:
        """删除缓存值"""
        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        """清除所有缓存"""
        self._cache.clear()

    def exists(self, key: str) -> bool:
        """检查键是否存在且未过期"""
        if key in self._cache:
            value, expires_at = self._cache[key]
            return time.time() < expires_at
        return False


class CacheDecorator:
    """缓存装饰器"""

    def __init__(self, cache: Cache, key_func: Callable = None, ttl: int = None):
        self.cache = cache
        self.key_func = key_func
        self.ttl = ttl

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            if self.key_func:
                key = self.key_func(*args, **kwargs)
            else:
                key = f"{func.__name__}:{args}:{kwargs}"

            # 检查缓存
            cached = self.cache.get(key)
            if cached is not None:
                logger.debug(f"Cache hit: {key}")
                return cached

            # 执行函数并缓存结果
            logger.debug(f"Cache miss: {key}")
            result = await func(*args, **kwargs)
            self.cache.set(key, result, self.ttl)
            return result

        return wrapper


class RateLimiter:
    """速率限制器"""

    def __init__(self, calls: int, period: float):
        self.calls = calls
        self.period = period
        self._timestamps: list = []

    async def acquire(self):
        """获取调用许可"""
        while True:
            now = time.time()
            self._timestamps.append(now)

            # 移除过期的时间戳
            self._timestamps = [t for t in self._timestamps if now - t < self.period]

            # 检查是否超过限制
            if len(self._timestamps) <= self.calls:
                return

            # 等待一段时间后重试
            await asyncio.sleep(self.period / self.calls)


class DataCacheManager:
    """数据缓存管理器"""

    def __init__(self):
        self.cache = Cache(ttl=600)  # 10 分钟
        self.rate_limiters: Dict[str, RateLimiter] = {}

    def get_rate_limiter(self, name: str, calls: int = 60, period: float = 60.0):
        """获取或创建速率限制器"""
        if name not in self.rate_limiters:
            self.rate_limiters[name] = RateLimiter(calls, period)
        return self.rate_limiters[name]

    async def wait_for_rate_limit(self, name: str):
        """等待速率限制"""
        limiter = self.get_rate_limiter(name)
        await limiter.acquire()


# 全局缓存管理器实例
data_cache_manager = DataCacheManager()
