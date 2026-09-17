import sys
from datetime import datetime

sys.path.insert(0, "services/strategy-engine")

from strategies.base import BarData, SignalAction
from strategies.preloaded_volume import (
    VolumeBreakoutStrategy, VolPriceUpStrategy, OBVDivergenceStrategy
)


def _bars(code, closes, volumes, ts_start=datetime(2026, 1, 1)):
    bars = []
    for i, c in enumerate(closes):
        bars.append(BarData(code=code, timestamp=ts_start, open=c, high=c * 1.01,
                            low=c * 0.99, close=c, volume=volumes[i]))
    return bars


def _run(strategy, bars):
    sigs = []
    for b in bars:
        s = strategy.on_bar(b)
        if s is not None and s.action != SignalAction.HOLD:
            sigs.append(s)
    return sigs


def test_volume_breakout_fires_on_high_volume_gain():
    closes = [10 + i * 0.1 for i in range(30)] + [14.2]
    vols = [100000] * 30 + [500000]  # 5x spike
    s = VolumeBreakoutStrategy("T", {}); s.initialize({})
    sigs = _run(s, _bars("600000", closes, vols))
    assert any(s.action == SignalAction.BUY for s in sigs)


def test_vol_price_up_fires_on_new_high_with_volume():
    closes = [10 + i * 0.2 for i in range(30)]
    vols = [100000 + i * 5000 for i in range(30)]
    s = VolPriceUpStrategy("T", {}); s.initialize({})
    sigs = _run(s, _bars("600000", closes, vols))
    assert any(s.action == SignalAction.BUY for s in sigs)


def test_obv_divergence_fires_sell_on_top_divergence():
    # 价格先创新高，随后放量回调（OBV 大跌），再缩量回升到新高但 OBV 未回到前高 → 顶背离卖
    closes = ([10 + i * 0.3 for i in range(20)]
              + [15.7 - 0.05 * (i + 1) for i in range(10)]
              + [15.2 + 0.3 * (i + 1) for i in range(12)])
    vols = [200000] * 20 + [500000] * 10 + [200000] * 12
    s = OBVDivergenceStrategy("T", {}); s.initialize({})
    s.on_trade({"code": "600000", "quantity": 100, "direction": "buy"})
    sigs = _run(s, _bars("600000", closes, vols))
    assert any(s.action == SignalAction.SELL for s in sigs), f"got {[x.action.value for x in sigs]}"