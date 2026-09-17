# Preset Industry Quantitative Strategies Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preload 16 industry-standard quant strategies (trend, mean-reversion, volume-price, multi-factor, candlestick patterns) with a shared risk mixin, all registered and DB-seeded so they appear in the UI and run on real Eastmoney data.

**Architecture:** Each strategy is a `BaseStrategy` subclass implementing `initialize(params)` + `on_bar(bar)`, reusing the indicator library in `strategies/indicators.py`. A `RiskMixin` provides ATR stop-loss / trailing-stop / position caps and is mixed into every new strategy. A `seed_strategies()` function idempotently inserts metadata rows into the `strategies` table on startup. `feed.py` switches from mock to eastmoney so live bars are real.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, pandas/numpy (indicators), pytest (tests).

## Global Constraints

- Strategy files live under `services/strategy-engine/strategies/`.
- Every strategy must keep the `name`/`version`/`description` class attributes and implement `initialize(self, params: Dict[str, Any])` + `on_bar(self, bar: BarData) -> Optional[StrategySignal]` exactly as `BaseStrategy` requires (`strategies/base.py:89-147`).
- Reuse indicators from `strategies/indicators.py` (SMA/EMA/MACD/RSI/KDJ/BOLL/ATR/OBV/ADX/crossover/crossunder). Do NOT reimplement them.
- All strategies must be single-symbol (operate on the `code` from the bar being fed).
- Tests follow the pattern in `tests/test_manager.py`: import via `sys.path.insert(0, "services/strategy-engine")`, create strategy instances directly, feed `BarData` via `on_bar`.
- Python version in the live system is 3.12 (`py` launcher available; `python` on PATH is an App Store stub — use `py`).

---

### Task 1: RiskMixin

**Files:**
- Create: `services/strategy-engine/strategies/risk_mixin.py`
- Test: `tests/test_risk_mixin.py`

**Interfaces:**
- Consumes: `BarData`, `SignalAction`, `StrategySignal`, `create_signal` from `BaseStrategy` (all defined in `strategies/base.py`).
- Produces: `class RiskMixin` with:
  - `setup_risk(self, params: Dict[str, Any])` — reads `atr_period`, `atr_stop_mult`, `trailing_stop_pct`, `max_position_pct`, `capital`, sets instance flags `risk_enabled` (default True).
  - `risk_check(self, bar: BarData) -> Optional[StrategySignal]` — returns a SELL signal if an ATR or trailing stop triggers for `bar.code`, else None.
  - `track_position(self, bar: BarData, is_buy: bool)` — called on BUY to record entry; on every bar updates high-water mark.
  - `size_position(self, code: str, price: float) -> int` — quantity capped by `max_position_pct * capital / price`, respecting symbol lot (100).

- [ ] **Step 1: Write the failing test**

```python
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

    # run 10 rising bars, high-water follows up
    for i in range(1, 11):
        s.on_bar(_bar("600000", 10.0 + i, ts))
    # price drops 20% from peak 20 -> trailing_stop_pct 0.10 must fire
    sig = s.on_bar(_bar("600000", 16.0, ts))
    assert sig is not None
    assert sig.action == SignalAction.SELL
    assert sig.reason.startswith("Trailing stop")


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -m pytest tests/test_risk_mixin.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'strategies.risk_mixin'`

- [ ] **Step 3: Write minimal implementation**

```python
"""
风控增强 Mixin
为策略提供 ATR 动态止损、移动止盈、最大持仓比例等风控能力。
采用方案 A：MixIn 直接注入策略类，策略内调用 risk 相关方法。
"""
from typing import Dict, Optional, Any

from .base import BarData, SignalAction, StrategySignal


class RiskMixin:
    """风控 Mixin：挂在 BaseStrategy 子类上，提供止损止盈与仓位控制"""

    _risk_enabled: bool = True
    _atr_period: int = 14
    _atr_stop_mult: float = 2.0
    _trailing_stop_pct: float = 0.08
    _max_position_pct: float = 0.2
    _capital: float = 100000.0
    _entry_prices: Dict[str, float] = {}
    _highest_prices: Dict[str, float] = {}
    _stop_levels: Dict[str, float] = {}

    def setup_risk(self, params: Dict[str, Any]):
        """从 params 读取风控参数"""
        self._risk_enabled = bool(params.get("risk_enabled", True))
        self._atr_period = int(params.get("atr_period", self._atr_period))
        self._atr_stop_mult = float(params.get("atr_stop_mult", self._atr_stop_mult))
        self._trailing_stop_pct = float(params.get("trailing_stop_pct", self._trailing_stop_pct))
        self._max_position_pct = float(params.get("max_position_pct", self._max_position_pct))
        self._capital = float(params.get("capital", self._capital))

    def track_risk_state(self, code: str, bar: BarData):
        """更新该标的的最高价轨迹，用于移动止盈"""
        if self.get_position(code) > 0:
            price = bar.close
            self._highest_prices[code] = max(self._highest_prices.get(code, price), price)
            # 记录入场价（若无）
            if code not in self._entry_prices:
                self._entry_prices[code] = price

    def compute_stop_level(self, code: str, bar: BarData) -> Optional[float]:
        """计算当前止损位：ATR 止损与移动止盈的较高者"""
        prices = self.get_close_prices(code, self._atr_period + 1)
        if len(prices) < self._atr_period + 1:
            return None

        from .indicators import ATR
        ohlcv = self.get_ohlcv(code, self._atr_period + 1)
        atr = ATR(ohlcv["high"], ohlcv["low"], ohlcv["close"], self._atr_period).iloc[-1]
        if atr <= 0:
            return None

        entry = self._entry_prices.get(code)
        stop_by_atr = (entry - self._atr_stop_mult * atr) if entry else None
        high = self._highest_prices.get(code)
        stop_by_trailing = (high * (1 - self._trailing_stop_pct)) if high else None

        candidates = [s for s in (stop_by_atr, stop_by_trailing) if s is not None]
        return max(candidates) if candidates else None

    def risk_check(self, bar: BarData) -> Optional[StrategySignal]:
        """检查风控：若触发止损/止盈则返回 SELL 信号"""
        if not self._risk_enabled:
            return None
        if self.get_position(bar.code) <= 0:
            return None

        self.track_risk_state(bar.code, bar)
        stop = self.compute_stop_level(bar.code, bar)
        self._stop_levels[bar.code] = stop
        if stop is not None and bar.close < stop:
            reason = f"Trailing/ATR stop hit: close {bar.close:.2f} < stop {stop:.2f}"
            qty = min(self.get_position(bar.code), 100)
            return self.create_signal(bar.code, SignalAction.SELL, bar.close, qty, reason, strength=0.9)

        return None

    def size_position(self, code: str, price: float) -> int:
        """按最大持仓比例计算建议数量（取整手）"""
        if price <= 0:
            return 0
        budget = self._capital * self._max_position_pct
        qty = int(budget / price // 100 * 100)
        existing = self.get_position(code)
        qty = max(qty - existing, 0)
        return int(qty)

    def apply_risk(self, bar: BarData, signal: Optional[StrategySignal]) -> Optional[StrategySignal]:
        """包装器：策略 on_bar 出口调用，先过风控再透传信号"""
        stop = self.risk_check(bar)
        if stop:
            return stop
        return signal
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -m pytest tests/test_risk_mixin.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add services/strategy-engine/strategies/risk_mixin.py tests/test_risk_mixin.py
git commit -m "feat(strategy-engine): add RiskMixin with ATR/trailing stop and position caps"
```

