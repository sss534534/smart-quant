import sys

import pytest

sys.path.insert(0, "services/strategy-engine")

from app.engine.manager import StrategyManager
from strategies.base import BarData, BaseStrategy, StrategyStatus


class NoopStrategy(BaseStrategy):
    name = "noop"
    version = "1.0.0"
    description = "record received bars"

    def initialize(self, params: dict):
        self._initialized = True
        self.received_codes = []

    def on_bar(self, bar: BarData):
        self.received_codes.append(bar.code)
        return None


@pytest.mark.asyncio
async def test_feed_bars_feeds_running_strategy(monkeypatch):
    from app import feed

    class FakeClient:
        async def get_quote(self, code, provider="mock"):
            return {"code": code, "price": 12.34, "volume": 8888}

        async def get_stock_list(self, **kwargs):
            return [{"code": "600000", "name": "浦发银行"}]

    manager = StrategyManager()
    await manager.initialize()
    strat = NoopStrategy("S1", {"code": "600000"})
    strat.initialize({"code": "600000"})
    manager.add_strategy(strat)
    manager._strategies["S1"]._status = StrategyStatus.RUNNING
    monkeypatch.setattr(feed, "strategy_manager", manager)
    monkeypatch.setattr(feed, "data_client", FakeClient())

    await feed.feed_market_bars()

    assert strat.received_codes == ["600000"]