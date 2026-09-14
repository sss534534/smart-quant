"""
统一错误处理模块
定义系统异常类型和错误处理机制
"""
from typing import Any, Dict, Optional
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """错误响应模型"""
    code: int
    message: str
    detail: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: str


class QuantBaseException(Exception):
    """量化系统基础异常类"""
    
    def __init__(
        self,
        code: int = 500,
        message: str = "Internal server error",
        detail: Optional[str] = None
    ):
        self.code = code
        self.message = message
        self.detail = detail
        super().__init__(self.message)


class DataException(QuantBaseException):
    """数据相关异常"""
    
    def __init__(
        self,
        message: str = "Data service error",
        detail: Optional[str] = None,
        code: int = 500
    ):
        super().__init__(code=code, message=message, detail=detail)


class StrategyException(QuantBaseException):
    """策略相关异常"""
    
    def __init__(
        self,
        message: str = "Strategy engine error",
        detail: Optional[str] = None,
        code: int = 500
    ):
        super().__init__(code=code, message=message, detail=detail)


class TradingException(QuantBaseException):
    """交易相关异常"""
    
    def __init__(
        self,
        message: str = "Trading service error",
        detail: Optional[str] = None,
        code: int = 500
    ):
        super().__init__(code=code, message=message, detail=detail)


class RiskException(QuantBaseException):
    """风控相关异常"""
    
    def __init__(
        self,
        message: str = "Risk control triggered",
        detail: Optional[str] = None,
        code: int = 400
    ):
        super().__init__(code=code, message=message, detail=detail)


class BacktestException(QuantBaseException):
    """回测相关异常"""
    
    def __init__(
        self,
        message: str = "Backtest service error",
        detail: Optional[str] = None,
        code: int = 500
    ):
        super().__init__(code=code, message=message, detail=detail)


class PortfolioException(QuantBaseException):
    """组合相关异常"""
    
    def __init__(
        self,
        message: str = "Portfolio service error",
        detail: Optional[str] = None,
        code: int = 500
    ):
        super().__init__(code=code, message=message, detail=detail)


class ValidationException(QuantBaseException):
    """数据验证异常"""
    
    def __init__(
        self,
        message: str = "Validation error",
        detail: Optional[str] = None,
        code: int = 400
    ):
        super().__init__(code=code, message=message, detail=detail)


class NotFoundException(QuantBaseException):
    """资源不存在异常"""
    
    def __init__(
        self,
        resource: str = "Resource",
        resource_id: Any = None,
        detail: Optional[str] = None
    ):
        message = f"{resource} not found"
        if resource_id:
            message = f"{resource} with id {resource_id} not found"
        super().__init__(code=404, message=message, detail=detail)


class PermissionException(QuantBaseException):
    """权限异常"""
    
    def __init__(
        self,
        message: str = "Permission denied",
        detail: Optional[str] = None
    ):
        super().__init__(code=403, message=message, detail=detail)


async def quant_exception_handler(request: Request, exc: QuantBaseException) -> JSONResponse:
    """量化系统异常处理器"""
    from datetime import datetime
    
    error_response = ErrorResponse(
        code=exc.code,
        message=exc.message,
        detail=exc.detail,
        request_id=request.state.request_id if hasattr(request.state, 'request_id') else None,
        timestamp=datetime.utcnow().isoformat()
    )
    
    return JSONResponse(
        status_code=exc.code,
        content=error_response.model_dump()
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """通用异常处理器"""
    from datetime import datetime
    
    error_response = ErrorResponse(
        code=500,
        message="Internal server error",
        detail=str(exc),
        request_id=request.state.request_id if hasattr(request.state, 'request_id') else None,
        timestamp=datetime.utcnow().isoformat()
    )
    
    return JSONResponse(
        status_code=500,
        content=error_response.model_dump()
    )


def raise_not_found(resource: str = "Resource", resource_id: Any = None):
    """抛出资源不存在异常"""
    raise NotFoundException(resource=resource, resource_id=resource_id)


def raise_validation_error(message: str, detail: Optional[str] = None):
    """抛出验证异常"""
    raise ValidationException(message=message, detail=detail)


def raise_data_error(message: str, detail: Optional[str] = None):
    """抛出数据异常"""
    raise DataException(message=message, detail=detail)


def raise_strategy_error(message: str, detail: Optional[str] = None):
    """抛出策略异常"""
    raise StrategyException(message=message, detail=detail)


def raise_trading_error(message: str, detail: Optional[str] = None):
    """抛出交易异常"""
    raise TradingException(message=message, detail=detail)


def raise_risk_error(message: str, detail: Optional[str] = None):
    """抛出风控异常"""
    raise RiskException(message=message, detail=detail)


def raise_backtest_error(message: str, detail: Optional[str] = None):
    """抛出回测异常"""
    raise BacktestException(message=message, detail=detail)


def raise_portfolio_error(message: str, detail: Optional[str] = None):
    """抛出组合异常"""
    raise PortfolioException(message=message, detail=detail)