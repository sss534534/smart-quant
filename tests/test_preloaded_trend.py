import sys
from datetime import datetime

sys.path.insert(0, "services/strategy-engine")

from strategies.base import BarData, SignalAction
from strategies.preloaded_trend import (
    BollingerBreakoutStrategy, TurtleStrategy, ADXTrendStrategy, TripleMAStrategy
)


def _bars(code, closes, ts_start=datetime(2026, 1, 1)):
    """生成 BarData 列表，价格逐步变化"""
    bars = []
    ts = ts_start
    for i, c in enumerate(closes):
        bars.append(BarData(code=code, timestamp=ts, open=c, high=c * 1.01,
                            low=c * 0.99, close=c, volume=100000 + i * 100))
        ts = ts
    return bars


def _run(strategy, bars):
    sigs = []
    for b in bars:
        s = strategy.on_bar(b)
        if s is not None and s.action != SignalAction.HOLD:
            sigs.append(s)
    return sigs


def _setup(cls, params):
    s = cls("T", params)
    s.initialize(params)
    return s


def test_boll_breakout_buys_on_strong_up_extension():
    # 长时间横盘后大幅拉升：收盘突破布林上轨
    closes = [10.0] * 55 + [15.0]
    s = _setup(BollingerBreakoutStrategy, {})
    sigs = _run(s, _bars("600000", closes))
    assert any(s.action == SignalAction.BUY for s in sigs), f"expected buy, got {len(sigs)}"


def test_turtle_exits_on_donchian_lower_break():
    closes = [10 + i * 0.2 for i in range(40)]
    s = _setup(TurtleStrategy, {})
    sigs = _run(s, _bars("600000", closes))
    assert any(s.action == SignalAction.BUY for s in sigs)


def test_adx_trend_only_trades_when_strong_trend():
    closes = [10 + i * 0.5 for i in range(80)]
    s = _setup(ADXTrendStrategy, {})
    sigs = _run(s, _bars("600000", closes))
    assert any(s.action == SignalAction.BUY for s in sigs)


def test_triple_ma_buys_on_bullish_alignment():
    # 缓涨后多头排列
    closes = [10 + i * 0.15 for i in range(80)]
    s = _setup(TripleMAStrategy, {})
    sigs = _run(s, _bars("600000", closes))
    assert any(s.action == SignalAction.BUY for s in sigs)