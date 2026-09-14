"""
Redis客户端配置和连接管理
"""
import redis
from redis.connection import ConnectionPool
from typing import Optional, Any
import logging

from .config import settings

logger = logging.getLogger(__name__)


def create_redis_pool() -> ConnectionPool:
    """创建Redis连接池"""
    pool = ConnectionPool(
        host=settings.redis.REDIS_HOST,
        port=settings.redis.REDIS_PORT,
        password=settings.redis.REDIS_PASSWORD,
        db=settings.redis.REDIS_DB,
        max_connections=settings.redis.REDIS_MAX_CONNECTIONS,
        socket_timeout=settings.redis.REDIS_SOCKET_TIMEOUT,
        socket_connect_timeout=settings.redis.REDIS_SOCKET_CONNECT_TIMEOUT,
        decode_responses=True,
    )
    
    logger.info(
        "Redis connection pool created",
        host=settings.redis.REDIS_HOST,
        port=settings.redis.REDIS_PORT,
        db=settings.redis.REDIS_DB,
        max_connections=settings.redis.REDIS_MAX_CONNECTIONS,
    )
    
    return pool


# 创建连接池和客户端
redis_pool = create_redis_pool()
redis_client = redis.Redis(connection_pool=redis_pool)


def get_redis() -> redis.Redis:
    """获取Redis客户端"""
    return redis_client


def check_redis_connection() -> bool:
    """检查Redis连接"""
    try:
        redis_client.ping()
        return True
    except Exception as e:
        logger.error("Redis connection check failed", error=str(e))
        return False


def get_redis_info() -> dict:
    """获取Redis信息"""
    try:
        info = redis_client.info()
        return {
            "host": settings.redis.REDIS_HOST,
            "port": settings.redis.REDIS_PORT,
            "db": settings.redis.REDIS_DB,
            "connected_clients": info.get("connected_clients", 0),
            "used_memory": info.get("used_memory", 0),
            "uptime_in_seconds": info.get("uptime_in_seconds", 0),
        }
    except Exception as e:
        logger.error("Failed to get Redis info", error=str(e))
        return {
            "host": settings.redis.REDIS_HOST,
            "port": settings.redis.REDIS_PORT,
            "db": settings.redis.REDIS_DB,
            "error": str(e),
        }


class RedisCache:
    """Redis缓存封装"""
    
    def __init__(self, prefix: str = "cache", default_ttl: int = 3600):
        """
        初始化缓存
        
        Args:
            prefix: 缓存键前缀
            default_ttl: 默认过期时间（秒）
        """
        self.prefix = prefix
        self.default_ttl = default_ttl
    
    def _make_key(self, key: str) -> str:
        """生成缓存键"""
        return f"{self.prefix}:{key}"
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        full_key = self._make_key(key)
        try:
            value = redis_client.get(full_key)
            if value:
                import json
                return json.loads(value)
            return None
        except Exception as e:
            logger.error("Redis get error", key=full_key, error=str(e))
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        full_key = self._make_key(key)
        ttl = ttl or self.default_ttl
        try:
            import json
            redis_client.setex(full_key, ttl, json.dumps(value))
            return True
        except Exception as e:
            logger.error("Redis set error", key=full_key, error=str(e))
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        full_key = self._make_key(key)
        try:
            redis_client.delete(full_key)
            return True
        except Exception as e:
            logger.error("Redis delete error", key=full_key, error=str(e))
            return False
    
    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        full_key = self._make_key(key)
        try:
            return redis_client.exists(full_key) > 0
        except Exception as e:
            logger.error("Redis exists error", key=full_key, error=str(e))
            return False
    
    def set_hash(self, key: str, mapping: dict, ttl: Optional[int] = None) -> bool:
        """设置哈希缓存"""
        full_key = self._make_key(key)
        ttl = ttl or self.default_ttl
        try:
            redis_client.hset(full_key, mapping=mapping)
            redis_client.expire(full_key, ttl)
            return True
        except Exception as e:
            logger.error("Redis hset error", key=full_key, error=str(e))
            return False
    
    def get_hash(self, key: str) -> Optional[dict]:
        """获取哈希缓存"""
        full_key = self._make_key(key)
        try:
            return redis_client.hgetall(full_key)
        except Exception as e:
            logger.error("Redis hgetall error", key=full_key, error=str(e))
            return None


# 创建缓存实例
market_cache = RedisCache(prefix="market", default_ttl=300)  # 5分钟
strategy_cache = RedisCache(prefix="strategy", default_ttl=60)  # 1分钟
portfolio_cache = RedisCache(prefix="portfolio", default_ttl=60)  # 1分钟