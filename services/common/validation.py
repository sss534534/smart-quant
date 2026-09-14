"""
输入验证模块
使用Pydantic进行请求数据验证和序列化
"""
from datetime import datetime, date
from typing import Optional, List, Any, Dict, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


class OrderDirection(str, Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """订单类型"""
    LIMIT = "limit"
    MARKET = "market"


class OrderStatus(str, Enum):
    """订单状态"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class PositionDirection(str, Enum):
    """持仓方向"""
    LONG = "long"
    SHORT = "short"


class RiskType(str, Enum):
    """风险类型"""
    POSITION_LIMIT = "position_limit"
    SINGLE_TRADE_LIMIT = "single_trade_limit"
    DAILY_LIMIT = "daily_limit"
    MAX_LOSS_LIMIT = "max_loss_limit"
    MAX_POSITION_LOSS = "max_position_loss"
    POSITION_PERCENTAGE = "position_percentage"
    RISK_VALUE = "risk_value"
    DRAWDOWN = "drawdown"


class BaseRequest(BaseModel):
    """基础请求模型"""
    
    class Config:
        # 允许从 orm 模型转换
        from_attributes = True
        # 使用枚举值
        use_enum_values = True


class PaginationRequest(BaseRequest):
    """分页请求"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")


class StockCodeRequest(BaseRequest):
    """股票代码请求"""
    code: str = Field(..., min_length=6, max_length=6, pattern=r'^\d{6}$', description="股票代码")
    
    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        """验证股票代码格式"""
        if not v.isdigit():
            raise ValueError('股票代码必须为纯数字')
        return v


class DateRangeRequest(BaseRequest):
    """日期范围请求"""
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    
    @model_validator(mode='after')
    def validate_date_range(self) -> 'DateRangeRequest':
        """验证日期范围"""
        if self.start_date > self.end_date:
            raise ValueError('开始日期不能大于结束日期')
        return self


class OrderCreateRequest(BaseRequest):
    """创建订单请求"""
    strategy_id: Optional[int] = Field(None, description="策略ID")
    code: str = Field(..., min_length=6, max_length=6, pattern=r'^\d{6}$', description="股票代码")
    direction: OrderDirection = Field(..., description="交易方向")
    order_type: OrderType = Field(OrderType.LIMIT, description="订单类型")
    price: Optional[float] = Field(None, gt=0, description="委托价格")
    quantity: int = Field(..., gt=0, description="委托数量")
    
    @model_validator(mode='after')
    def validate_order(self) -> 'OrderCreateRequest':
        """验证订单参数"""
        if self.order_type == OrderType.LIMIT and self.price is None:
            raise ValueError('限价单必须指定价格')
        return self


class OrderQueryRequest(PaginationRequest):
    """订单查询请求"""
    code: Optional[str] = Field(None, min_length=6, max_length=6, description="股票代码")
    direction: Optional[OrderDirection] = Field(None, description="交易方向")
    status: Optional[OrderStatus] = Field(None, description="订单状态")
    start_date: Optional[datetime] = Field(None, description="开始时间")
    end_date: Optional[datetime] = Field(None, description="结束时间")


class StrategyCreateRequest(BaseRequest):
    """创建策略请求"""
    name: str = Field(..., min_length=1, max_length=100, description="策略名称")
    code: str = Field(..., min_length=1, max_length=50, description="策略代码")
    type: str = Field(..., description="策略类型")
    description: Optional[str] = Field(None, description="策略描述")
    params: Dict[str, Any] = Field(default_factory=dict, description="策略参数")


