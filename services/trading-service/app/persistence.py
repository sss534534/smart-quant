"""
交易持久化：订单/成交 双写 DB，以及从 DB 重建引擎
"""
from datetime import datetime
from typing import Optional

from common import SessionLocal, get_logger
from common.models.order import (
    Order as OrderRow,
    Trade as TradeRow,
    OrderStatus as OrderStatusRow,
    OrderDirection as OrderDirectionRow,
    OrderType as OrderTypeRow,
)

logger = get_logger("trading-service")


def _order_status(o) -> str:
    return o.status.value if hasattr(o.status, "value") else str(o.status)


def _coerce(value, enum_cls, default=None):
    """把运行时枚举/字符串转成 DB 模型枚举值"""
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    raw = value.value if hasattr(value, "value") else value
    try:
        return enum_cls(raw)
    except ValueError:
        return default


def save_order(order, db_factory=SessionLocal):
    """把运行时订单对象写/更新到 orders 表（order_no 作唯一键）"""
    db = db_factory()
    try:
        row = db.query(OrderRow).filter_by(order_no=order.order_id).first()
        if row is None:
            row = OrderRow(order_no=order.order_id)
            db.add(row)
        row.strategy_id = order.strategy_id
        row.code = order.code
        row.direction = _coerce(order.direction, OrderDirectionRow)
        row.order_type = _coerce(order.order_type, OrderTypeRow, OrderTypeRow.LIMIT)
        row.price = order.price
        row.quantity = int(order.quantity)
        row.filled_quantity = int(order.filled_quantity)
        row.avg_price = order.avg_price
        row.status = _coerce(order.status, OrderStatusRow, OrderStatusRow.PENDING)
        row.submit_time = getattr(order, "submit_time", None) or getattr(order, "create_time", None) or datetime.now()
        row.filled_time = getattr(order, "filled_time", None)
        row.update_time = getattr(order, "update_time", None) or datetime.now()
        row.reject_reason = getattr(order, "reject_reason", None)
        row.extra = getattr(order, "metadata", {})
        db.commit()
        logger.info("Order persisted", order_no=order.order_id, status=_order_status(order))
    finally:
        db.close()


def save_trade(trade, db_factory=SessionLocal):
    """把成交记录写入 trades 表"""
    db = db_factory()
    try:
        row = TradeRow(
            order_no=trade.order_id,
            code=trade.code,
            direction=_coerce(trade.direction, OrderDirectionRow),
            price=trade.price,
            quantity=int(trade.quantity),
            commission=float(trade.commission),
            slip=float(trade.slippage),
            trade_time=datetime.fromisoformat(trade.trade_time.replace("Z", "+00:00"))
            if isinstance(trade.trade_time, str) else trade.trade_time,
            extra={"tax": 0.0},
        )
        db.add(row)
        db.commit()
        logger.info("Trade persisted", order_no=trade.order_id, code=trade.code)
    finally:
        db.close()


def update_order_status(order, status=None, filled_quantity=None, avg_price=None, reject_reason=None,
                        db_factory=SessionLocal):
    """更新订单状态并写回 DB"""
    if status is not None:
        order.status = status
    if filled_quantity is not None:
        order.filled_quantity = int(filled_quantity)
    if avg_price is not None:
        order.avg_price = avg_price
    if reject_reason is not None:
        order.reject_reason = reject_reason
    from datetime import datetime as _dt
    order.update_time = _dt.now()
    if _order_status(order) == "filled":
        order.filled_time = order.filled_time or _dt.now()
    save_order(order, db_factory=db_factory)


def rebuild_engine(engine, db_factory=SessionLocal, initial_capital: float = 100000.0):
    """从 DB 重建引擎：订单、成交、资金、持仓（按成交重放）"""
    from app.engine import Order, Trade, OrderDirection, OrderType, OrderStatus

    db = db_factory()
    try:
        order_rows = db.query(OrderRow).order_by(OrderRow.id).all()
        trade_rows = db.query(TradeRow).order_by(TradeRow.id).all()
    finally:
        db.close()

    # 重建订单字典
    for r in order_rows:
        engine._orders[r.order_no] = Order(
            order_id=r.order_no,
            strategy_id=r.strategy_id,
            code=r.code,
            direction=OrderDirection(r.direction.value) if r.direction else OrderDirection.BUY,
            order_type=OrderType(r.order_type.value) if r.order_type else OrderType.MARKET,
            price=r.price,
            quantity=r.quantity,
            filled_quantity=r.filled_quantity or 0,
            avg_price=r.avg_price or 0.0,
            status=OrderStatus(r.status.value) if r.status else OrderStatus.PENDING,
            create_time=r.submit_time or datetime.now(),
            update_time=r.update_time or datetime.now(),
            submit_time=r.submit_time,
            filled_time=r.filled_time,
            reject_reason=r.reject_reason,
            metadata=r.extra or {},
        )

    # 重放成交恢复资金与持仓
    capital = float(initial_capital)
    positions = {}
    for t in trade_rows:
        amount = t.price * t.quantity
        tax = float((t.extra or {}).get("tax", 0.0))
        direction = OrderDirection(t.direction.value) if t.direction else OrderDirection.BUY
        if direction == OrderDirection.BUY:
            capital -= amount + t.commission
            pos = positions.setdefault(t.code, {"quantity": 0, "avg_price": 0.0, "frozen": 0})
            total = pos["quantity"] + t.quantity
            pos["avg_price"] = (pos["avg_price"] * pos["quantity"] + t.price * t.quantity) / total
            pos["quantity"] = total
        else:
            capital += amount - t.commission - tax
            pos = positions.get(t.code)
            if pos:
                pos["quantity"] -= t.quantity
                if pos["quantity"] <= 0:
                    del positions[t.code]
        engine._trades.append(Trade(
            trade_id=f"T{len(engine._trades)+1:06d}",
            order_id=t.order_no,
            code=t.code,
            direction=direction,
            price=t.price,
            quantity=t.quantity,
            amount=amount,
            commission=t.commission,
            slippage=t.slip or 0.0,
            trade_time=t.trade_time or datetime.now(),
            metadata=t.extra or {},
        ))
    engine._capital = capital
    engine._positions = positions
    logger.info("Trading engine rebuilt from DB", orders=len(engine._orders), trades=len(trade_rows))