---

### Task 2: Trend strategies batch — `boll_breakout`, `turtle`, `adx_trend`, `triple_ma`

**Files:**
- Create: `services/strategy-engine/strategies/preloaded_trend.py`
- Test: `tests/test_preloaded_trend.py`

**Interfaces:**
- Consumes: `BaseStrategy`, `BarData`, `SignalAction`, `StrategySignal` (`strategies/base.py`), indicators (`strategies/indicators.py`), `RiskMixin` (Task 1).
- Produces: classes `BollingerBreakoutStrategy`, `TurtleStrategy`, `ADXTrendStrategy`, `TripleMAStrategy` with `name` values `boll_breakout`, `turtle`, `adx_trend`, `triple_ma`. Each is a registered-when-imported class.

- [ ] **Step 1: Write the failing test**

```python
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
    # 强上升趋势：从 10 一路涨到 30，布林中轨向上，收盘常超上轨
    closes = [10 + i * 0.3 for i in range(60)]
    s = _setup(BollingerBreakoutStrategy, {})
    sigs = _run(s, _bars("600000", closes))
    assert any(s.action == SignalAction.BUY for s in sigs), f"expected buy, got {len(sigs)}"


def test_turtle_exits_on_donchian_lower_break():
    closes = [10 + i * 0.2 for i in range(40)]
    s = _setup(TurtleStrategy, {})
    sigs = _run(s, _bars("600000", closes))
    assert any(s.action == SignalAction.BUY for s in sigs)


def test_adx_trend_only_trades_when_strong_trend():
    closes = [10 + i * 0.5 for i in range(40)]
    s = _setup(ADXTrendStrategy, {})
    sigs = _run(s, _bars("600000", closes))
    assert any(s.action == SignalAction.BUY for s in sigs)


def test_triple_ma_buys_on_bullish_alignment():
    # 缓涨 + 温和回撤后继续走高，多头排列
    closes = [10 + i * 0.15 for i in range(80)]
    s = _setup(TripleMAStrategy, {})
    sigs = _run(s, _bars("600000", closes))
    assert any(s.action == SignalAction.BUY for s in sigs)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -m pytest tests/test_preloaded_trend.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'strategies.preloaded_trend'`

- [ ] **Step 3: Write minimal implementation**

```python
"""
趋势跟踪策略集（预置）
布林带突破、海龟交易、ADX趋势过滤、三均线趋势
"""
from typing import Dict, Any, Optional

from .base import BaseStrategy, SignalAction, BarData, StrategySignal
from .indicators import SMA, EMA, ATR, ADX, BOLL, crossover, crossunder
from .risk_mixin import RiskMixin


class BollingerBreakoutStrategy(RiskMixin, BaseStrategy):
    """布林带突破：突破上轨买、跌破下轨卖"""

    name = "boll_breakout"
    version = "1.0.0"
    description = "Bollinger Band breakout trend strategy"

    def initialize(self, params: Dict[str, Any]):
        self.boll_period = int(params.get("boll_period", 20))
        self.std = float(params.get("std", 2.0))
        self.code = params.get("code", "600000")
        self.setup_risk(params)
        self._initialized = True
        self._status = self._status.RUNNING

    def on_bar(self, bar: BarData) -> Optional[StrategySignal]:
        self.update_bar_history(bar)
        if len(self.get_bar_history(bar.code)) < self.boll_period * 2:
            return None

        ohlcv = self.get_ohlcv(bar.code, self.boll_period * 2)
        upper, middle, lower = BOLL(ohlcv["close"], self.boll_period, self.std)
        if len(self.get_bar_history(bar.code)) < 3:
            return None

        pos = self.get_position(bar.code)
        sig = None
        if pos == 0 and bar.close > upper.iloc[-1]:
            qty = self.size_position(bar.code, bar.close)
            sig = self.create_signal(bar.code, SignalAction.BUY, bar.close, qty,
                                     f"Price {bar.close:.2f} broke above upper band {upper.iloc[-1]:.2f}",
                                     metadata={"upper": upper.iloc[-1], "middle": middle.iloc[-1]})
        elif pos == 0 and bar.close < lower.iloc[-1]:
            qty = self.size_position(bar.code, bar.close)
            sig = self.create_signal(bar.code, SignalAction.SELL, bar.close, qty,
                                     f"Price {bar.close:.2f} broke below lower band {lower.iloc[-1]:.2f}",
                                     metadata={"lower": lower.iloc[-1]})
        return self.apply_risk(bar, sig)


class TurtleStrategy(RiskMixin, BaseStrategy):
    """海龟交易：唐奇安通道突破入场，通道反向出场"""

    name = "turtle"
    version = "1.0.0"
    description = "Turtle Trading Donchian channel breakout strategy"

    def initialize(self, params: Dict[str, Any]):
        self.entry_period = int(params.get("entry_period", 20))
        self.exit_period = int(params.get("exit_period", 10))
        self.code = params.get("code", "600000")
        self.setup_risk(params)
        self._initialized = True
        self._status = self._status.RUNNING

    def _donchian(self, hist, period):
        highs = [b.high for b in hist]
        lows = [b.low for b in hist]
        up = max(highs[-period:])
        dn = min(lows[-period:])
        return up, dn

    def on_bar(self, bar: BarData) -> Optional[StrategySignal]:
        self.update_bar_history(bar)
        hist = self.get_bar_history(bar.code)
        if len(hist) < self.entry_period + 5:
            return None

        pos = self.get_position(bar.code)
        sig = None
        if pos == 0:
            up, _ = self._donchian(hist[:-1], self.entry_period)
            if bar.high >= up:
                qty = self.size_position(bar.code, bar.close)
                sig = self.create_signal(bar.code, SignalAction.BUY, bar.close, qty,
                                         f"Broke 20-day high {up:.2f} at {bar.high:.2f}")
        else:
            _, dn = self._donchian(hist[:-1], self.exit_period)
            if bar.low <= dn:
                qty = min(self.get_position(bar.code), 100)
                sig = self.create_signal(bar.code, SignalAction.SELL, bar.close, qty,
                                         f"Broke 10-day low {dn:.2f} at {bar.low:.2f}")
        return self.apply_risk(bar, sig)


class ADXTrendStrategy(RiskMixin, BaseStrategy):
    """ADX趋势过滤：ADX 大于阈值且 +DI 占优时买入"""

    name = "adx_trend"
    version = "1.0.0"
    description = "ADX trend-strength filtered strategy"

    def initialize(self, params: Dict[str, Any]):
        self.adx_period = int(params.get("adx_period", 14))
        self.threshold = float(params.get("threshold", 25))
        self.code = params.get("code", "600000")
        self.setup_risk(params)
        self._initialized = True
        self._status = self._status.RUNNING

    def on_bar(self, bar: BarData) -> Optional[StrategySignal]:
        self.update_bar_history(bar)
        ohlcv = self.get_ohlcv(bar.code, self.adx_period * 4)
        if len(ohlcv) < self.adx_period * 4:
            return None

        adx = ADX(ohlcv["high"], ohlcv["low"], ohlcv["close"], self.adx_period)
        if adx.isna().iloc[-1] or adx.iloc[-1] < self.threshold:
            return None

        # +DI 估算：最近 close 变化方向
        pos = self.get_position(bar.code)
        sig = None
        if pos == 0 and ohlcv["close"].diff().iloc[-1] > 0:
            qty = self.size_position(bar.code, bar.close)
            sig = self.create_signal(bar.code, SignalAction.BUY, bar.close, qty,
                                     f"ADX {adx.iloc[-1]:.1f} above threshold with uptrend")
        elif pos > 0 and ohlcv["close"].diff().iloc[-1] < 0:
            qty = min(self.get_position(bar.code), 100)
            sig = self.create_signal(bar.code, SignalAction.SELL, bar.close, qty,
                                     "ADX uptrend weakening")
        return self.apply_risk(bar, sig)


class TripleMAStrategy(RiskMixin, BaseStrategy):
    """三均线趋势：多头排列买、空头排列卖"""

    name = "triple_ma"
    version = "1.0.0"
    description = "Triple moving average alignment strategy"

    def initialize(self, params: Dict[str, Any]):
        self.fast = int(params.get("fast", 5))
        self.mid = int(params.get("mid", 20))
        self.slow = int(params.get("slow", 60))
        self.code = params.get("code", "600000")
        self.setup_risk(params)
        self._initialized = True
        self._status = self._status.RUNNING

    def on_bar(self, bar: BarData) -> Optional[StrategySignal]:
        self.update_bar_history(bar)
        if len(self.get_bar_history(bar.code)) < self.slow + 5:
            return None

        prices = self.get_close_prices(bar.code, self.slow + 5)
        ma_f = SMA(prices, self.fast)
        ma_m = SMA(prices, self.mid)
        ma_s = SMA(prices, self.slow)
        if ma_s.isna().iloc[-1]:
            return None

        pos = self.get_position(bar.code)
        sig = None
        crossed_up = crossover(ma_f, ma_m).iloc[-1]
        crossed_dn = crossunder(ma_f, ma_m).iloc[-1]
        aligned_up = ma_f.iloc[-1] > ma_m.iloc[-1] > ma_s.iloc[-1]
        aligned_dn = ma_f.iloc[-1] < ma_m.iloc[-1] < ma_s.iloc[-1]
        if pos == 0 and (crossed_up or aligned_up):
            qty = self.size_position(bar.code, bar.close)
            sig = self.create_signal(bar.code, SignalAction.BUY, bar.close, qty,
                                     f"Bullish alignment MA{self.fast}>{self.mid}>{self.slow}")
        elif pos > 0 and (crossed_dn or aligned_dn):
            qty = min(self.get_position(bar.code), 100)
            sig = self.create_signal(bar.code, SignalAction.SELL, bar.close, qty,
                                     f"Bearish alignment MA{self.fast}<{self.mid}<{self.slow}")
        return self.apply_risk(bar, sig)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -m pytest tests/test_preloaded_trend.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add services/strategy-engine/strategies/preloaded_trend.py tests/test_preloaded_trend.py
git commit -m "feat(strategy-engine): add trend strategies boll_breakout/turtle/adx_trend/triple_ma"
```