class StrategyUpdateRequest(BaseRequest):
    """更新策略请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="策略名称")
    description: Optional[str] = Field(None, description="策略描述")
    params: Optional[Dict[str, Any]] = Field(None, description="策略参数")
    status: Optional[str] = Field(None, description="策略状态")


class BacktestCreateRequest(BaseRequest):
    """创建回测请求"""
    name: str = Field(..., min_length=1, max_length=200, description="回测名称")
    strategy_id: int = Field(..., description="策略ID")
    code_list: List[str] = Field(..., min_length=1, description="测试股票列表")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    initial_capital: float = Field(100000, gt=0, description="初始资金")
    commission_rate: float = Field(0.0003, ge=0, le=0.01, description="佣金率")
    slip_rate: float = Field(0.001, ge=0, le=0.05, description="滑点率")
    params: Dict[str, Any] = Field(default_factory=dict, description="回测参数")


class RiskLimitCreateRequest(BaseRequest):
    """创建风控限额请求"""
    limit_name: str = Field(..., min_length=1, max_length=100, description="限额名称")
    risk_type: RiskType = Field(..., description="风险类型")
    limit_value: float = Field(..., gt=0, description="限额值")
    warning_value: Optional[float] = Field(None, ge=0, description="警告值")
    description: Optional[str] = Field(None, description="描述")
    enabled: bool = Field(True, description="是否启用")


class MarketDataQueryRequest(BaseRequest):
    """市场数据查询请求"""
    code: str = Field(..., min_length=6, max_length=6, description="股票代码")
    data_type: str = Field("kline_1d", description="数据类型")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")
    limit: int = Field(100, ge=1, le=1000, description="返回数量")


class PortfolioSummaryRequest(BaseRequest):
    """组合摘要请求"""
    account_no: str = Field(..., description="账户号")


class RiskCheckRequest(BaseRequest):
    """风控检查请求"""
    order_no: str = Field(..., description="订单号")
    code: str = Field(..., min_length=6, max_length=6, description="股票代码")
    direction: OrderDirection = Field(..., description="交易方向")
    price: float = Field(..., gt=0, description="价格")
    quantity: int = Field(..., gt=0, description="数量")


# 响应模型
class PaginationResponse(BaseModel):
    """分页响应"""
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="每页数量")
    items: List[Any] = Field(..., description="数据列表")


class OrderResponse(BaseModel):
    """订单响应"""
    id: int
    order_no: str
    strategy_id: Optional[int]
    code: str
    direction: OrderDirection
    order_type: OrderType
    price: Optional[float]
    quantity: int
    filled_quantity: int
    avg_price: Optional[float]
    status: OrderStatus
    submit_time: datetime
    update_time: datetime
    filled_time: Optional[datetime]
    reject_reason: Optional[str]
    
    class Config:
        from_attributes = True


class StrategyResponse(BaseModel):
    """策略响应"""
    id: int
    name: str
    code: str
    type: str
    description: Optional[str]
    params: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BacktestResponse(BaseModel):
    """回测响应"""
    id: int
    name: str
    strategy_id: int
    code_list: List[str]
    start_date: datetime
    end_date: datetime
    initial_capital: float
    commission_rate: float
    slip_rate: float
    status: str
    progress: int
    params: Dict[str, Any]
    created_by: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    error_msg: Optional[str]
    
    class Config:
        from_attributes = True


class RiskLimitResponse(BaseModel):
    """风控限额响应"""
    id: int
    limit_name: str
    risk_type: RiskType
    limit_value: float
    warning_value: Optional[float]
    description: Optional[str]
    enabled: bool
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PositionResponse(BaseModel):
    """持仓响应"""
    id: int
    code: str
    name: Optional[str]
    direction: PositionDirection
    quantity: int
    avg_cost: Optional[float]
    avg_price: Optional[float]
    current_price: Optional[float]
    frozen_quantity: int
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AccountResponse(BaseModel):
    """账户响应"""
    id: int
    account_no: str
    account_type: str
    balance: float
    frozen_balance: float
    total_deposited: float
    total_withdrawn: float
    total_profit: float
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    service: str
    version: str
    timestamp: datetime
    uptime: Optional[float] = None


class ErrorResponse(BaseModel):
    """错误响应"""
    code: int
    message: str
    detail: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: datetime