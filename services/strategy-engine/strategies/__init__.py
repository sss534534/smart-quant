"""
策略模块
提供策略基类、指标库、策略工厂和内置策略
"""
from .base import (
    BaseStrategy,
    StrategyStatus,
    StrategySignal,
    SignalAction,
    BarData,
)
from .indicators import (
    SMA,
    EMA,
    WMA,
    MACD,
    RSI,
    KDJ,
    BOLL,
    ATR,
    OBV,
    VWAP,
    MFI,
    ADX,
    CCI,
    BollingerBandWidth,
    HistoricalVolatility,
    support_resistance,
    crossover,
    crossunder,
)
from .factory import StrategyFactory
from .builtin import (
    DualMAStrategy,
    RSIMeanReversionStrategy,
    MACDStrategy,
    register_strategies,
)

__all__ = [
    # 基类
    "BaseStrategy",
    "StrategyStatus",
    "StrategySignal",
    "SignalAction",
    "BarData",
    # 指标
    "SMA",
    "EMA",
    "WMA",
    "MACD",
    "RSI",
    "KDJ",
    "BOLL",
    "ATR",
    "OBV",
    "VWAP",
    "MFI",
    "ADX",
    "CCI",
    "BollingerBandWidth",
    "HistoricalVolatility",
    "support_resistance",
    "crossover",
    "crossunder",
    # 工厂
    "StrategyFactory",
    # 内置策略
    "DualMAStrategy",
    "RSIMeanReversionStrategy",
    "MACDStrategy",
    "register_strategies",
]