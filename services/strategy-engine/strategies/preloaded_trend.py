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