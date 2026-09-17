import sys
from datetime import datetime

sys.path.insert(0, "services/strategy-engine")

from strategies.base import BarData, SignalAction
from strategies.preloaded_meanrev import (
    BollingerMeanRevStrategy, RSIExtremeStrategy, HammerPatternStrategy,
    EngulfingPatternStrategy, DojiReversalStrategy, GapWindowStrategy
)


def _bar(code, open_, high, low, close, volume=100000, ts=datetime(2026, 1, 1)):
    return BarData(code=code, timestamp=ts, open=open_, high=high, low=low,
                   close=close, volume=volume)


def _flat(code, closes, ts_start=datetime(2026, 1, 1)):
    bars = []
    for i, c in enumerate(closes):
        bars.append(_bar(code, c, c * 1.005, c * 0.995, c))
    return bars


def _run(strategy, bars):
    sigs = []
    for b in bars:
        s = strategy.on_bar(b)
        if s is not None and s.action != SignalAction.HOLD:
            sigs.append(s)
    return sigs


def test_boll_meanrev_buys_when_price_touches_lower_band():
    # 平盘后一根急跌到布林下轨之下 → 买入
    closes = [20] * 45 + [18.0]
    s = BollingerMeanRevStrategy("T", {}); s.initialize({})
    sigs = _run(s, [b for b in _flat("600000", closes)])
    assert any(x.action == SignalAction.BUY for x in sigs)


def test_rsi_extreme_buys_when_rsi_below_20():
    # 连续下跌 → RSI 低到 <20 → 买入
    closes = [20 - i * 0.5 for i in range(30)]
    s = RSIExtremeStrategy("T", {}); s.initialize({})
    sigs = _run(s, _flat("600000", closes))
    assert any(x.action == SignalAction.BUY for x in sigs), f"got {[x.action.value for x in sigs]}"


def test_hammer_buys_in_downtrend_then_hammer():
    # 下跌趋势后一根长下影锤子线 → 买入
    closes = [20 - i * 0.1 for i in range(30)]
    bars = _flat("600000", closes)
    bars.append(_bar("600000", 17.0, 17.25, 15.0, 17.2, 200000))  # 长下影
    s = HammerPatternStrategy("T", {}); s.initialize({})
    sigs = _run(s, bars)
    assert any(x.action == SignalAction.BUY for x in sigs), f"got {len(sigs)}"


def test_engulfing_buys_after_bullish_engulf():
    closes = [20 - i * 0.1 for i in range(30)]
    bars = _flat("600000", closes)
    bars.append(_bar("600000", 17.5, 17.7, 16.9, 17.0, 150000))  # 阴线
    bars.append(_bar("600000", 16.8, 17.8, 16.7, 17.6, 150000))  # 阳包阴
    s = EngulfingPatternStrategy("T", {}); s.initialize({})
    sigs = _run(s, bars)
    assert any(x.action == SignalAction.BUY for x in sigs), f"got {len(sigs)}"


def test_doji_reversal_sells_at_high_point():
    closes = [10 + i * 0.2 for i in range(40)]
    bars = _flat("600000", closes)
    bars.append(_bar("600000", closes[-1], closes[-1] * 1.001, closes[-1] * 0.999, closes[-1], 100))
    s = DojiReversalStrategy("T", {}); s.initialize({})
    s.on_trade({"code": "600000", "quantity": 100, "direction": "buy"})
    sigs = _run(s, bars)
    assert any(x.action == SignalAction.SELL for x in sigs), f"got {[x.action.value for x in sigs]}"


def test_gap_window_buys_on_up_gap_not_filled():
    closes = [10 + i * 0.1 for i in range(30)]
    bars = _flat("600000", closes)
    bars.append(_bar("600000", closes[-1] * 1.03, closes[-1] * 1.04, closes[-1] * 1.02, closes[-1] * 1.035))
    s = GapWindowStrategy("T", {}); s.initialize({})
    sigs = _run(s, bars)
    assert any(x.action == SignalAction.BUY for x in sigs), f"got {len(sigs)}"