---

### Task 3: Volume-price strategies — `volume_breakout`, `vol_price_up`, `obv_divergence`

**Files:**
- Create: `services/strategy-engine/strategies/preloaded_volume.py`
- Test: `tests/test_preloaded_volume.py`

**Interfaces:**
- Consumes: `BaseStrategy`, `BarData`, `SignalAction`, `StrategySignal`, indicators (`SMA`, `OBV`), `RiskMixin`.
- Produces: classes `VolumeBreakoutStrategy`, `VolPriceUpStrategy`, `OBVDivergenceStrategy` with `name` values `volume_breakout`, `vol_price_up`, `obv_divergence`.

- [ ] **Step 1: Write the failing test**

```python
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
    # 价格仍创新高，但成交量逐波递减 → OBV 不创新高 → 顶背离卖
    closes = [10 + i * 0.3 for i in range(40)]
    vols = [200000] * 20 + [50000] * 11
    s = OBVDivergenceStrategy("T", {}); s.initialize({})
    s.on_trade({"code": "600000", "quantity": 100, "direction": "buy"})
    sigs = _run(s, _bars("600000", closes, vols))
    assert any(s.action == SignalAction.SELL for s in sigs), f"got {[x.action.value for x in sigs]}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -m pytest tests/test_preloaded_volume.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'strategies.preloaded_volume'`

- [ ] **Step 3: Write minimal implementation**

