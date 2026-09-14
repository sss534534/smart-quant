"""
行情喂料任务：从 data-service 拉取实时 quote，转成 BarData 推给运行中的策略
"""
from typing import Optional
from datetime import datetime

from app.data_client import data_client
from app.engine.manager import strategy_manager
from strategies.base import BarData


async def fetch_bar(code: str) -> Optional[dict]:
    """拉取单只股票 quote 并转为 BarData dict（失败返回 None）"""
    quote = await data_client.get_quote(code, provider="mock")
    if not quote:
        return None
    price = float(quote.get("price", 0))
    if price <= 0:
        return None
    ts = quote.get("timestamp") or datetime.now()
    return BarData(
        code=code,
        timestamp=ts,
        open=price,
        high=price,
        low=price,
        close=price,
        volume=int(quote.get("volume", 0) or 0),
    ).to_dict()


async def feed_market_bars():
    """对所有运行中策略的标的拉取行情并喂给策略管理器"""
    running = strategy_manager.get_running_strategies()
    if not running:
        return
    codes = {s.params.get("code") or "600000" for s in running}
    for code in codes:
        bar = await fetch_bar(code)
        if bar:
            await strategy_manager.process_bars(bar)