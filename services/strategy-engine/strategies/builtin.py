"""
示例策略：双均线策略
当短期均线上穿长期均线时买入，下穿时卖出
"""
from typing import Dict, Any, Optional
import pandas as pd

from .base import BaseStrategy, StrategySignal, SignalAction, BarData
from .indicators import SMA, crossover, crossunder


class DualMAStrategy(BaseStrategy):
    """双均线策略"""
    
    name = "dual_ma"
    version = "1.0.0"
    description = "Dual Moving Average Crossover Strategy"
    
    def __init__(self, strategy_id: str, params: Dict[str, Any] = None):
        super().__init__(strategy_id, params)
        
        # 策略参数
        self.short_period: int = 5  # 短期均线周期
        self.long_period: int = 20  # 长期均线周期
        self.position_size: int = 100  # 每次交易数量
        self.code: str = "000001"  # 默认股票代码
        
    def initialize(self, params: Dict[str, Any]):
        """
        初始化策略参数
        
        Args:
            params: 策略参数
        """
        self.short_period = params.get("short_period", self.short_period)
        self.long_period = params.get("long_period", self.long_period)
        self.position_size = params.get("position_size", self.position_size)
        self.code = params.get("code", self.code)
        
        # 验证参数
        if self.short_period >= self.long_period:
            raise ValueError("Short period must be less than long period")
        
        self._initialized = True
        self._status = self._status.RUNNING
        self._start_time = pd.Timestamp.now()
        
        self.notify("initialized", {
            "short_period": self.short_period,
            "long_period": self.long_period,
            "position_size": self.position_size,
            "code": self.code,
        })
    
    def on_bar(self, bar: BarData) -> Optional[StrategySignal]:
        """
        处理K线数据
        
        Args:
            bar: K线数据
        
        Returns:
            交易信号（可选）
        """
        # 更新历史数据
        self.update_bar_history(bar)
        
        # 检查是否有足够的历史数据
        bars = self.get_bar_history(bar.code, self.long_period + 1)
        if len(bars) < self.long_period:
            return None
        
        # 计算均线
        close_prices = self.get_close_prices(bar.code, self.long_period + 1)
        short_ma = SMA(close_prices, self.short_period)
        long_ma = SMA(close_prices, self.long_period)
        
        # 检查金叉和死叉
        if crossover(short_ma, long_ma).iloc[-1]:
            # 金叉 - 买入信号
            current_position = self.get_position(bar.code)
            if current_position == 0:
                return self.create_signal(
                    code=bar.code,
                    action=SignalAction.BUY,
                    price=bar.close,
                    quantity=self.position_size,
                    reason=f"Golden cross: MA{self.short_period} crossed above MA{self.long_period}",
                    strength=0.8,
                    metadata={
                        "short_ma": short_ma.iloc[-1],
                        "long_ma": long_ma.iloc[-1],
                    }
                )
        
        elif crossunder(short_ma, long_ma).iloc[-1]:
            # 死叉 - 卖出信号
            current_position = self.get_position(bar.code)
            if current_position > 0:
                return self.create_signal(
                    code=bar.code,
                    action=SignalAction.SELL,
                    price=bar.close,
                    quantity=min(current_position, self.position_size),
                    reason=f"Death cross: MA{self.short_period} crossed below MA{self.long_period}",
                    strength=0.8,
                    metadata={
                        "short_ma": short_ma.iloc[-1],
                        "long_ma": long_ma.iloc[-1],
                    }
                )
        
        return None


