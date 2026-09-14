"""
健康检查和监控指标模块
提供服务健康状态检查和性能指标收集
"""
import time
import psutil
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from .config import settings
from .database import check_db_connection, get_db_info
from .redis_client import check_redis_connection, get_redis_info


class HealthStatus(str, Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    status: HealthStatus
    service: str
    version: str
    timestamp: str
    uptime: float
    checks: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class ComponentHealth:
    """组件健康状态"""
    name: str
    status: HealthStatus
    message: Optional[str] = None
    latency_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


class HealthChecker:
    """健康检查器"""
    
    def __init__(self, service_name: str):
        """
        初始化健康检查器
        
        Args:
            service_name: 服务名称
        """
        self.service_name = service_name
        self.start_time = time.time()
        self.version = settings.SERVICE_VERSION
    
    def check_database(self) -> ComponentHealth:
        """检查数据库健康状态"""
        start_time = time.time()
        try:
            is_healthy = check_db_connection()
            latency = (time.time() - start_time) * 1000
            
            if is_healthy:
                return ComponentHealth(
                    name="database",
                    status=HealthStatus.HEALTHY,
                    message="Database connection is healthy",
                    latency_ms=latency,
                    details=get_db_info()
                )
            else:
                return ComponentHealth(
                    name="database",
                    status=HealthStatus.UNHEALTHY,
                    message="Database connection failed",
                    latency_ms=latency
                )
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database check failed: {str(e)}",
                latency_ms=latency
            )
    
    def check_redis(self) -> ComponentHealth:
        """检查Redis健康状态"""
        start_time = time.time()
        try:
            is_healthy = check_redis_connection()
            latency = (time.time() - start_time) * 1000
            
            if is_healthy:
                return ComponentHealth(
                    name="redis",
                    status=HealthStatus.HEALTHY,
                    message="Redis connection is healthy",
                    latency_ms=latency,
                    details=get_redis_info()
                )
            else:
                return ComponentHealth(
                    name="redis",
                    status=HealthStatus.UNHEALTHY,
                    message="Redis connection failed",
                    latency_ms=latency
                )
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            return ComponentHealth(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis check failed: {str(e)}",
                latency_ms=latency
            )
    
    def check_system_resources(self) -> ComponentHealth:
        """检查系统资源"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # 判断资源状态
            if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
                status = HealthStatus.DEGRADED
                message = "System resources are running low"
            else:
                status = HealthStatus.HEALTHY
                message = "System resources are healthy"
            
            return ComponentHealth(
                name="system",
                status=status,
                message=message,
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_used_gb": round(memory.used / (1024**3), 2),
                    "memory_total_gb": round(memory.total / (1024**3), 2),
                    "disk_percent": disk.percent,
                    "disk_used_gb": round(disk.used / (1024**3), 2),
                    "disk_total_gb": round(disk.total / (1024**3), 2),
                }
            )
        except Exception as e:
            return ComponentHealth(
                name="system",
                status=HealthStatus.DEGRADED,
                message=f"System check failed: {str(e)}"
            )
    
    def check_all(self) -> HealthCheckResult:
        """执行所有健康检查"""
        checks = {}
        overall_status = HealthStatus.HEALTHY
        
        # 检查数据库
        db_health = self.check_database()
        checks["database"] = asdict(db_health)
        if db_health.status == HealthStatus.UNHEALTHY:
            overall_status = HealthStatus.UNHEALTHY
        elif db_health.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
            overall_status = HealthStatus.DEGRADED
        
        # 检查Redis
        redis_health = self.check_redis()
        checks["redis"] = asdict(redis_health)
        if redis_health.status == HealthStatus.UNHEALTHY:
            overall_status = HealthStatus.UNHEALTHY
        elif redis_health.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
            overall_status = HealthStatus.DEGRADED
        
        # 检查系统资源
        system_health = self.check_system_resources()
        checks["system"] = asdict(system_health)
        if system_health.status == HealthStatus.UNHEALTHY:
            overall_status = HealthStatus.UNHEALTHY
        elif system_health.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
            overall_status = HealthStatus.DEGRADED
        
        return HealthCheckResult(
            status=overall_status,
            service=self.service_name,
            version=self.version,
            timestamp=datetime.utcnow().isoformat(),
            uptime=time.time() - self.start_time,
            checks=checks
        )


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, service_name: str):
        """
        初始化指标收集器
        
        Args:
            service_name: 服务名称
        """
        self.service_name = service_name
        self.start_time = time.time()
        self.request_count = 0
        self.error_count = 0
        self.request_latencies = []
    
    def record_request(self, latency: float, status_code: int):
        """
        记录请求
        
        Args:
            latency: 请求延迟（秒）
            status_code: 状态码
        """
        self.request_count += 1
        self.request_latencies.append(latency)
        
        if status_code >= 400:
            self.error_count += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        uptime = time.time() - self.start_time
        
        # 计算延迟统计
        if self.request_latencies:
            avg_latency = sum(self.request_latencies) / len(self.request_latencies)
            max_latency = max(self.request_latencies)
            min_latency = min(self.request_latencies)
        else:
            avg_latency = max_latency = min_latency = 0
        
        return {
            "service": self.service_name,
            "uptime_seconds": uptime,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0,
            "avg_latency_ms": avg_latency * 1000,
            "max_latency_ms": max_latency * 1000,
            "min_latency_ms": min_latency * 1000,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def reset(self):
        """重置指标"""
        self.request_count = 0
        self.error_count = 0
        self.request_latencies = []


# 全局健康检查器和指标收集器实例
def get_health_checker(service_name: str) -> HealthChecker:
    """获取健康检查器"""
    return HealthChecker(service_name)


def get_metrics_collector(service_name: str) -> MetricsCollector:
    """获取指标收集器"""
    return MetricsCollector(service_name)