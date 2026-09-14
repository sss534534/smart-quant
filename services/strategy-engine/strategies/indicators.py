"""
技术指标库
提供常用的技术分析指标计算函数
"""
import pandas as pd
import numpy as np
from typing import Tuple, Optional


# ==================== 移动平均线 ====================

def SMA(close: pd.Series, period: int) -> pd.Series:
    """
    简单移动平均线
    
    Args:
        close: 收盘价序列
        period: 周期
    
    Returns:
        SMA序列
    """
    return close.rolling(window=period).mean()


def EMA(close: pd.Series, period: int) -> pd.Series:
    """
    指数移动平均线
    
    Args:
        close: 收盘价序列
        period: 周期
    
    Returns:
        EMA序列
    """
    return close.ewm(span=period, adjust=False).mean()


def WMA(close: pd.Series, period: int) -> pd.Series:
    """
    加权移动平均线
    
    Args:
        close: 收盘价序列
        period: 周期
    
    Returns:
        WMA序列
    """
    weights = np.arange(1, period + 1)
    return close.rolling(window=period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)


# ==================== MACD ====================

def MACD(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    MACD指标
    
    Args:
        close: 收盘价序列
        fast: 快线周期
        slow: 慢线周期
        signal: 信号线周期
    
    Returns:
        (DIF, DEA, MACD柱状图)
    """
    ema_fast = EMA(close, fast)
    ema_slow = EMA(close, slow)
    dif = ema_fast - ema_slow
    dea = EMA(dif, signal)
    macd = (dif - dea) * 2
    return dif, dea, macd


# ==================== RSI ====================

def RSI(close: pd.Series, period: int = 14) -> pd.Series:
    """
    相对强弱指数
    
    Args:
        close: 收盘价序列
        period: 周期
    
    Returns:
        RSI序列
    """
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


# ==================== KDJ ====================

def KDJ(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    KDJ指标
    
    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        period: 周期
    
    Returns:
        (K, D, J)
    """
    lowest_low = low.rolling(window=period).min()
    highest_high = high.rolling(window=period).max()
    rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
    k = rsv.ewm(com=2, adjust=False).mean()
    d = k.ewm(com=2, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j


# ==================== 布林带 ====================

def BOLL(close: pd.Series, period: int = 20, std: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    布林带
    
    Args:
        close: 收盘价序列
        period: 周期
        std: 标准差倍数
    
    Returns:
        (上轨, 中轨, 下轨)
    """
    sma = close.rolling(window=period).mean()
    std_dev = close.rolling(window=period).std()
    upper = sma + std_dev * std
    lower = sma - std_dev * std
    return upper, sma, lower


# ==================== ATR ====================

def ATR(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    平均真实波幅
    
    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        period: 周期
    
    Returns:
        ATR序列
    """
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr


# ==================== 成交量指标 ====================

def OBV(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    能量潮指标
    
    Args:
        close: 收盘价序列
        volume: 成交量序列
    
    Returns:
        OBV序列
    """
    obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
    return obv


def VWAP(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    成交量加权平均价
    
    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        volume: 成交量序列
    
    Returns:
        VWAP序列
    """
    typical_price = (high + low + close) / 3
    vwap = (typical_price * volume).cumsum() / volume.cumsum()
    return vwap


def MFI(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 14) -> pd.Series:
    """
    资金流量指数
    
    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        volume: 成交量序列
        period: 周期
    
    Returns:
        MFI序列
    """
    typical_price = (high + low + close) / 3
    money_flow = typical_price * volume
    positive_flow = money_flow.where(typical_price > typical_price.shift(), 0)
    negative_flow = money_flow.where(typical_price < typical_price.shift(), 0)
    
    positive_mf = positive_flow.rolling(window=period).sum()
    negative_mf = negative_flow.rolling(window=period).sum()
    
    mfi = 100 - (100 / (1 + positive_mf / negative_mf))
    return mfi


# ==================== 趋势指标 ====================

def ADX(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    平均趋向指数
    
    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        period: 周期
    
    Returns:
        ADX序列
    """
    plus_dm = high.diff()
    minus_dm = -low.diff()
    
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    
    tr = ATR(high, low, close, 1)
    
    plus_di = 100 * EMA(plus_dm, period) / EMA(tr, period)
    minus_di = 100 * EMA(minus_dm, period) / EMA(tr, period)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = EMA(dx, period)
    
    return adx


def CCI(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
    """
    顺势指标
    
    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        period: 周期
    
    Returns:
        CCI序列
    """
    tp = (high + low + close) / 3
    sma = tp.rolling(window=period).mean()
    mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    cci = (tp - sma) / (0.015 * mad)
    return cci


# ==================== 波动率指标 ====================

def BollingerBandWidth(close: pd.Series, period: int = 20, std: int = 2) -> pd.Series:
    """
    布林带宽度
    
    Args:
        close: 收盘价序列
        period: 周期
        std: 标准差倍数
    
    Returns:
        布林带宽度序列
    """
    upper, middle, lower = BOLL(close, period, std)
    bandwidth = (upper - lower) / middle * 100
    return bandwidth


def HistoricalVolatility(close: pd.Series, period: int = 20) -> pd.Series:
    """
    历史波动率
    
    Args:
        close: 收盘价序列
        period: 周期
    
    Returns:
        历史波动率序列
    """
    log_return = np.log(close / close.shift())
    vol = log_return.rolling(window=period).std() * np.sqrt(252)
    return vol


# ==================== 形态识别 ====================

def support_resistance(high: pd.Series, low: pd.Series, window: int = 20) -> Tuple[pd.Series, pd.Series]:
    """
    支撑位和阻力位
    
    Args:
        high: 最高价序列
        low: 最低价序列
        window: 窗口大小
    
    Returns:
        (支撑位, 阻力位)
    """
    resistance = high.rolling(window=window).max()
    support = low.rolling(window=window).min()
    return support, resistance


# ==================== 辅助函数 ====================

def crossover(series1: pd.Series, series2: pd.Series) -> pd.Series:
    """
    金叉检测
    
    Args:
        series1: 序列1
        series2: 序列2
    
    Returns:
        金叉信号序列
    """
    return (series1 > series2) & (series1.shift() <= series2.shift())


def crossunder(series1: pd.Series, series2: pd.Series) -> pd.Series:
    """
    死叉检测
    
    Args:
        series1: 序列1
        series2: 序列2
    
    Returns:
        死叉信号序列
    """
    return (series1 < series2) & (series1.shift() >= series2.shift())