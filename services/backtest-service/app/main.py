"""
回测服务主入口
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time

from app.routers import backtest
from common import (
    setup_logging,
    settings,
    RequestMiddleware,
    PerformanceMiddleware,
    CORSMiddleware,
    quant_exception_handler,
    general_exception_handler,
    QuantBaseException,
    auth_service,
    auth_router as auth_routes,
)

# 配置日志
logger = setup_logging("backtest-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Backtest Service starting up...")
    await auth_service.initialize(secret_key=settings.SECRET_KEY)
    yield
    logger.info("Backtest Service shutting down...")


app = FastAPI(
    title="Backtest Service",
    description="量化回测服务",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# 添加中间件
app.add_middleware(RequestMiddleware, service_name="backtest-service")
app.add_middleware(PerformanceMiddleware, service_name="backtest-service", slow_threshold=1.0)
app.add_middleware(CORSMiddleware)

# Prometheus 监控
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app)
except Exception as e:
    logger.warning(f"Prometheus instrumentation failed: {e}")

# 添加异常处理器
app.add_exception_handler(QuantBaseException, quant_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# 注册路由
API_V1_PREFIX = "/api/v1"
app.include_router(backtest.router, prefix="/backtest", tags=["backtest"])
app.include_router(backtest.router, prefix=f"{API_V1_PREFIX}/backtest", tags=["backtest"])

# 认证路由
app.include_router(auth_routes, prefix="/auth", tags=["auth"])
app.include_router(auth_routes, prefix=f"{API_V1_PREFIX}/auth", tags=["auth"])


@app.get("/health", tags=["health"])
async def health_check():
    """健康检查"""
    from datetime import datetime
    return {
        "status": "healthy",
        "service": "backtest-service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)