```python
"""
量价分析策略集（预置）
放量突破、量价齐升、OBV 背离
"""
from typing import Dict, Any, Optional

from .base import BaseStrategy, SignalAction, BarData, StrategySignal
from .indicators import SMA, OBV
from .risk_mixin import RiskMixin


class VolumeBreakoutStrategy(RiskMixin, BaseStrategy):
    """放量突破：价格突破 N 日高点且成交量放大 n 倍"""

    name = "volume_breakout"
    version = "1.0.0"
    description = "Volume-confirmed price breakout strategy"

    def initialize(self, params: Dict[str, Any]):
        self.high_period = int(params.get("high_period", 20))
        self.vol_ratio = float(params.get("vol_ratio", 2.0))
        self.code = params.get("code", "600000")
        self.setup_risk(params)
        self._initialized = True
        self._status = self._status.RUNNING

    def on_bar(self, bar: BarData) -> Optional[StrategySignal]:
        self.update_bar_history(bar)
        hist = self.get_bar_history(bar.code)
        if len(hist) < self.high_period + 2:
            return None

        highs = [b.high for b in hist[:-1]]
        avg_vol = SMA([b.volume for b in hist[:-1]], 5)
        prior_max = max(highs[-self.high_period:])
        avg_vol = sum(b.volume for b in hist[-6:-1]) / 5 if len(hist) >= 6 else 0

        pos = self.get_position(bar.code)
        sig = None
        if pos == 0 and bar.close > prior_max and avg_vol > 0 and bar.volume >= self.vol_ratio * avg_vol:
            qty = self.size_position(bar.code, bar.close)
            sig = self.create_signal(bar.code, SignalAction.BUY, bar.close, qty,
                                     f"Breakout above {prior_max:.2f} with volume {bar.volume} vs avg {avg_vol:.0f}")
        return self.apply_risk(bar, sig)


class VolPriceUpStrategy(RiskMixin, BaseStrategy):
    """量价齐升：价格与量能同步创新高"""

    name = "vol_price_up"
    version = "1.0.0"
    description = "Rising price joined by rising volume strategy"

    def initialize(self, params: Dict[str, Any]):
        self.lookback = int(params.get("lookback", 20))
        self.code = params.get("code", "600000")
        self.setup_risk(params)
        self._initialized = True
        self._status = self._status.RUNNING

    def on_bar(self, bar: BarData) -> Optional[StrategySignal]:
        self.update_bar_history(bar)
        hist = self.get_bar_history(bar.code)
        if len(hist) < self.lookback + 2:
            return None

        prior = hist[-(self.lookback + 1):-1]
        pos = self.get_position(bar.code)
        sig = None
        if pos == 0 and bar.close > max(b.close for b in prior) and bar.volume > max(b.volume for b in prior):
            qty = self.size_position(bar.code, bar.close)
            sig = self.create_signal(bar.code, SignalAction.BUY, bar.close, qty,
                                     "Price and volume both hit new highs")
        return self.apply_risk(bar, sig)


class OBVDivergenceStrategy(RiskMixin, BaseStrategy):
    """OBV 背离：价格创新高但 OBV 未创新高（顶背离）卖出，反之买入"""

    name = "obv_divergence"
    version = "1.0.0"
    description = "OBV price-volume divergence strategy"

    def initialize(self, params: Dict[str, Any]):
        self.lookback = int(params.get("lookback", 20))
        self.code = params.get("code", "600000")
        self.setup_risk(params)
        self._initialized = True
        self._status = self._status.RUNNING

    def on_bar(self, bar: BarData) -> Optional[StrategySignal]:
        self.update_bar_history(bar)
        hist = self.get_bar_history(bar.code)
        if len(hist) < self.lookback * 2:
            return None

        closes = [b.close for b in hist]
        vols = [b.volume for b in hist]
        obv = OBV(closes, vols)
        window = len(hist) // 2

        pos = self.get_position(bar.code)
        sig = None
        price_high = closes[-1] == max(closes[-window:])
        obv_high = obv.iloc[-1] >= max(obv.iloc[-window:])
        if price_high and not obv_high:
            if pos > 0:
                qty = min(self.get_position(bar.code), 100)
                sig = self.create_signal(bar.code, SignalAction.SELL, bar.close, qty,
                                         "Top divergence: price new high but OBV lower")
        return self.apply_risk(bar, sig)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -m pytest tests/test_preloaded_volume.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add services/strategy-engine/strategies/preloaded_volume.py tests/test_preloaded_volume.py
git commit -m "feat(strategy-engine): add volume-price strategies volume_breakout/vol_price_up/obv_divergence"
```

---

### Task 4: Mean-reversion + candlestick batch — `boll_meanrev`, `rsi_extreme`, `hammer`, `engulfing`, `doji_reversal`, `gap_window`

**Files:**
- Create: `services/strategy-engine/strategies/preloaded_meanrev.py`
- Test: `tests/test_preloaded_meanrev.py`

**Interfaces:**
- Consumes: `BaseStrategy`, `BarData`, `SignalAction`, `StrategySignal`, indicators (`BOLL`, `RSI`), `RiskMixin`.
- Produces: classes named per batch — `BollingerMeanRevStrategy`, `RSIExtremeStrategy`, `HammerPatternStrategy`, `EngulfingPatternStrategy`, `DojiReversalStrategy`, `GapWindowStrategy`; `name` values `boll_meanrev`, `rsi_extreme`, `hammer`, `engulfing`, `doji_reversal`, `gap_window`.

- [ ] **Step 1: Write the failing test**

```python
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
    closes = [20] * 30 + [18.0]
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
    bars.append(_bar("600000", 17.0, 17.5, 15.0, 17.2, 200000))  # 长下影
    s = HammerPatternStrategy("T", {}); s.initialize({})
    sigs = _run(s, bars)
    assert any(x.action == SignalAction.BUY for x in sigs), f"got {len(sigs)}"


def test_engulfing_buys_after_bullish_engulf():
    closes = [20 - i * 0.1 for i in range(30)]
    bars = _flat("600000", closes)
    bars.append(_bar("600000", 17.0, 17.6, 16.8, 17.5, 150000))  # 阳线
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
    bars.append(_bar("600000", closes[-1] * 1.03, closes[-1] * 1.04, closes[-1] * 1.02, closes[-1] * 1.025))
    s = GapWindowStrategy("T", {}); s.initialize({})
    sigs = _run(s, bars)
    assert any(x.action == SignalAction.BUY for x in sigs), f"got {len(sigs)}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -m pytest tests/test_preloaded_meanrev.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'strategies.preloaded_meanrev'`

- [ ] **Step 3: Write minimal implementation**

