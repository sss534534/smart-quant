import sys
from datetime import datetime

sys.path.insert(0, "services/strategy-engine")

from strategies.base import BarData, SignalAction
from strategies.preloaded_factor import (
    MomentumFactorStrategy, LowVolatilityStrategy, MultiFactorStrategy
)


def _flat(code, closes):
    bars = []
    for i, c in enumerate(closes):
        bars.append(BarData(code=code, timestamp=datetime(2026, 1, 1), open=c,
                            high=c * 1.005, low=c * 0.995, close=c, volume=100000 + i * 100))
    return bars


def _run(strategy, bars):
    sigs = []
    for b in bars:
        s = strategy.on_bar(b)
        if s is not None and s.action != SignalAction.HOLD:
            sigs.append(s)
    return sigs


def test_momentum_buys_strong_uptrend():
    closes = [10 * (1.01 ** i) for i in range(80)]
    s = MomentumFactorStrategy("T", {}); s.initialize({})
    sigs = _run(s, _flat("600000", closes))
    assert any(x.action == SignalAction.BUY for x in sigs), f"got {[x.action.value for x in sigs]}"


def test_low_volatility_buys_steady_stock():
    closes = [100 + i for i in range(40)]
    s = LowVolatilityStrategy("T", {}); s.initialize({})
    sigs = _run(s, _flat("600000", closes))
    assert any(x.action == SignalAction.BUY for x in sigs), f"got {[x.action.value for x in sigs]}"


def test_multifactor_scores_over_threshold():
    closes = [10 * (1.008 ** i) for i in range(80)]
    s = MultiFactorStrategy("T", {}); s.initialize({})
    sigs = _run(s, _flat("600000", closes))
    assert any(x.action == SignalAction.BUY for x in sigs), f"got {[x.action.value for x in sigs]}"