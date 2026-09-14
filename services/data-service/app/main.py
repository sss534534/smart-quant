"""
数据服务主入口
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time

from app.routers import market
from common import (
    setup_logging,
    settings,
    init_db,
    RequestMiddleware,
    PerformanceMiddleware,
    CORSMiddleware,
    quant_exception_handler,
    general_exception_handler,
    QuantBaseException,
    auth_router as auth_routes,
)

# 配置日志
logger = setup_logging("data-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Data Service starting up...")
    # 初始化数据库
    init_db()
    # 初始化认证服务
    from common import auth_service, scheduler
    await auth_service.initialize(secret_key=settings.SECRET_KEY)
    # 启动定时任务：交易日 15:30 拉取日线缓存
    scheduler.start()
    yield
    scheduler.shutdown()
    logger.info("Data Service shutting down...")


app = FastAPI(
    title="Data Service",
    description="量化数据服务",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "market", "description": "市场数据"},
        {"name": "health", "description": "健康检查"},
        {"name": "metrics", "description": "服务指标"},
    ],
)

# 添加中间件
app.add_middleware(RequestMiddleware, service_name="data-service")
app.add_middleware(PerformanceMiddleware, service_name="data-service", slow_threshold=1.0)
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
    market.router,
    prefix=f"{API_V1_PREFIX}/market",
    tags=["market"],
    responses={404: {"description": "Not found"}},
)

# 兼容旧路由（无版本前缀）
app.include_router(
    market.router,
    prefix="/market",
    tags=["market"],
    responses={404: {"description": "Not found"}},
)

# 认证路由
app.include_router(auth_routes, prefix="/auth", tags=["auth"])
app.include_router(auth_routes, prefix=f"{API_V1_PREFIX}/auth", tags=["auth"])

# WebSocket 实时推送端点
from common import connection_manager


@app.websocket("/ws/{channel}")
async def websocket_endpoint(websocket, channel: str):
    """WebSocket 实时推送频道：market.quote / strategy.signal / trading.order / risk.alert / portfolio.update"""
    await connection_manager.connect(channel, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except Exception:
        connection_manager.disconnect(channel, websocket)


@app.get("/health", tags=["health"])
async def health_check():
    """健康检查"""
    from datetime import datetime
    return {
        "status": "healthy",
        "service": "data-service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/", tags=["root"])
async def root():
    """根路径"""
    return {
        "service": "data-service",
        "version": "1.0.0",
        "docs": "/docs",
        "api_prefix": API_V1_PREFIX,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)