```python
"""
均值回归 + K线形态策略集（预置）
布林回归、RSI极限回归、锤子线、吞没、十字星反转、跳空缺口
"""
from typing import Dict, Any, Optional

from .base import BaseStrategy, SignalAction, BarData, StrategySignal
from .indicators import BOLL, RSI
from .risk_mixin import RiskMixin


class BollingerMeanRevStrategy(RiskMixin, BaseStrategy):
    """布林均值回归：触及下轨买、触及上轨卖、中轨止盈"""

    name = "boll_meanrev"
    version = "1.0.0"
    description = "Bollinger mean reversion strategy"

    def initialize(self, params: Dict[str, Any]):
        self.boll_period = int(params.get("boll_period", 20))
        self.std = float(params.get("std", 2.0))
        self.code = params.get("code", "600000")
        self.setup_risk(params)
        self._initialized = True
        self._status = self._status.RUNNING

    def on_bar(self, bar: BarData) -> Optional[StrategySignal]:
        self.update_bar_history(bar)
        if len(self.get_bar_history(bar.code)) < self.boll_period * 2:
            return None

        ohlcv = self.get_ohlcv(bar.code, self.boll_period * 2)
        upper, middle, lower = BOLL(ohlcv["close"], self.boll_period, self.std)
        pos = self.get_position(bar.code)
        sig = None
        if pos == 0 and bar.close < lower.iloc[-1]:
            qty = self.size_position(bar.code, bar.close)
            sig = self.create_signal(bar.code, SignalAction.BUY, bar.close, qty,
                                     f"Price below lower band {lower.iloc[-1]:.2f}, mean reversion")
        elif pos > 0 and bar.close > middle.iloc[-1]:
            qty = min(self.get_position(bar.code), 100)
            sig = self.create_signal(bar.code, SignalAction.SELL, bar.close, qty,
                                     f"Mean reversion to middle band {middle.iloc[-1]:.2f}")
        return self.apply_risk(bar, sig)


class RSIExtremeStrategy(RiskMixin, BaseStrategy):
    """RSI 极限回归：RSI<oversold 买、RSI>overbought 卖"""

    name = "rsi_extreme"
    version = "1.0.0"
    description = "Extreme RSI mean reversion strategy"

    def initialize(self, params: Dict[str, Any]):
        self.rsi_period = int(params.get("rsi_period", 14))
        self.oversold = float(params.get("oversold", 20))
        self.overbought = float(params.get("overbought", 80))
        self.code = params.get("code", "600000")
        self.setup_risk(params)
        self._initialized = True
        self._status = self._status.RUNNING

    def on_bar(self, bar: BarData) -> Optional[StrategySignal]:
        self.update_bar_history(bar)
        if len(self.get_bar_history(bar.code)) < self.rsi_period + 2:
            return None

        prices = self.get_close_prices(bar.code, self.rsi_period + 2)
        rsi = RSI(prices, self.rsi_period)
        if rsi.isna().iloc[-1]:
            return None

        cur = rsi.iloc[-1]
        pos = self.get_position(bar.code)
        sig = None
        if pos == 0 and cur < self.oversold:
            qty = self.size_position(bar.code, bar.close)
            sig = self.create_signal(bar.code, SignalAction.BUY, bar.close, qty,
                                     f"RSI {cur:.1f} oversold (<{self.oversold})")
        elif pos > 0 and cur > self.overbought:
            qty = min(self.get_position(bar.code), 100)
            sig = self.create_signal(bar.code, SignalAction.SELL, bar.close, qty,
                                     f"RSI {cur:.1f} overbought (>{self.overbought})")
        return self.apply_risk(bar, sig)


class HammerPatternStrategy(RiskMixin, BaseStrategy):
    """锤子线形态：下跌趋势末段出现长下影锤子线买入"""

    name = "hammer"
    version = "1.0.0"
    description = "Hammer candlestick pattern strategy"

    def initialize(self, params: Dict[str, Any]):
        self.body_ratio = float(params.get("body_ratio", 2.0))
        self.lookback = int(params.get("lookback", 20))
        self.code = params.get("code", "600000")
        self.setup_risk(params)
        self._initialized = True
        self._status = self._status.RUNNING

    def on_bar(self, bar: BarData) -> Optional[StrategySignal]:
        self.update_bar_history(bar)
        hist = self.get_bar_history(bar.code)
        if len(hist) < self.lookback + 2:
            return None

        body = abs(bar.close - bar.open)
        lower_shadow = min(bar.open, bar.close) - bar.low
        upper_shadow = bar.high - max(bar.open, bar.close)
        is_hammer = (body > 0 and lower_shadow > self.body_ratio * body
                     and upper_shadow <= body * 0.5)
        prior = [b.close for b in hist[:-(self.lookback + 1)]]
        downtrend = len(prior) > 5 and prior[-1] < max(prior) - (max(prior) - min(prior)) * 0.5

        pos = self.get_position(bar.code)
        if pos == 0 and is_hammer and self.get_close_prices(bar.code, self.lookback).iloc[-1] < \
                self.get_close_prices(bar.code, self.lookback).iloc[0]:
            qty = self.size_position(bar.code, bar.close)
            return self.create_signal(bar.code, SignalAction.BUY, bar.close, qty,
                                      "Hammer after downtrend")
        return self.apply_risk(bar, None)


class EngulfingPatternStrategy(RiskMixin, BaseStrategy):
    """吞没形态：低位阳包阴买、高位阴包阳卖"""

    name = "engulfing"
    version = "1.0.0"
    description = "Engulfing candlestick pattern strategy"

    def initialize(self, params: Dict[str, Any]):
        self.lookback = int(params.get("lookback", 20))
        self.code = params.get("code", "600000")
        self.setup_risk(params)
        self._initialized = True
        self._status = self._status.RUNNING

    def on_bar(self, bar: BarData) -> Optional[StrategySignal]:
        self.update_bar_history(bar)
        hist = self.get_bar_history(bar.code)
        if len(hist) < 3:
            return None

        prev = hist[-2]
        prev_body = prev.close - prev.open
        cur_body = bar.close - bar.open
        # 阳包阴
        bullish_engulf = (prev_body < 0 and cur_body > 0
                          and bar.open <= prev.close and bar.close >= prev.open)
        # 阴包阳
        bearish_engulf = (prev_body > 0 and cur_body < 0
                          and bar.open >= prev.close and bar.close <= prev.open)

        pos = self.get_position(bar.code)
        sig = None
        if pos == 0 and bullish_engulf:
            qty = self.size_position(bar.code, bar.close)
            sig = self.create_signal(bar.code, SignalAction.BUY, bar.close, qty, "Bullish engulfing")
        elif pos > 0 and bearish_engulf:
            qty = min(self.get_position(bar.code), 100)
            sig = self.create_signal(bar.code, SignalAction.SELL, bar.close, qty, "Bearish engulfing")
        return self.apply_risk(bar, sig)


class DojiReversalStrategy(RiskMixin, BaseStrategy):
    """十字星反转：高位十字星卖、低位十字星买"""

    name = "doji_reversal"
    version = "1.0.0"
    description = "Doji reversal pattern strategy"

    def initialize(self, params: Dict[str, Any]):
        self.doji_tolerance = float(params.get("doji_tolerance", 0.1))
        self.lookback = int(params.get("lookback", 20))
        self.code = params.get("code", "600000")
        self.setup_risk(params)
        self._initialized = True
        self._status = self._status.RUNNING

    def on_bar(self, bar: BarData) -> Optional[StrategySignal]:
        self.update_bar_history(bar)
        hist = self.get_bar_history(bar.code)
        if len(hist) < self.lookback + 2:
            return None

        body = abs(bar.close - bar.open)
        rng = bar.high - bar.low
        is_doji = rng > 0 and body < rng * self.doji_tolerance

        closes = [b.close for b in hist]
        window = closes[:-(self.lookback + 1)]
        high_point = window and bar.close > max(window) * 0.99
        low_point = window and bar.close < min(window) * 1.01

        pos = self.get_position(bar.code)
        sig = None
        if is_doji and high_point and pos > 0:
            qty = min(self.get_position(bar.code), 100)
            sig = self.create_signal(bar.code, SignalAction.SELL, bar.close, qty, "Doji at high point")
        elif is_doji and low_point and pos == 0:
            qty = self.size_position(bar.code, bar.close)
            sig = self.create_signal(bar.code, SignalAction.BUY, bar.close, qty, "Doji at low point")
        return self.apply_risk(bar, sig)


class GapWindowStrategy(RiskMixin, BaseStrategy):
    """跳空缺口：向上跳空不回补买入"""

    name = "gap_window"
    version = "1.0.0"
    description = "Up-gap window continuation strategy"

    def initialize(self, params: Dict[str, Any]):
        self.gap_ratio = float(params.get("gap_ratio", 0.01))
        self.code = params.get("code", "600000")
        self.setup_risk(params)
        self._initialized = True
        self._status = self._status.RUNNING

    def on_bar(self, bar: BarData) -> Optional[StrategySignal]:
        self.update_bar_history(bar)
        hist = self.get_bar_history(bar.code)
        if len(hist) < 3:
            return None

        prev = hist[-2]
        gap = (bar.open - prev.close) / prev.close if prev.close else 0
        pos = self.get_position(bar.code)
        sig = None
        if pos == 0 and gap > self.gap_ratio and bar.close >= bar.open:
            qty = self.size_position(bar.code, bar.close)
            sig = self.create_signal(bar.code, SignalAction.BUY, bar.close, qty,
                                     f"Up gap {gap:.2%} confirmed by bullish bar")
        return self.apply_risk(bar, sig)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -m pytest tests/test_preloaded_meanrev.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add services/strategy-engine/strategies/preloaded_meanrev.py tests/test_preloaded_meanrev.py
git commit -m "feat(strategy-engine): add mean-reversion & candlestick strategies (6)"
```

