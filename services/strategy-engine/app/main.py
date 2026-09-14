"""
策略引擎服务主入口
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import logging

from app.routers import strategy
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
logger = setup_logging("strategy-engine")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Strategy Engine starting up...")
    from common import init_db, auth_service, scheduler
    init_db()
    await auth_service.initialize(secret_key=settings.SECRET_KEY)
    # 启动定时任务：每分钟推送 bar 给运行中策略
    scheduler.start()
    from app.feed import feed_market_bars
    # 每 30 秒把最新 quote 喂给运行中的策略
    scheduler.add_interval_job("feed_bars", feed_market_bars, seconds=30)
    from app.bridge import register_handlers
    register_handlers()
    yield
    scheduler.shutdown()
    logger.info("Strategy Engine shutting down...")


app = FastAPI(
    title="Strategy Engine",
    description="量化策略引擎服务",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "strategy", "description": "策略管理"},
        {"name": "health", "description": "健康检查"},
        {"name": "metrics", "description": "服务指标"},
    ],
)

# 添加中间件
app.add_middleware(RequestMiddleware, service_name="strategy-engine")
app.add_middleware(PerformanceMiddleware, service_name="strategy-engine", slow_threshold=1.0)
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

# API版本前缀
API_V1_PREFIX = "/api/v1"

# 注册路由（支持版本控制）
app.include_router(
    strategy.router,
    prefix=f"{API_V1_PREFIX}/strategy",
    tags=["strategy"],
    responses={404: {"description": "Not found"}},
)

# 兼容旧路由（无版本前缀）
app.include_router(
    strategy.router,
    prefix="/strategy",
    tags=["strategy"],
    responses={404: {"description": "Not found"}},
)

# 认证路由
app.include_router(auth_routes, prefix="/auth", tags=["auth"])
app.include_router(auth_routes, prefix=f"{API_V1_PREFIX}/auth", tags=["auth"])


@app.get("/health", tags=["health"])
async def health_check():
    """健康检查"""
    from datetime import datetime
    return {
        "status": "healthy",
        "service": "strategy-engine",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/", tags=["root"])
async def root():
    """根路径"""
    return {
        "service": "strategy-engine",
        "version": "1.0.0",
        "docs": "/docs",
        "api_prefix": API_V1_PREFIX,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)