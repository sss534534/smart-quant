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