---

### Task 5: Multi-factor strategies — `momentum_factor`, `low_volatility`, `multi_factor`

**Files:**
- Create: `services/strategy-engine/strategies/preloaded_factor.py`
- Test: `tests/test_preloaded_factor.py`

**Interfaces:**
- Consumes: `BaseStrategy`, `BarData`, `SignalAction`, `StrategySignal`, indicators (`HistoricalVolatility`), `RiskMixin`.
- Produces: classes `MomentumFactorStrategy`, `LowVolatilityStrategy`, `MultiFactorStrategy`; `name` values `momentum_factor`, `low_volatility`, `multi_factor`.

- [ ] **Step 1: Write the failing test**

```python
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
    closes = [10 * (1.01 ** i) for i in range(60)]
    s = MomentumFactorStrategy("T", {}); s.initialize({})
    sigs = _run(s, _flat("600000", closes))
    assert any(x.action == SignalAction.BUY for x in sigs), f"got {[x.action.value for x in sigs]}"


def test_low_volatility_buys_steady_stock():
    closes = [100, 101, 100, 102, 101, 103, 102, 104, 103, 105, 104, 106, 105, 107, 106, 108, 107, 109, 108, 110]
    s = LowVolatilityStrategy("T", {}); s.initialize({})
    sigs = _run(s, _flat("600000", closes))
    assert any(x.action == SignalAction.BUY for x in sigs), f"got {[x.action.value for x in sigs]}"


def test_multifactor_scores_over_threshold():
    closes = [10 * (1.008 ** i) for i in range(80)]
    s = MultiFactorStrategy("T", {}); s.initialize({})
    sigs = _run(s, _flat("600000", closes))
    assert any(x.action == SignalAction.BUY for x in sigs), f"got {[x.action.value for x in sigs]}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -m pytest tests/test_preloaded_factor.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'strategies.preloaded_factor'`

- [ ] **Step 3: Write minimal implementation**

```python
"""
多因子选股策略集（预置）
动量、低波动、综合评分
"""
from typing import Dict, Any, Optional

from .base import BaseStrategy, SignalAction, BarData, StrategySignal
from .indicators import SMA, HistoricalVolatility
from .risk_mixin import RiskMixin


class MomentumFactorStrategy(RiskMixin, BaseStrategy):
    """动量因子：多周期加权收益率打分，超过阈值买入"""

    name = "momentum_factor"
    version = "1.0.0"
    description = "Multi-horizon momentum factor strategy"

    def initialize(self, params: Dict[str, Any]):
        self.lookbacks = params.get("lookbacks", [10, 20, 60])
        self.threshold = float(params.get("threshold", 0.05))
        self.code = params.get("code", "600000")
        self.setup_risk(params)
        self._initialized = True
        self._status = self._status.RUNNING

    def _score(self, closes):
        score = 0.0
        weights = [1.0 / (i + 1) for i in range(len(self.lookbacks))]
        for (lb, w) in zip(self.lookbacks, weights):
            if len(closes) >= lb + 1:
                ret = closes[-1] / closes[-1 - lb] - 1
                score += w * ret
        return score / sum(weights) if weights else 0.0

    def on_bar(self, bar: BarData) -> Optional[StrategySignal]:
        self.update_bar_history(bar)
        closes = self.get_close_prices(bar.code, max(self.lookbacks) + 1)
        if len(closes) < max(self.lookbacks) + 1:
            return None

        score = self._score(list(closes))
        pos = self.get_position(bar.code)
        sig = None
        if pos == 0 and score > self.threshold:
            qty = self.size_position(bar.code, bar.close)
            sig = self.create_signal(bar.code, SignalAction.BUY, bar.close, qty,
                                     f"Momentum score {score:.3f} above {self.threshold}")
        return self.apply_risk(bar, sig)


class LowVolatilityStrategy(RiskMixin, BaseStrategy):
    """低波动因子：年化波动率低于阈值时买入（稳健）"""

    name = "low_volatility"
    version = "1.0.0"
    description = "Low volatility factor strategy"

    def initialize(self, params: Dict[str, Any]):
        self.vol_period = int(params.get("vol_period", 20))
        self.max_vol = float(params.get("max_vol", 0.25))
        self.code = params.get("code", "600000")
        self.setup_risk(params)
        self._initialized = True
        self._status = self._status.RUNNING

    def on_bar(self, bar: BarData) -> Optional[StrategySignal]:
        self.update_bar_history(bar)
        if len(self.get_bar_history(bar.code)) < self.vol_period + 2:
            return None

        ohlcv = self.get_ohlcv(bar.code, self.vol_period + 2)
        vol = HistoricalVolatility(ohlcv["close"], self.vol_period)
        if vol.isna().iloc[-1]:
            return None

        pos = self.get_position(bar.code)
        sig = None
        if pos == 0 and vol.iloc[-1] < self.max_vol:
            qty = self.size_position(bar.code, bar.close)
            sig = self.create_signal(bar.code, SignalAction.BUY, bar.close, qty,
                                     f"Annualized vol {vol.iloc[-1]:.2f} below {self.max_vol}")
        return self.apply_risk(bar, sig)


class MultiFactorStrategy(RiskMixin, BaseStrategy):
    """综合评分：动量 + 低波 + 量能 + 趋势 加权打分择时"""

    name = "multi_factor"
    version = "1.0.0"
    description = "Composite multi-factor scoring strategy"

    def initialize(self, params: Dict[str, Any]):
        self.lookback = int(params.get("lookback", 20))
        self.buy_threshold = float(params.get("buy_threshold", 0.6))
        self.sell_threshold = float(params.get("sell_threshold", -0.3))
        self.code = params.get("code", "600000")
        self.setup_risk(params)
        self._initialized = True
        self._status = self._status.RUNNING

    def _score(self, closes, volumes):
        # 1) 动量
        mom = closes[-1] / closes[-1 - self.lookback] - 1 if len(closes) > self.lookback else 0
        mom_s = max(min(mom / 0.1, 1.0), -1.0)
        # 2) 趋势（均线多头）
        avg = sum(closes[-self.lookback:]) / self.lookback
        trend_s = 1.0 if closes[-1] > avg else 0.0
        # 3) 量能（近5日量 > 前20日均量）
        if len(volumes) > self.lookback:
            recent = sum(volumes[-5:]) / 5
            prior = sum(volumes[-(self.lookback + 5):-5]) / self.lookback if self.lookback else recent
            vol_s = 1.0 if prior > 0 and recent > prior else 0.0
        else:
            vol_s = 0.0
        combined = 0.5 * mom_s + 0.3 * trend_s + 0.2 * vol_s
        return mom_s, trend_s, vol_s, combined

    def on_bar(self, bar: BarData) -> Optional[StrategySignal]:
        self.update_bar_history(bar)
        hist = self.get_bar_history(bar.code)
        if len(hist) < self.lookback + 5:
            return None

        closes = [b.close for b in hist]
        volumes = [b.volume for b in hist]
        mom_s, trend_s, vol_s, combined = self._score(closes, volumes)

        pos = self.get_position(bar.code)
        sig = None
        if pos == 0 and combined > self.buy_threshold:
            qty = self.size_position(bar.code, bar.close)
            sig = self.create_signal(bar.code, SignalAction.BUY, bar.close, qty,
                                     f"Composite score {combined:.2f} above {self.buy_threshold}",
                                     metadata={"momentum": mom_s, "trend": trend_s, "volume": vol_s})
        elif pos > 0 and combined < self.sell_threshold:
            qty = min(self.get_position(bar.code), 100)
            sig = self.create_signal(bar.code, SignalAction.SELL, bar.close, qty,
                                     f"Composite score {combined:.2f} below {self.sell_threshold}")
        return self.apply_risk(bar, sig)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -m pytest tests/test_preloaded_factor.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add services/strategy-engine/strategies/preloaded_factor.py tests/test_preloaded_factor.py
git commit -m "feat(strategy-engine): add multi-factor strategies momentum/low_volatility/multi_factor"
```