class RSIMeanReversionStrategy(BaseStrategy):
    """RSI均值回归策略"""
    
    name = "rsi_mean_reversion"
    version = "1.0.0"
    description = "RSI Mean Reversion Strategy"
    
    def __init__(self, strategy_id: str, params: Dict[str, Any] = None):
        super().__init__(strategy_id, params)
        
        # 策略参数
        self.rsi_period: int = 14
        self.oversold: float = 30
        self.overbought: float = 70
        self.position_size: int = 100
        self.code: str = "000001"
        
    def initialize(self, params: Dict[str, Any]):
        """初始化策略参数"""
        self.rsi_period = params.get("rsi_period", self.rsi_period)
        self.oversold = params.get("oversold", self.oversold)
        self.overbought = params.get("overbought", self.overbought)
        self.position_size = params.get("position_size", self.position_size)
        self.code = params.get("code", self.code)
        
        self._initialized = True
        self._status = self._status.RUNNING
        self._start_time = pd.Timestamp.now()
        
        self.notify("initialized", {
            "rsi_period": self.rsi_period,
            "oversold": self.oversold,
            "overbought": self.overbought,
        })
    
    def on_bar(self, bar: BarData) -> Optional[StrategySignal]:
        """处理K线数据"""
        self.update_bar_history(bar)
        
        # 检查是否有足够的历史数据
        bars = self.get_bar_history(bar.code, self.rsi_period + 1)
        if len(bars) < self.rsi_period + 1:
            return None
        
        # 计算RSI
        from .indicators import RSI
        close_prices = self.get_close_prices(bar.code, self.rsi_period + 1)
        rsi = RSI(close_prices, self.rsi_period)
        current_rsi = rsi.iloc[-1]
        
        # 检查超买超卖
        if current_rsi < self.oversold:
            # 超卖 - 买入信号
            current_position = self.get_position(bar.code)
            if current_position == 0:
                return self.create_signal(
                    code=bar.code,
                    action=SignalAction.BUY,
                    price=bar.close,
                    quantity=self.position_size,
                    reason=f"RSI oversold: {current_rsi:.2f} < {self.oversold}",
                    strength=(self.oversold - current_rsi) / self.oversold,
                    metadata={"rsi": current_rsi}
                )
        
        elif current_rsi > self.overbought:
            # 超买 - 卖出信号
            current_position = self.get_position(bar.code)
            if current_position > 0:
                return self.create_signal(
                    code=bar.code,
                    action=SignalAction.SELL,
                    price=bar.close,
                    quantity=min(current_position, self.position_size),
                    reason=f"RSI overbought: {current_rsi:.2f} > {self.overbought}",
                    strength=(current_rsi - self.overbought) / (100 - self.overbought),
                    metadata={"rsi": current_rsi}
                )
        
        return None


class MACDStrategy(BaseStrategy):
    """MACD策略"""
    
    name = "macd"
    version = "1.0.0"
    description = "MACD Crossover Strategy"
    
    def __init__(self, strategy_id: str, params: Dict[str, Any] = None):
        super().__init__(strategy_id, params)
        
        # 策略参数
        self.fast_period: int = 12
        self.slow_period: int = 26
        self.signal_period: int = 9
        self.position_size: int = 100
        self.code: str = "000001"
        
    def initialize(self, params: Dict[str, Any]):
        """初始化策略参数"""
        self.fast_period = params.get("fast_period", self.fast_period)
        self.slow_period = params.get("slow_period", self.slow_period)
        self.signal_period = params.get("signal_period", self.signal_period)
        self.position_size = params.get("position_size", self.position_size)
        self.code = params.get("code", self.code)
        
        self._initialized = True
        self._status = self._status.RUNNING
        self._start_time = pd.Timestamp.now()
        
        self.notify("initialized", {
            "fast_period": self.fast_period,
            "slow_period": self.slow_period,
            "signal_period": self.signal_period,
        })
    
    def on_bar(self, bar: BarData) -> Optional[StrategySignal]:
        """处理K线数据"""
        self.update_bar_history(bar)
        
        # 检查是否有足够的历史数据
        required_bars = self.slow_period + self.signal_period + 1
        bars = self.get_bar_history(bar.code, required_bars)
        if len(bars) < required_bars:
            return None
        
        # 计算MACD
        from .indicators import MACD, crossover, crossunder
        close_prices = self.get_close_prices(bar.code, required_bars)
        dif, dea, macd = MACD(close_prices, self.fast_period, self.slow_period, self.signal_period)
        
        # 检查金叉和死叉
        if crossover(dif, dea).iloc[-1]:
            # 金叉 - 买入信号
            current_position = self.get_position(bar.code)
            if current_position == 0:
                return self.create_signal(
                    code=bar.code,
                    action=SignalAction.BUY,
                    price=bar.close,
                    quantity=self.position_size,
                    reason=f"MACD golden cross: DIF crossed above DEA",
                    strength=abs(dif.iloc[-1] - dea.iloc[-1]) / bar.close * 100,
                    metadata={
                        "dif": dif.iloc[-1],
                        "dea": dea.iloc[-1],
                        "macd": macd.iloc[-1],
                    }
                )
        
        elif crossunder(dif, dea).iloc[-1]:
            # 死叉 - 卖出信号
            current_position = self.get_position(bar.code)
            if current_position > 0:
                return self.create_signal(
                    code=bar.code,
                    action=SignalAction.SELL,
                    price=bar.close,
                    quantity=min(current_position, self.position_size),
                    reason=f"MACD death cross: DIF crossed below DEA",
                    strength=abs(dif.iloc[-1] - dea.iloc[-1]) / bar.close * 100,
                    metadata={
                        "dif": dif.iloc[-1],
                        "dea": dea.iloc[-1],
                        "macd": macd.iloc[-1],
                    }
                )
        
        return None


# 策略注册
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