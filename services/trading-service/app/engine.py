"""
交易引擎
提供订单管理、成交处理、模拟交易等功能
"""
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import logging
import asyncio

logger = logging.getLogger(__name__)


class OrderStatus(str, Enum):
    """订单状态"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderDirection(str, Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """订单类型"""
    LIMIT = "limit"
    MARKET = "market"


@dataclass
class Order:
    """订单"""
    order_id: str
    strategy_id: Optional[int]
    code: str
    direction: OrderDirection
    order_type: OrderType
    price: float
    quantity: int
    filled_quantity: int = 0
    avg_price: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    create_time: datetime = field(default_factory=datetime.now)
    update_time: datetime = field(default_factory=datetime.now)
    submit_time: Optional[datetime] = None
    filled_time: Optional[datetime] = None
    reject_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def remaining_quantity(self) -> int:
        """剩余数量"""
        return self.quantity - self.filled_quantity
    
    @property
    def is_active(self) -> bool:
        """是否活跃"""
        return self.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "order_id": self.order_id,
            "strategy_id": self.strategy_id,
            "code": self.code,
            "direction": self.direction.value,
            "order_type": self.order_type.value,
            "price": self.price,
            "quantity": self.quantity,
            "filled_quantity": self.filled_quantity,
            "avg_price": self.avg_price,
            "status": self.status.value,
            "create_time": self.create_time.isoformat(),
            "update_time": self.update_time.isoformat(),
            "submit_time": self.submit_time.isoformat() if self.submit_time else None,
            "filled_time": self.filled_time.isoformat() if self.filled_time else None,
            "reject_reason": self.reject_reason,
            "metadata": self.metadata,
        }


@dataclass
class Trade:
    """成交记录"""
    trade_id: str
    order_id: str
    code: str
    direction: OrderDirection
    price: float
    quantity: int
    amount: float
    commission: float
    slippage: float
    trade_time: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "trade_id": self.trade_id,
            "order_id": self.order_id,
            "code": self.code,
            "direction": self.direction.value,
            "price": self.price,
            "quantity": self.quantity,
            "amount": self.amount,
            "commission": self.commission,
            "slippage": self.slippage,
            "trade_time": self.trade_time.isoformat(),
            "metadata": self.metadata,
        }


class TradingEngine:
    """交易引擎"""
    
    def __init__(
        self,
        commission_rate: float = 0.0003,
        slippage_rate: float = 0.001,
        min_commission: float = 5.0,
        stamp_tax_rate: float = 0.001,
    ):
        """
        初始化交易引擎
        
        Args:
            commission_rate: 佣金费率
            slippage_rate: 滑点费率
            min_commission: 最低佣金
            stamp_tax_rate: 印花税费率
        """
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.min_commission = min_commission
        self.stamp_tax_rate = stamp_tax_rate
        
        self._orders: Dict[str, Order] = {}
        self._trades: List[Trade] = []
        self._positions: Dict[str, Dict[str, Any]] = {}
        self._capital: float = 0.0
        
        self._trade_counter: int = 0
        self._callbacks: Dict[str, List] = {}
        
        self._initialized = False
        self._running = False
        
    async def initialize(self, initial_capital: float = 100000.0):
        """初始化交易引擎"""
        self._capital = initial_capital
        self._initialized = True
        self._running = True
        
        logger.info(f"Trading engine initialized with capital: {initial_capital}")
    
    async def shutdown(self):
        """关闭交易引擎"""
        self._running = False
        logger.info("Trading engine shutdown")
    
    def register_callback(self, event: str, callback):
        """注册回调函数"""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)
    
    def _emit_event(self, event: str, data: Any):
        """触发事件"""
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Callback error: {e}")
    
    def calculate_commission(self, amount: float, direction: OrderDirection) -> float:
        """计算佣金"""
        commission = amount * self.commission_rate
        return max(commission, self.min_commission)
    
    def calculate_slippage(self, price: float, direction: OrderDirection) -> float:
        """计算滑点"""
        return price * self.slippage_rate
    
    def calculate_tax(self, amount: float, direction: OrderDirection) -> float:
        """计算印花税"""
        if direction == OrderDirection.SELL:
            return amount * self.stamp_tax_rate
        return 0.0
    
    def create_order(
        self,
        code: str,
        direction: OrderDirection,
        order_type: OrderType,
        price: float,
        quantity: int,
        strategy_id: Optional[int] = None,
        metadata: Dict[str, Any] = None,
    ) -> Order:
        """
        创建订单
        
        Args:
            code: 股票代码
            direction: 交易方向
            order_type: 订单类型
            price: 价格
            quantity: 数量
            strategy_id: 策略ID
            metadata: 元数据
        
        Returns:
            订单对象
        """
        # 验证参数
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if price <= 0:
            raise ValueError("Price must be positive")
        if quantity % 100 != 0:
            raise ValueError("Quantity must be a multiple of 100")
        
        # 生成订单ID
        order_id = f"O{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"
        
        # 创建订单
        order = Order(
            order_id=order_id,
            strategy_id=strategy_id,
            code=code,
            direction=direction,
            order_type=order_type,
            price=price,
            quantity=quantity,
            metadata=metadata or {},
        )
        
        self._orders[order_id] = order
        
        logger.info(f"Order created: {order_id} {direction.value} {code} x {quantity} @ {price}")
        self._emit_event("order_created", order)
        
        return order
    
    async def submit_order(self, order_id: str) -> bool:
        """
        提交订单 - 下单前调用 risk-service 风控检查，成交后调用 portfolio-service 回填持仓
        """
        order = self._orders.get(order_id)
        if not order:
            logger.error(f"Order not found: {order_id}")
            return False

        if order.status != OrderStatus.PENDING:
            logger.error(f"Order status invalid: {order.status}")
            return False

        # 风控检查：调用 risk-service
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    "http://risk-service:8005/risk/check",
                    json={
                        "order_no": order.order_id,
                        "code": order.code,
                        "direction": order.direction.value,
                        "price": order.price,
                        "quantity": order.quantity,
                    },
                    params={"total_capital": self._capital + sum(
                        p.get("quantity", 0) * p.get("avg_price", 0) for p in self._positions.values()
                    )},
                )
                if resp.status_code == 200:
                    risk_result = resp.json()
                    if not risk_result.get("passed", True):
                        order.status = OrderStatus.REJECTED
                        order.reject_reason = f"风控拦截: {risk_result.get('message', '')}"
                        self._emit_event("order_rejected", order)
                        logger.warning(f"Order rejected by risk: {order_id} - {risk_result.get('message')}")
                        return False
        except Exception as e:
            # 风控不可用时降级为通过，避免阻断
            logger.warning(f"Risk check unavailable, proceeding: {e}")

        # 检查资金/持仓
        if order.direction == OrderDirection.BUY:
            total_cost = order.price * order.quantity * (1 + self.slippage_rate)
            if total_cost > self._capital:
                order.status = OrderStatus.REJECTED
                order.reject_reason = "Insufficient capital"
                self._emit_event("order_rejected", order)
                return False
        elif order.direction == OrderDirection.SELL:
            position = self._positions.get(order.code, {})
            available_quantity = position.get("quantity", 0) - position.get("frozen", 0)
            if order.quantity > available_quantity:
                order.status = OrderStatus.REJECTED
                order.reject_reason = "Insufficient position"
                self._emit_event("order_rejected", order)
                return False

            # 冻结持仓
            position["frozen"] = position.get("frozen", 0) + order.quantity

        # 更新状态
        order.status = OrderStatus.SUBMITTED
        order.submit_time = datetime.now()
        order.update_time = datetime.now()

        logger.info(f"Order submitted: {order_id}")
        self._emit_event("order_submitted", order)

        # 模拟成交
        await self._simulate_fill(order)

        return True
    
    async def _simulate_fill(self, order: Order):
        """模拟成交"""
        import asyncio
        import random
        
        # 模拟延迟
        await asyncio.sleep(random.uniform(0.01, 0.1))
        
        # 计算滑点
        slippage = self.calculate_slippage(order.price, order.direction)
        
        if order.direction == OrderDirection.BUY:
            fill_price = order.price * (1 + slippage / order.price)
        else:
            fill_price = order.price * (1 - slippage / order.price)
        
        # 计算费用
        amount = fill_price * order.quantity
        commission = self.calculate_commission(amount, order.direction)
        tax = self.calculate_tax(amount, order.direction)
        
        # 更新订单
        order.filled_quantity = order.quantity
        order.avg_price = fill_price
        order.status = OrderStatus.FILLED
        order.filled_time = datetime.now()
        order.update_time = datetime.now()
        
        # 创建成交记录
        self._trade_counter += 1
        trade = Trade(
            trade_id=f"T{datetime.now().strftime('%Y%m%d%H%M%S')}{self._trade_counter:04d}",
            order_id=order.order_id,
            code=order.code,
            direction=order.direction,
            price=fill_price,
            quantity=order.quantity,
            amount=amount,
            commission=commission,
            slippage=slippage,
            metadata=order.metadata,
        )
        
        self._trades.append(trade)
        
        # 更新资金和持仓
        if order.direction == OrderDirection.BUY:
            total_cost = amount + commission
            self._capital -= total_cost
            
            if order.code in self._positions:
                pos = self._positions[order.code]
                total_quantity = pos["quantity"] + order.quantity
                pos["avg_price"] = (pos["avg_price"] * pos["quantity"] + fill_price * order.quantity) / total_quantity
                pos["quantity"] = total_quantity
            else:
                self._positions[order.code] = {
                    "quantity": order.quantity,
                    "avg_price": fill_price,
                    "frozen": 0,
                }
        elif order.direction == OrderDirection.SELL:
            pos = self._positions[order.code]
            pos["quantity"] -= order.quantity
            pos["frozen"] -= order.quantity
            
            if pos["quantity"] == 0:
                del self._positions[order.code]
            
            self._capital += amount - commission - tax
        
        logger.info(f"Order filled: {order.order_id} at {fill_price}")
        self._emit_event("order_filled", order)
        self._emit_event("trade_executed", trade)

        # 同步成交到 portfolio-service（增量）
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    "http://portfolio-service:8004/portfolio/process-trade",
                    json={
                        "code": trade.code,
                        "direction": trade.direction.value,
                        "price": trade.price,
                        "quantity": trade.quantity,
                        "commission": trade.commission,
                        "tax": 0.0,
                        "name": "",
                        "order_no": trade.order_id,
                        "trade_time": trade.trade_time.isoformat(),
                    },
                )
        except Exception as e:
            logger.warning(f"Portfolio sync failed (non-blocking): {e}")
    
    async def cancel_order(self, order_id: str) -> bool:
        """
        取消订单
        
        Args:
            order_id: 订单ID
        
        Returns:
            是否成功
        """
        order = self._orders.get(order_id)
        if not order:
            logger.error(f"Order not found: {order_id}")
            return False
        
        if not order.is_active:
            logger.error(f"Order cannot be cancelled: {order.status}")
            return False
        
        # 解冻持仓
        if order.direction == OrderDirection.SELL and order.code in self._positions:
            self._positions[order.code]["frozen"] -= order.remaining_quantity
        
        # 更新状态
        order.status = OrderStatus.CANCELLED
        order.update_time = datetime.now()
        
        logger.info(f"Order cancelled: {order_id}")
        self._emit_event("order_cancelled", order)
        
        return True
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """获取订单"""
        return self._orders.get(order_id)
    
    def get_orders(
        self,
        code: Optional[str] = None,
        direction: Optional[OrderDirection] = None,
        status: Optional[OrderStatus] = None,
        limit: int = 100,
    ) -> List[Order]:
        """获取订单列表"""
        orders = list(self._orders.values())
        
        if code:
            orders = [o for o in orders if o.code == code]
        if direction:
            orders = [o for o in orders if o.direction == direction]
        if status:
            orders = [o for o in orders if o.status == status]
        
        # 按创建时间倒序
        orders.sort(key=lambda o: o.create_time, reverse=True)
        
        return orders[:limit]
    
    def get_trades(
        self,
        code: Optional[str] = None,
        direction: Optional[OrderDirection] = None,
        limit: int = 100,
    ) -> List[Trade]:
        """获取成交列表"""
        trades = self._trades.copy()
        
        if code:
            trades = [t for t in trades if t.code == code]
        if direction:
            trades = [t for t in trades if t.direction == direction]
        
        # 按成交时间倒序
        trades.sort(key=lambda t: t.trade_time, reverse=True)
        
        return trades[:limit]
    
    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """获取持仓"""
        return self._positions.copy()
    
    def get_position(self, code: str) -> Optional[Dict[str, Any]]:
        """获取单只股票持仓"""
        return self._positions.get(code)
    
    def get_capital(self) -> float:
        """获取可用资金"""
        return self._capital
    
    def get_total_value(self, prices: Dict[str, float] = None) -> float:
        """
        获取总资产
        
        Args:
            prices: 当前价格字典
        
        Returns:
            总资产
        """
        position_value = 0.0
        for code, pos in self._positions.items():
            current_price = prices.get(code, pos["avg_price"]) if prices else pos["avg_price"]
            position_value += pos["quantity"] * current_price
        
        return self._capital + position_value
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_orders = len(self._orders)
        active_orders = len([o for o in self._orders.values() if o.is_active])
        total_trades = len(self._trades)
        
        return {
            "total_orders": total_orders,
            "active_orders": active_orders,
            "total_trades": total_trades,
            "capital": self._capital,
            "positions": len(self._positions),
        }


# 全局交易引擎实例
trading_engine = TradingEngine()