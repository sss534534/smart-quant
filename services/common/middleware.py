"""
请求中间件
提供请求ID生成、日志记录、性能监控等功能
"""
import time
import uuid
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .logging import request_id_var, user_id_var, get_logger


class RequestMiddleware(BaseHTTPMiddleware):
    """请求处理中间件"""
    
    def __init__(self, app: ASGIApp, service_name: str = "unknown"):
        super().__init__(app)
        self.service_name = service_name
        self.logger = get_logger(service_name)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 生成请求ID
        req_id = str(uuid.uuid4())
        request.state.request_id = req_id
        
        # 设置上下文变量
        request_id_var.set(req_id)
        
        # 记录请求开始
        start_time = time.time()
        self.logger.info(
            "Request started",
            method=request.method,
            url=str(request.url),
            client_ip=request.client.host if request.client else None
        )
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录请求完成
            self.logger.info(
                "Request completed",
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                process_time=f"{process_time:.4f}s"
            )
            
            # 添加响应头
            response.headers["X-Request-ID"] = req_id
            response.headers["X-Process-Time"] = f"{process_time:.4f}"
            
            return response
            
        except Exception as e:
            # 记录异常
            process_time = time.time() - start_time
            self.logger.error(
                "Request failed",
                method=request.method,
                url=str(request.url),
                process_time=f"{process_time:.4f}s",
                error=str(e)
            )
            raise


class PerformanceMiddleware(BaseHTTPMiddleware):
    """性能监控中间件"""
    
    def __init__(self, app: ASGIApp, service_name: str = "unknown", slow_threshold: float = 1.0):
        super().__init__(app)
        self.service_name = service_name
        self.logger = get_logger(service_name)
        self.slow_threshold = slow_threshold
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # 记录慢请求
        if process_time > self.slow_threshold:
            self.logger.warning(
                "Slow request detected",
                method=request.method,
                url=str(request.url),
                process_time=f"{process_time:.4f}s",
                threshold=f"{self.slow_threshold}s"
            )
        
        return response


class CORSMiddleware(BaseHTTPMiddleware):
    """CORS中间件"""
    
    def __init__(
        self,
        app: ASGIApp,
        allow_origins: Optional[list] = None,
        allow_methods: Optional[list] = None,
        allow_headers: Optional[list] = None,
        allow_credentials: bool = False
    ):
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["*"]
        self.allow_headers = allow_headers or ["*"]
        self.allow_credentials = allow_credentials
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method == "OPTIONS":
            response = Response()
        else:
            response = await call_next(request)
        
        # 添加CORS头
        origin = request.headers.get("Origin")
        if origin and ( "*" in self.allow_origins or origin in self.allow_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
        elif "*" in self.allow_origins:
            response.headers["Access-Control-Allow-Origin"] = "*"
        
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
        
        if self.allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return response