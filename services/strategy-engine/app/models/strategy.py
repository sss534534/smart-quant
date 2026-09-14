from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class StrategyStatus(Enum):
    """策略状态"""
    INIT = "init"           # 初始化中
    RUNNING = "running"     # 运行中
    PAUSED = "paused"       # 暂停
    STOPPED = "stopped"     # 已停止
    ERROR = "error"         # 错误


class SignalAction(Enum):
    """信号操作"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"


@dataclass
class StrategySignal:
    """策略信号"""
    signal_id: str
    strategy_id: str
    strategy_name: str
    code: str
    action: SignalAction
    price: float
    quantity: int
    strength: float = 1.0
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    params: Dict = field(default_factory=dict)


class BaseStrategy(ABC):
    """策略基类"""

    name: str = "base_strategy"
    description: str = "Base strategy"
    version: str = "1.0.0"

    def __init__(self, strategy_id: str, params: Dict = None):
        self.strategy_id = strategy_id
        self.params = params or {}
        self._initialized = False
        self._status = StrategyStatus.INIT
        self._signals: List[StrategySignal] = []
        self._callbacks: Dict[str, List[Callable]] = {
            "on_signal": [],
            "on_bar": [],
            "on_trade": [],
            "on_error": [],
        }
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._stats = {
            "bars_processed": 0,
            "signals_generated": 0,
            "trades_executed": 0,
        }

    @abstractmethod
    def initialize(self, params: Dict) -> None:
        """初始化策略"""
        pass

    @abstractmethod
    def on_bar(self, bar: Dict) -> Optional[StrategySignal]:
        """处理 K 线数据，返回信号（可选）"""
        pass

    def on_trade(self, trade: Dict) -> None:
        """处理交易"""
        pass

    def register_callback(self, event: str, callback: Callable):
        """注册回调"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def unregister_callback(self, event: str, callback: Callable):
        """注销回调"""
        if event in self._callbacks:
            if callback in self._callbacks[event]:
                self._callbacks[event].remove(callback)

    def notify(self, event: str, *args, **kwargs):
        """通知回调"""
        callbacks = self._callbacks.get(event, [])
        for callback in callbacks:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Callback error {event}: {e}")

    def emit_signal(self, signal: StrategySignal):
        """发出信号"""
        self._signals.append(signal)
        self._stats["signals_generated"] += 1
        self.notify("on_signal", signal)
        logger.info(f"Signal: {signal.code} {signal.action.value} - {signal.reason}")

    def emit_trade(self, trade: Dict):
        """发出交易"""
        self.notify("on_trade", trade)

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "status": self._status.value,
            "bars_processed": self._stats["bars_processed"],
            "signals_generated": self._stats["signals_generated"],
            "trades_executed": self._stats["trades_executed"],
            "start_time": self._start_time.isoformat() if self._start_time else None,
            "end_time": self._end_time.isoformat() if self._end_time else None,
        }

    def reset_stats(self):
        """重置统计"""
        self._stats = {
            "bars_processed": 0,
            "signals_generated": 0,
            "trades_executed": 0,
        }

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "params": self.params,
            "status": self._status.value,
            "stats": self.get_stats(),
        }
