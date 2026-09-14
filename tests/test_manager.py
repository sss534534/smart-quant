import asyncio
import sys
from datetime import datetime

import pytest

sys.path.insert(0, "services/strategy-engine")

from app.engine.manager import StrategyManager
from strategies.base import BarData, BaseStrategy, SignalAction, StrategySignal


class OneShotStrategy(BaseStrategy):
    name = "oneshot"
    version = "1.0.0"
    description = "emit buy on first bar"

    def initialize(self, params: dict):
        self._initialized = True

    def on_bar(self, bar: BarData):
        # 用 BarData 校验：若收到 dict 则 bar['code'] 抛 TypeError
        assert isinstance(bar, BarData), f"expected BarData, got {type(bar)}"
        if len(self.get_bar_history(bar.code)) == 1:
            return self.create_signal(bar.code, SignalAction.BUY, bar.close, 100, "test")
        return None


@pytest.mark.asyncio
async def test_run_converts_dict_and_fires_callbacks():
    manager = StrategyManager()
    await manager.initialize()

    events = []
    manager.register_signal_callback(lambda s: events.append(s))

    strat = OneShotStrategy("S1", {"code": "600000"})
    strat.initialize({"code": "600000"})
    manager.add_strategy(strat)
    await manager.start("S1")

    bar = BarData(code="600000", timestamp=datetime.fromisoformat("2026-09-14T10:00:00"),
                  open=10.0, high=10.5, low=9.8, close=10.2, volume=100000)

    # 直接处理模式：一次 process_bars 只喂一次
    for _ in range(3):
        await manager.process_bars(bar.to_dict())

    emitted = [s for s in events if s is not None]
    assert len(emitted) == 1, f"expected exactly 1 signal, got {len(emitted)}"
    sig = emitted[0]
    assert isinstance(sig, StrategySignal)
    assert sig.action == SignalAction.BUY
    assert sig.strategy_id == "S1"