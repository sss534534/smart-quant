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