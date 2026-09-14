"""
组合引擎
提供持仓管理、资金账户、盈亏归因、组合分析等功能
"""
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class PositionDirection(str, Enum):
    """持仓方向"""
    LONG = "long"
    SHORT = "short"


class PositionStatus(str, Enum):
    """持仓状态"""
    ACTIVE = "active"
    CLOSED = "closed"
    LIQUIDATED = "liquidated"


@dataclass
class Position:
    """持仓（运行时）"""
    code: str
    name: str = ""
    direction: PositionDirection = PositionDirection.LONG
    quantity: int = 0
    avg_cost: float = 0.0       # 含交易费用的成本
    avg_price: float = 0.0     # 不含费用的均价
    current_price: float = 0.0
    frozen_quantity: int = 0
    status: PositionStatus = PositionStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    closed_at: Optional[datetime] = None
    realized_pnl: float = 0.0
    total_buy_amount: float = 0.0
    total_sell_amount: float = 0.0
    total_commission: float = 0.0
    total_tax: float = 0.0

    @property
    def market_value(self) -> float:
        """市值"""
        return self.quantity * self.current_price if self.current_price else 0.0

    @property
    def cost_value(self) -> float:
        """成本市值"""
        return self.quantity * self.avg_cost

    @property
    def unrealized_pnl(self) -> float:
        """浮动盈亏"""
        return (self.current_price - self.avg_cost) * self.quantity if self.current_price else 0.0

    @property
    def unrealized_pnl_pct(self) -> float:
        """浮动盈亏比例"""
        if self.avg_cost <= 0:
            return 0.0
        return (self.current_price - self.avg_cost) / self.avg_cost

    @property
    def total_pnl(self) -> float:
        """总盈亏（已实现+浮动）"""
        return self.realized_pnl + self.unrealized_pnl

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "direction": self.direction.value,
            "quantity": self.quantity,
            "avg_cost": round(self.avg_cost, 4),
            "avg_price": round(self.avg_price, 4),
            "current_price": round(self.current_price, 4),
            "frozen_quantity": self.frozen_quantity,
            "status": self.status.value,
            "market_value": round(self.market_value, 2),
            "cost_value": round(self.cost_value, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "unrealized_pnl_pct": round(self.unrealized_pnl_pct, 4),
            "realized_pnl": round(self.realized_pnl, 2),
            "total_pnl": round(self.total_pnl, 2),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class Account:
    """资金账户（运行时）"""
    account_no: str
    account_type: str = "cash"
    balance: float = 0.0          # 可用资金
    frozen_balance: float = 0.0
    total_deposited: float = 0.0
    total_withdrawn: float = 0.0
    total_profit: float = 0.0
    status: str = "active"

    @property
    def total_assets_at_cost(self) -> float:
        """按成本计总资产（不含浮动）"""
        return self.balance  # 仅现金部分，需调用方加持仓成本

    def to_dict(self) -> Dict[str, Any]:
        return {
            "account_no": self.account_no,
            "account_type": self.account_type,
            "balance": round(self.balance, 2),
            "frozen_balance": round(self.frozen_balance, 2),
            "total_deposited": round(self.total_deposited, 2),
            "total_withdrawn": round(self.total_withdrawn, 2),
            "total_profit": round(self.total_profit, 2),
            "status": self.status,
        }


@dataclass
class AccountLog:
    """资金流水（运行时）"""
    log_id: str
    account_no: str
    type: str               # deposit/withdraw/trade/fee/dividend
    amount: float
    balance_after: float
    description: str = ""
    related_order_no: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_id": self.log_id,
            "account_no": self.account_no,
            "type": self.type,
            "amount": round(self.amount, 2),
            "balance_after": round(self.balance_after, 2),
            "description": self.description,
            "related_order_no": self.related_order_no,
            "created_at": self.created_at.isoformat(),
        }


