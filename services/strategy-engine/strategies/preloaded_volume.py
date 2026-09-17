"""
量价分析策略集（预置）
放量突破、量价齐升、OBV 背离
"""
from typing import Dict, Any, Optional

import pandas as pd

from .base import BaseStrategy, SignalAction, BarData, StrategySignal
from .indicators import OBV
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
        obv = OBV(pd.Series(closes), pd.Series(vols))
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