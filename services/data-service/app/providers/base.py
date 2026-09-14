from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
from dataclasses import dataclass


@dataclass
class Quote:
    """实时行情数据"""
    code: str
    name: str
    price: float
    change: float
    change_pct: float
    volume: int
    amount: float
    timestamp: datetime


@dataclass
class KLine:
    """K 线数据"""
    code: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class BaseDataProvider(ABC):
    """数据提供者基类"""

    @abstractmethod
    async def get_quote(self, code: str) -> Optional[Quote]:
        """获取实时行情"""
        pass

    @abstractmethod
    async def get_klines(
        self,
        code: str,
        start_date: date,
        end_date: date,
        interval: str = '1d'
    ) -> List[KLine]:
        """获取 K 线数据"""
        pass

    @abstractmethod
    async def get_stock_list(self, exchange: str = None) -> List[Dict]:
        """获取股票列表"""
        pass

    @abstractmethod
    async def initialize(self):
        """初始化连接"""
        pass

    @abstractmethod
    async def close(self):
        """关闭连接"""
        pass
