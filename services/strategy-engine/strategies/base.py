"""
策略基类
提供策略开发的基础框架和生命周期管理
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class StrategyStatus(str, Enum):
    """策略状态"""
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class SignalAction(str, Enum):
    """信号动作"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class StrategySignal:
    """策略信号"""
    strategy_id: str
    code: str
    action: SignalAction
    price: float
    quantity: int
    reason: str
    strength: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "strategy_id": self.strategy_id,
            "code": self.code,
            "action": self.action.value,
            "price": self.price,
            "quantity": self.quantity,
            "reason": self.reason,
            "strength": self.strength,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class BarData:
    """K线数据"""
    code: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float = 0.0
    turnover: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "code": self.code,
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "amount": self.amount,
            "turnover": self.turnover,
        }


class BaseStrategy(ABC):
    """
    策略基类
    
    所有策略都需要继承此类并实现以下方法：
    - initialize: 初始化策略参数
    - on_bar: 处理K线数据
    - on_trade: 处理成交回报（可选）
    """
    
    name: str = "base_strategy"
    version: str = "1.0.0"
    description: str = "Base strategy class"
    
    def __init__(self, strategy_id: str, params: Dict[str, Any] = None):
        """
        初始化策略
        
        Args:
            strategy_id: 策略ID
            params: 策略参数
        """
        self.strategy_id = strategy_id
        self.params = params or {}
        self._status = StrategyStatus.INITIALIZED
        self._initialized = False
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._signal_history: List[StrategySignal] = []
        self._position: Dict[str, int] = {}  # 持仓 {code: quantity}
        self._capital: float = 0.0  # 可用资金
        self._total_value: float = 0.0  # 总资产
        self._bar_history: Dict[str, List[BarData]] = {}  # 历史K线 {code: [bar1, bar2, ...]}
        self._max_history_length: int = 1000  # 最大历史K线长度
        
        logger.info(f"Strategy {self.name} ({strategy_id}) created")

    @abstractmethod
    def initialize(self, params: Dict[str, Any]):
        """
        初始化策略参数
        
        Args:
            params: 策略参数
        """
        pass

    @abstractmethod
    def on_bar(self, bar: BarData) -> Optional[StrategySignal]:
        """
        处理K线数据
        
        Args:
            bar: K线数据
        
        Returns:
            交易信号（可选）
        """
        pass

    def on_trade(self, trade: Dict[str, Any]):
        """
        处理成交回报
        
        Args:
            trade: 成交数据
        """
        code = trade.get("code")
        quantity = trade.get("quantity", 0)
        direction = trade.get("direction", "buy")
        
        if direction == "buy":
            self._position[code] = self._position.get(code, 0) + quantity
        elif direction == "sell":
            self._position[code] = self._position.get(code, 0) - quantity
            if self._position[code] <= 0:
                del self._position[code]
        
        logger.debug(f"Strategy {self.strategy_id} trade: {trade}")

    def on_error(self, error: str):
        """
        处理错误
        
        Args:
            error: 错误信息
        """
        logger.error(f"Strategy {self.strategy_id} error: {error}")
        self._status = StrategyStatus.ERROR

    def notify(self, event: str, data: Dict[str, Any]):
        """
        通知事件
        
        Args:
            event: 事件类型
            data: 事件数据
        """
        logger.debug(f"Strategy {self.strategy_id} notification: {event} - {data}")

    def emit_signal(self, signal: StrategySignal):
        """
        发出交易信号
        
        Args:
            signal: 交易信号
        """
        self._signal_history.append(signal)
        logger.info(f"Signal emitted: {signal.action.value} {signal.code} at {signal.price}")

    def get_position(self, code: str = None) -> Union[Dict[str, int], int]:
        """
        获取持仓
        
        Args:
            code: 股票代码（可选）
        
        Returns:
            持仓数量或持仓字典
        """
        if code:
            return self._position.get(code, 0)
        return self._position.copy()

    def get_total_position(self) -> int:
        """获取总持仓数量"""
        return sum(self._position.values())

    def update_bar_history(self, bar: BarData):
        """
        更新历史K线
        
        Args:
            bar: K线数据
        """
        if bar.code not in self._bar_history:
            self._bar_history[bar.code] = []
        
        self._bar_history[bar.code].append(bar)
        
        # 限制历史长度
        if len(self._bar_history[bar.code]) > self._max_history_length:
            self._bar_history[bar.code] = self._bar_history[bar.code][-self._max_history_length:]

    def get_bar_history(self, code: str, length: int = None) -> List[BarData]:
        """
        获取历史K线
        
        Args:
            code: 股票代码
            length: 获取长度
        
        Returns:
            K线列表
        """
        bars = self._bar_history.get(code, [])
        if length:
            return bars[-length:]
        return bars

    def get_close_prices(self, code: str, length: int = None) -> pd.Series:
        """
        获取收盘价序列
        
        Args:
            code: 股票代码
            length: 获取长度
        
        Returns:
            收盘价序列
        """
        bars = self.get_bar_history(code, length)
        if not bars:
            return pd.Series()
        
        prices = [bar.close for bar in bars]
        return pd.Series(prices)

    def get_ohlcv(self, code: str, length: int = None) -> pd.DataFrame:
        """
        获取OHLCV数据
        
        Args:
            code: 股票代码
            length: 获取长度
        
        Returns:
            OHLCV DataFrame
        """
        bars = self.get_bar_history(code, length)
        if not bars:
            return pd.DataFrame()
        
        data = {
            "open": [bar.open for bar in bars],
            "high": [bar.high for bar in bars],
            "low": [bar.low for bar in bars],
            "close": [bar.close for bar in bars],
            "volume": [bar.volume for bar in bars],
        }
        
        return pd.DataFrame(data)

    def create_signal(
        self,
        code: str,
        action: SignalAction,
        price: float,
        quantity: int,
        reason: str,
        strength: float = 1.0,
        metadata: Dict[str, Any] = None
    ) -> StrategySignal:
        """
        创建交易信号
        
        Args:
            code: 股票代码
            action: 交易动作
            price: 价格
            quantity: 数量
            reason: 原因
            strength: 信号强度
            metadata: 元数据
        
        Returns:
            交易信号
        """
        return StrategySignal(
            strategy_id=self.strategy_id,
            code=code,
            action=action,
            price=price,
            quantity=quantity,
            reason=reason,
            strength=strength,
            metadata=metadata or {},
        )

    def get_stats(self) -> Dict[str, Any]:
        """获取策略统计信息"""
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "status": self._status.value,
            "start_time": self._start_time.isoformat() if self._start_time else None,
            "end_time": self._end_time.isoformat() if self._end_time else None,
            "total_signals": len(self._signal_history),
            "position": self._position,
            "capital": self._capital,
            "total_value": self._total_value,
        }

    def reset(self):
        """重置策略状态"""
        self._status = StrategyStatus.INITIALIZED
        self._initialized = False
        self._start_time = None
        self._end_time = None
        self._signal_history.clear()
        self._position.clear()
        self._capital = 0.0
        self._total_value = 0.0
        self._bar_history.clear()
        logger.info(f"Strategy {self.strategy_id} reset")