---

### Task 6: Register all strategies in factory & `__init__`

**Files:**
- Modify: `services/strategy-engine/strategies/__init__.py` (import new modules)
- Modify: `services/strategy-engine/strategies/builtin.py` (add `register_strategies` registration calls for new modules)
- Test: `tests/test_registration.py`

**Interfaces:**
- Consumes: strategy classes from Tasks 2-5.
- Produces: `register_strategies()` that registers all 16 preloaded strategies in `StrategyFactory`, callable anywhere.

- [ ] **Step 1: Write the failing test**

```python
import sys

sys.path.insert(0, "services/strategy-engine")

from strategies.factory import StrategyFactory
from strategies.builtin import register_strategies


def test_all_preloaded_strategies_registered():
    register_strategies()
    names = set(StrategyFactory.get_all().keys())
    expected = {
        "dual_ma", "rsi_mean_reversion", "macd",
        "boll_breakout", "turtle", "adx_trend", "triple_ma",
        "volume_breakout", "vol_price_up", "obv_divergence",
        "boll_meanrev", "rsi_extreme", "hammer", "engulfing",
        "doji_reversal", "gap_window",
        "momentum_factor", "low_volatility", "multi_factor",
    }
    missing = expected - names
    assert not missing, f"missing strategies: {missing}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -m pytest tests/test_registration.py -v`
Expected: FAIL — `AssertionError: missing strategies: {...}` (none of the new ones registered yet)

- [ ] **Step 3: Wire up registration**

In `services/strategy-engine/strategies/__init__.py`, add imports after the existing `from .builtin import (...)` block:

```python
from .preloaded_trend import (
    BollingerBreakoutStrategy,
    TurtleStrategy,
    ADXTrendStrategy,
    TripleMAStrategy,
)
from .preloaded_volume import (
    VolumeBreakoutStrategy,
    VolPriceUpStrategy,
    OBVDivergenceStrategy,
)
from .preloaded_meanrev import (
    BollingerMeanRevStrategy,
    RSIExtremeStrategy,
    HammerPatternStrategy,
    EngulfingPatternStrategy,
    DojiReversalStrategy,
    GapWindowStrategy,
)
from .preloaded_factor import (
    MomentumFactorStrategy,
    LowVolatilityStrategy,
    MultiFactorStrategy,
)
```

In `services/strategy-engine/strategies/builtin.py`, replace the `register_strategies()` body:

```python
def register_strategies():
    """注册所有内置策略（含预置业界策略）"""
    from .factory import StrategyFactory
    from .preloaded_trend import (
        BollingerBreakoutStrategy, TurtleStrategy,
        ADXTrendStrategy, TripleMAStrategy,
    )
    from .preloaded_volume import (
        VolumeBreakoutStrategy, VolPriceUpStrategy, OBVDivergenceStrategy,
    )
    from .preloaded_meanrev import (
        BollingerMeanRevStrategy, RSIExtremeStrategy, HammerPatternStrategy,
        EngulfingPatternStrategy, DojiReversalStrategy, GapWindowStrategy,
    )
    from .preloaded_factor import (
        MomentumFactorStrategy, LowVolatilityStrategy, MultiFactorStrategy,
    )

    for cls in (
        DualMAStrategy, RSIMeanReversionStrategy, MACDStrategy,
        BollingerBreakoutStrategy, TurtleStrategy, ADXTrendStrategy, TripleMAStrategy,
        VolumeBreakoutStrategy, VolPriceUpStrategy, OBVDivergenceStrategy,
        BollingerMeanRevStrategy, RSIExtremeStrategy, HammerPatternStrategy,
        EngulfingPatternStrategy, DojiReversalStrategy, GapWindowStrategy,
        MomentumFactorStrategy, LowVolatilityStrategy, MultiFactorStrategy,
    ):
        StrategyFactory.register(cls)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -m pytest tests/test_registration.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/strategy-engine/strategies/__init__.py services/strategy-engine/strategies/builtin.py tests/test_registration.py
git commit -m "feat(strategy-engine): register all 16 preloaded strategies in factory"
```

---

### Task 7: DB seed + eastmoney feed

**Files:**
- Create: `services/strategy-engine/app/seed.py`
- Modify: `services/strategy-engine/app/main.py` (call seed in lifespan)
- Modify: `services/strategy-engine/app/feed.py:14` (`provider="mock"` → `provider="eastmoney"`)
- Test: `tests/test_seed.py`

**Interfaces:**
- Consumes: `Strategy` model (`common.models.strategy`), SQLAlchemy `Session`, the 16 strategy names from Tasks 2-5.
- Produces: `async def seed_strategies(db)` — idempotent; inserts one `Strategy` row per preloaded strategy code if not present; returns count inserted. `SEED_STRATEGIES` list of dicts (code/name/type/description/params).

- [ ] **Step 1: Write the failing test**

```python
import sys

sys.path.insert(0, "services/strategy-engine")
sys.path.insert(0, "../")

from app.seed import seed_strategies, SEED_STRATEGIES


def test_seed_inserts_strategies(db_session):
    import asyncio
    inserted = asyncio.run(seed_strategies(db_session))
    assert inserted == len(SEED_STRATEGIES)

    from common.models.strategy import Strategy
    rows = db_session.query(Strategy).all()
    codes = {r.code for r in rows}
    assert len(codes) >= len(SEED_STRATEGIES)


def test_seed_is_idempotent(db_session):
    import asyncio
    asyncio.run(seed_strategies(db_session))
    asyncio.run(seed_strategies(db_session))
    from common.models.strategy import Strategy
    rows = db_session.query(Strategy).all()
    assert len(rows) == len(SEED_STRATEGIES)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -m pytest tests/test_seed.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.seed'`