class PortfolioEngine:
    """组合引擎"""

    DEFAULT_ACCOUNT_NO = "DEFAULT-001"

    def __init__(self):
        self._positions: Dict[str, Position] = {}
        self._account: Optional[Account] = None
        self._logs: List[AccountLog] = []
        self._initialized = False
        self._running = False
        self._initial_capital: float = 100000.0
        self._callbacks: Dict[str, List] = {}

    # ---------- 初始化 ----------
    async def initialize(self, initial_capital: float = 100000.0):
        if self._initialized:
            return
        self._initial_capital = initial_capital
        self._account = Account(
            account_no=self.DEFAULT_ACCOUNT_NO,
            balance=initial_capital,
            total_deposited=initial_capital,
        )
        self._initialized = True
        self._running = True
        logger.info(f"PortfolioEngine initialized with capital={initial_capital}")

    async def shutdown(self):
        self._running = False
        logger.info("PortfolioEngine shutdown")

    # ---------- 事件回调 ----------
    def register_callback(self, event: str, callback):
        self._callbacks.setdefault(event, []).append(callback)

    def _emit_event(self, event: str, data: Any):
        for cb in self._callbacks.get(event, []):
            try:
                cb(data)
            except Exception as e:
                logger.error(f"Callback error on {event}: {e}")

    # ---------- 持仓更新 ----------
    def process_trade(
        self,
        code: str,
        direction: str,
        price: float,
        quantity: int,
        commission: float = 0.0,
        tax: float = 0.0,
        name: str = "",
        order_no: str = "",
        trade_time: Optional[datetime] = None,
    ) -> Tuple[Position, float]:
        """
        处理一笔成交，更新持仓与账户

        Returns:
            (更新后的 Position, 已实现盈亏)
        """
        if not self._initialized:
            raise RuntimeError("PortfolioEngine not initialized")

        if direction not in ("buy", "sell"):
            raise ValueError(f"Invalid direction: {direction}")

        trade_time = trade_time or datetime.now()
        amount = price * quantity
        pos = self._positions.get(code)

        realized_pnl = 0.0

        if direction == "buy":
            # 买入：增加持仓，扣减资金
            if pos is None:
                pos = Position(
                    code=code,
                    name=name,
                    direction=PositionDirection.LONG,
                    quantity=quantity,
                    avg_price=price,
                    avg_cost=price + (commission / quantity if quantity else 0),
                    current_price=price,
                    created_at=trade_time,
                    updated_at=trade_time,
                    total_buy_amount=amount,
                    total_commission=commission,
                )
                self._positions[code] = pos
            else:
                total_quantity = pos.quantity + quantity
                # 加权平均价（不含费用）
                pos.avg_price = (pos.avg_price * pos.quantity + price * quantity) / total_quantity
                # 含费用的成本
                pos.avg_cost = (pos.avg_cost * pos.quantity + amount + commission) / total_quantity
                pos.quantity = total_quantity
                pos.total_buy_amount += amount
                pos.total_commission += commission
                pos.updated_at = trade_time

            # 扣资金
            self._account.balance -= (amount + commission + tax)
            self._add_log("trade", -(amount + commission + tax),
                          description=f"买入 {code} x{quantity}@{price}",
                          related_order_no=order_no, created_at=trade_time)

        elif direction == "sell":
            # 卖出：减少持仓，计算已实现盈亏
            if pos is None or pos.quantity < quantity:
                raise ValueError(f"Insufficient position for {code}: need {quantity}, have {pos.quantity if pos else 0}")

            # 已实现盈亏 = (卖出价 - 成本价) * 数量 - 卖出费用
            realized_pnl = (price - pos.avg_cost) * quantity - commission - tax
            pos.realized_pnl += realized_pnl
            pos.total_sell_amount += amount
            pos.total_commission += commission
            pos.total_tax += tax
            pos.quantity -= quantity
            pos.updated_at = trade_time

            if pos.quantity == 0:
                pos.status = PositionStatus.CLOSED
                pos.closed_at = trade_time

            # 加资金
            self._account.balance += (amount - commission - tax)
            self._account.total_profit += realized_pnl
            self._add_log("trade", amount - commission - tax,
                          description=f"卖出 {code} x{quantity}@{price} 盈亏={realized_pnl:.2f}",
                          related_order_no=order_no, created_at=trade_time)

        self._emit_event("position_updated", pos)
        self._emit_event("trade_settled", {
            "code": code, "direction": direction, "price": price,
            "quantity": quantity, "realized_pnl": realized_pnl,
        })
        return pos, realized_pnl

    def update_price(self, code: str, price: float):
        """更新某只股票当前价"""
        pos = self._positions.get(code)
        if pos and price > 0:
            pos.current_price = price
            pos.updated_at = datetime.now()

    def update_prices(self, prices: Dict[str, float]):
        """批量更新价格"""
        for code, price in prices.items():
            self.update_price(code, price)

    # ---------- 资金操作 ----------
    def deposit(self, amount: float, description: str = "现金存入") -> bool:
        if amount <= 0:
            return False
        self._account.balance += amount
        self._account.total_deposited += amount
        self._add_log("deposit", amount, description=description)
        return True

    def withdraw(self, amount: float, description: str = "现金取出") -> bool:
        if amount <= 0 or amount > self._account.balance:
            return False
        self._account.balance -= amount
        self._account.total_withdrawn += amount
        self._add_log("withdraw", -amount, description=description)
        return True

    def _add_log(self, type_: str, amount: float, description: str = "",
                 related_order_no: Optional[str] = None,
                 created_at: Optional[datetime] = None):
        log = AccountLog(
            log_id=f"L{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}",
            account_no=self._account.account_no,
            type=type_,
            amount=amount,
            balance_after=self._account.balance,
            description=description,
            related_order_no=related_order_no,
            created_at=created_at or datetime.now(),
        )
        self._logs.append(log)
        self._emit_event("account_log", log)

    # ---------- 查询 ----------
    def get_positions(self, status: Optional[str] = None) -> List[Position]:
        positions = list(self._positions.values())
        if status:
            positions = [p for p in positions if p.status.value == status]
        return positions

    def get_position(self, code: str) -> Optional[Position]:
        return self._positions.get(code)

    def get_account(self) -> Account:
        return self._account

    def get_logs(self, limit: int = 100, log_type: Optional[str] = None) -> List[AccountLog]:
        logs = self._logs.copy()
        if log_type:
            logs = [l for l in logs if l.type == log_type]
        logs.sort(key=lambda l: l.created_at, reverse=True)
        return logs[:limit]

    def get_summary(self, prices: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """账户总览"""
        if prices:
            self.update_prices(prices)
        positions_value = sum(p.market_value for p in self._positions.values() if p.status == PositionStatus.ACTIVE)
        positions_cost = sum(p.cost_value for p in self._positions.values() if p.status == PositionStatus.ACTIVE)
        unrealized_pnl = sum(p.unrealized_pnl for p in self._positions.values() if p.status == PositionStatus.ACTIVE)
        realized_pnl = sum(p.realized_pnl for p in self._positions.values())
        total_assets = self._account.balance + positions_value
        total_profit = realized_pnl + unrealized_pnl
        return {
            "total_assets": round(total_assets, 2),
            "cash": round(self._account.balance, 2),
            "frozen_balance": round(self._account.frozen_balance, 2),
            "positions_value": round(positions_value, 2),
            "positions_cost": round(positions_cost, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "realized_pnl": round(realized_pnl, 2),
            "total_profit": round(total_profit, 2),
            "total_profit_pct": round((total_profit / self._initial_capital) if self._initial_capital else 0, 4),
            "initial_capital": round(self._initial_capital, 2),
            "positions_count": len([p for p in self._positions.values() if p.status == PositionStatus.ACTIVE]),
        }

    def get_attribution(self, prices: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """组合归因分析"""
        if prices:
            self.update_prices(prices)
        positions = [p for p in self._positions.values() if p.status == PositionStatus.ACTIVE]
        total_value = sum(p.market_value for p in positions) or 1.0

        # 按行业/板块分组（若 name 字段含行业信息可扩展）
        by_code = [{"code": p.code, "name": p.name, "weight": round(p.market_value / total_value, 4),
                    "unrealized_pnl": round(p.unrealized_pnl, 2),
                    "realized_pnl": round(p.realized_pnl, 2)} for p in positions]
        by_code.sort(key=lambda x: x["weight"], reverse=True)

        return {
            "total_market_value": round(total_value if total_value != 1.0 else 0.0, 2),
            "positions_count": len(positions),
            "concentration": {
                "top1": by_code[0]["weight"] if by_code else 0,
                "top5": round(sum(x["weight"] for x in by_code[:5]), 4),
            },
            "by_code": by_code,
        }

    def rebuild_from_trades(self, trades: List[Dict[str, Any]]):
        """从成交列表重建持仓状态"""
        self._positions.clear()
        self._account.balance = self._initial_capital
        self._account.total_profit = 0.0
        self._logs.clear()
        for t in sorted(trades, key=lambda x: x.get("trade_time") or x.get("timestamp") or ""):
            self.process_trade(
                code=t["code"],
                direction=t["direction"],
                price=float(t["price"]),
                quantity=int(t["quantity"]),
                commission=float(t.get("commission", 0)),
                tax=float(t.get("tax", 0)),
                name=t.get("name", ""),
                order_no=t.get("order_id") or t.get("order_no", ""),
                trade_time=t.get("trade_time") or t.get("timestamp"),
            )

    def get_stats(self) -> Dict[str, Any]:
        return {
            "positions_count": len(self._positions),
            "active_positions": len([p for p in self._positions.values() if p.status == PositionStatus.ACTIVE]),
            "logs_count": len(self._logs),
            "initialized": self._initialized,
            "running": self._running,
        }


# 全局组合引擎实例
portfolio_engine = PortfolioEngine()
