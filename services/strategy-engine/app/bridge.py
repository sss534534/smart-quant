"""
信号桥接：策略信号 → 落库 strategy_signals + 桥接 trading-service 下单
"""
import asyncio
import logging
from typing import Callable

import httpx

from common import get_logger, SessionLocal
from common.models.strategy import StrategySignal as StrategySignalRow
from strategies.base import StrategySignal, SignalAction

logger = get_logger("strategy-engine")

TRADING_SERVICE_URL = "http://trading-service:8003"


async def persist_signal(signal: StrategySignal, db_factory=None):
    """把策略信号写入 strategy_signals 表"""
    # 运行时解析，避免定义期绑定导致无法替换/测试
    if db_factory is None:
        db_factory = SessionLocal
    # strategy_id 形如 "S000001"，取数字部分对应 strategies.id
    numeric_id = 0
    if signal.strategy_id.startswith("S"):
        try:
            numeric_id = int(signal.strategy_id[1:])
        except ValueError:
            numeric_id = 0
    row = StrategySignalRow(
        strategy_id=numeric_id,
        code=signal.code,
        action=signal.action.value,
        price=float(signal.price),
        quantity=int(signal.quantity),
        reason=signal.reason,
        strength=float(signal.strength),
    )
    db = db_factory()
    try:
        db.add(row)
        db.commit()
        logger.info("Strategy signal persisted", code=signal.code, action=signal.action.value)
    finally:
        db.close()


async def sync_strategy_position(signal: StrategySignal):
    """把已成交信号回喂给策略实例，保持策略内部持仓一致"""
    from app.engine.manager import strategy_manager
    strategy = strategy_manager.get_strategy(signal.strategy_id)
    if strategy is None:
        return
    try:
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: strategy.on_trade({
                "code": signal.code,
                "direction": signal.action.value,
                "quantity": int(signal.quantity),
            }),
        )
    except Exception as e:
        logger.warning(f"Failed to sync strategy position: {e}")


async def submit_order(signal: StrategySignal):
    """POST trading-service 下单（market 单，价格用信号价格）"""
    payload = {
        "strategy_id": int(signal.strategy_id[1:]) if signal.strategy_id.startswith("S") else None,
        "code": signal.code,
        "direction": signal.action.value,
        "order_type": "market",
        "price": float(signal.price),
        "quantity": int(signal.quantity),
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{TRADING_SERVICE_URL}/trading/order",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        if resp.status_code != 201:
            logger.error(f"Order submission failed: {resp.status_code} {resp.text}")
            return
        logger.info(f"Order submitted: {payload['code']} {payload['direction']} x{payload['quantity']}")
        await sync_strategy_position(signal)


async def handle_signal(signal: StrategySignal):
    """信号处理入口：先落库，再按开关决定是否下单"""
    try:
        await persist_signal(signal)
    except Exception as e:
        logger.error(f"persist_signal failed: {e}")

    from common import settings
    if signal.action in (SignalAction.BUY, SignalAction.SELL) and settings.trading.TRADING_ENABLED:
        await submit_order(signal)


def register_handlers():
    """注册同步回调包装（manager 的回调是同步调用，这里转成异步任务）"""
    from app.engine.manager import strategy_manager
    from common import settings

    def _on_signal(signal: StrategySignal):
        try:
            asyncio.get_event_loop().create_task(handle_signal(signal))
        except RuntimeError:
            asyncio.run(handle_signal(signal))  # 兜底：无事件循环时

    strategy_manager.register_signal_callback(_on_signal)
    logger.info("Signal bridge handlers registered (TRADING_ENABLED=%s)",
                settings.trading.TRADING_ENABLED)