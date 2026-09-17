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