import sys
from datetime import datetime

import pytest

sys.path.insert(0, "services/strategy-engine")

from strategies.base import BarData, BaseStrategy, SignalAction
from strategies.risk_mixin import RiskMixin


class RiskedStrategy(RiskMixin, BaseStrategy):
    name = "risked_test"
    version = "1.0.0"
    description = "test risk mixin"

    def initialize(self, params: dict):
        self.setup_risk(params)
        self._initialized = True
        self._status = self._status.RUNNING

    def on_bar(self, bar: BarData):
        self.update_bar_history(bar)
        if len(self.get_bar_history(bar.code)) == 1:
            return self.create_signal(bar.code, SignalAction.BUY, bar.close, 100, "entry")
        stop = self.risk_check(bar)
        if stop:
            return stop
        return None


def _bar(code, close, ts):
    return BarData(code=code, timestamp=ts, open=close, high=close, low=close,
                   close=close, volume=100000)


def test_trailing_stop_fires_after_profit_then_drawdown():
    s = RiskedStrategy("T1", {})
    s.initialize({"capital": 100000})
    ts = datetime(2026, 1, 1)
    s.on_bar(_bar("600000", 10.0, ts))          # buy entry
    assert s.get_position("600000") == 0        # before on_trade callback, no position yet
    s.on_trade({"code": "600000", "quantity": 100, "direction": "buy"})

    # run 15 rising bars (>= atr_period+1=15 prices needed for ATR warmup)
    for i in range(1, 16):
        s.on_bar(_bar("600000", 10.0 + i, ts))
    # price drops ~36% from peak 25 -> trailing stop (25 * 0.92 = 23.0) must fire
    sig = s.on_bar(_bar("600000", 16.0, ts))
    assert sig is not None
    assert sig.action == SignalAction.SELL
    assert sig.reason.startswith("Trailing")


def test_size_position_caps_at_pct():
    s = RiskedStrategy("T2", {})
    s.initialize({"capital": 100000, "max_position_pct": 0.2})
    qty = s.size_position("600000", 10.0)
    # 0.2 * 100000 / 10 = 2000, floored to lot 100 -> 2000
    assert qty == 2000


def test_risk_disabled_when_flag_off():
    s = RiskedStrategy("T3", {})
    s.initialize({"risk_enabled": False, "trailing_stop_pct": 0.10})
    s.on_bar(_bar("600000", 10.0, datetime(2026, 1, 1)))
    s.on_trade({"code": "600000", "quantity": 100, "direction": "buy"})
    for i in range(1, 11):
        s.on_bar(_bar("600000", 10.0 + i, datetime(2026, 1, 1)))
    sig = s.on_bar(_bar("600000", 16.0, datetime(2026, 1, 1)))
    assert sig is None  # risk disabled -> no stop signal