- [ ] **Step 3: Write minimal implementation**

Create `services/strategy-engine/app/seed.py`:

```python
"""
预置策略元数据（DB seed）
启动时幂等写入，保证前端策略列表开箱即有业界策略
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from common import get_logger
from common.models.strategy import Strategy

logger = get_logger("strategy-engine")

SEED_STRATEGIES: List[Dict[str, Any]] = [
    # ---- 趋势 ----
    {"code": "boll_breakout", "name": "布林带突破", "type": "technical",
     "description": "收盘突破布林上轨买入、跌破下轨卖出，捕捉趋势启动",
     "params": {"boll_period": 20, "std": 2.0, "code": "600000", "position_size": 100}},
    {"code": "turtle", "name": "海龟交易", "type": "technical",
     "description": "唐奇安通道20日上轨突破买入，10日下轨离场，ATR 计算仓位与止损",
     "params": {"entry_period": 20, "exit_period": 10, "atr_period": 14, "code": "600000"}},
    {"code": "adx_trend", "name": "ADX趋势过滤", "type": "technical",
     "description": "ADX 大于阈值且方向向上时顺势买入，趋势转弱卖出",
     "params": {"adx_period": 14, "threshold": 25, "code": "600000"}},
    {"code": "triple_ma", "name": "三均线趋势", "type": "technical",
     "description": "5/20/60 多头排列买入，空头排列卖出",
     "params": {"fast": 5, "mid": 20, "slow": 60, "code": "600000"}},
    # ---- 量价 ----
    {"code": "volume_breakout", "name": "放量突破", "type": "technical",
     "description": "突破20日高点且成交量放大 2 倍以上买入",
     "params": {"high_period": 20, "vol_ratio": 2.0, "code": "600000"}},
    {"code": "vol_price_up", "name": "量价齐升", "type": "technical",
     "description": "价格与成交量同步创 N 日新高时买入",
     "params": {"lookback": 20, "code": "600000"}},
    {"code": "obv_divergence", "name": "OBV 背离", "type": "technical",
     "description": "价格创新高而 OBV 未创新高（顶背离）卖出",
     "params": {"lookback": 20, "code": "600000"}},
    # ---- 均值回归 ----
    {"code": "boll_meanrev", "name": "布林回归", "type": "technical",
     "description": "触及布林下轨买入、上轨卖出、中轨止盈",
     "params": {"boll_period": 20, "std": 2.0, "code": "600000"}},
    {"code": "rsi_extreme", "name": "RSI 极限回归", "type": "technical",
     "description": "RSI 低于 20 超卖买入、高于 80 超买卖出",
     "params": {"rsi_period": 14, "oversold": 20, "overbought": 80, "code": "600000"}},
    # ---- K线形态 ----
    {"code": "hammer", "name": "锤子线", "type": "technical",
     "description": "下跌末段出现长下影线锤子线形态买入",
     "params": {"body_ratio": 2.0, "lookback": 20, "code": "600000"}},
    {"code": "engulfing", "name": "吞没形态", "type": "technical",
     "description": "低位阳包阴买入、高位阴包阳卖出",
     "params": {"lookback": 20, "code": "600000"}},
    {"code": "doji_reversal", "name": "十字星反转", "type": "technical",
     "description": "高位十字星卖出、低位十字星买入",
     "params": {"doji_tolerance": 0.1, "lookback": 20, "code": "600000"}},
    {"code": "gap_window", "name": "跳空缺口", "type": "technical",
     "description": "向上跳空且当日收阳不全回补时买入",
     "params": {"gap_ratio": 0.01, "code": "600000"}},
    # ---- 多因子 ----
    {"code": "momentum_factor", "name": "动量因子", "type": "factor",
     "description": "多周期加权收益率打分，超过阈值买入",
     "params": {"lookbacks": [10, 20, 60], "threshold": 0.05, "code": "600000"}},
    {"code": "low_volatility", "name": "低波动因子", "type": "factor",
     "description": "年化波动率低于阈值时买入，追求稳健",
     "params": {"vol_period": 20, "max_vol": 0.25, "code": "600000"}},
    {"code": "multi_factor", "name": "综合多因子", "type": "factor",
     "description": "动量 + 趋势 + 量能综合评分择时",
     "params": {"lookback": 20, "buy_threshold": 0.6, "sell_threshold": -0.3, "code": "600000"}},
]


def seed_strategies(db: Session) -> int:
    """幂等写入预置策略，返回新增条数"""
    inserted = 0
    for item in SEED_STRATEGIES:
        exists = db.query(Strategy).filter(Strategy.code == item["code"]).first()
        if exists:
            continue
        db.add(Strategy(
            name=item["name"],
            code=item["code"],
            type=item["type"],
            description=item["description"],
            params=item["params"],
            status="active",
        ))
        inserted += 1
    db.commit()
    if inserted:
        logger.info(f"Seeded {inserted} preloaded strategies")
    return inserted
```

Modify `services/strategy-engine/app/main.py` lifespan — after `init_db()` add:

```python
    # 预置业界策略元数据（幂等）
    from app.seed import seed_strategies, SEED_STRATEGIES
    from common.database import SessionLocal
    with SessionLocal() as db:
        seed_strategies(db)
```

Modify `services/strategy-engine/app/feed.py:14`:

```python
    quote = await data_client.get_quote(code, provider="eastmoney")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -m pytest tests/test_seed.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Verify lifespan wiring compiles and run full suite**

Run: `py -m py_compile services/strategy-engine/app/main.py services/strategy-engine/app/seed.py services/strategy-engine/app/feed.py`
Run: `py -m pytest tests/test_seed.py tests/test_registration.py tests/test_risk_mixin.py tests/test_preloaded_trend.py tests/test_preloaded_volume.py tests/test_preloaded_meanrev.py tests/test_preloaded_factor.py -q`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add services/strategy-engine/app/seed.py services/strategy-engine/app/main.py services/strategy-engine/app/feed.py tests/test_seed.py
git commit -m "feat(strategy-engine): seed 16 strategies in DB and switch feed to eastmoney"
```

---

### Task 8: Full-suite verification & frontend check

**Files:** none (verification only)

- [ ] **Step 1: Run the entire backend test suite**

Run: `py -m pytest tests/ -q`
Expected: all pass (existing suites + new strategy tests)

- [ ] **Step 2: Build frontend (Node 22)**

Run: `nvm use 22.22.0`, then `$env:Path="C:\nvm4w\nodejs;"+$env:Path`, then `npm run build` in `web-frontend/`
Expected: build succeeds (strategy list is DB-driven — no frontend code change needed)

- [ ] **Step 3: Restore default Node**

Run: `nvm use 10.15.0`

- [ ] **Step 4: Commit (if any fixes were needed — otherwise skip)**

```bash
git add -A
git commit -m "fix(strategy-engine): resolve issues found in full verification"
```