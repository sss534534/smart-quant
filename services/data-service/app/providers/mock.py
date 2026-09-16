import asyncio
import logging
import random
from typing import List, Dict, Optional
from datetime import datetime, date, timedelta
from .base import BaseDataProvider, Quote, KLine

logger = logging.getLogger(__name__)


# 模拟股票列表
MOCK_STOCKS = [
    {'code': '600000', 'name': '浦发银行', 'exchange': 'SSE'},
    {'code': '600036', 'name': '招商银行', 'exchange': 'SSE'},
    {'code': '000001', 'name': '平安银行', 'exchange': 'SZSE'},
    {'code': '000002', 'name': '万科 A', 'exchange': 'SZSE'},
    {'code': '601318', 'name': '中国平安', 'exchange': 'SSE'},
    {'code': '000858', 'name': '五粮液', 'exchange': 'SZSE'},
    {'code': '600519', 'name': '贵州茅台', 'exchange': 'SSE'},
    {'code': '300750', 'name': '宁德时代', 'exchange': 'SZSE'},
    {'code': '601127', 'name': '赛力斯', 'exchange': 'SSE'},
    {'code': '002415', 'name': '海康威视', 'exchange': 'SZSE'},
]

# 模拟 K 线数据缓存
MOCK_KLINES_CACHE = {}


def _generate_random_klines(
    code: str,
    start_date: date,
    end_date: date,
    base_price: float = 100.0
) -> List[KLine]:
    """生成随机 K 线数据"""
    klines = []
    current_date = start_date
    current_price = base_price
    current_volume = 1000000

    while current_date <= end_date:
        # 随机波动
        change_pct = random.uniform(-0.05, 0.05)
        open_price = current_price * (1 + random.uniform(-0.01, 0.01))
        close_price = open_price * (1 + change_pct)
        high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.02))
        low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.02))
        volume = int(current_volume * random.uniform(0.5, 1.5))

        klines.append(KLine(
            code=code,
            date=current_date.strftime('%Y-%m-%d'),
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume
        ))

        current_price = close_price
        current_volume = volume
        current_date += timedelta(days=1)

    return klines


class MockDataProvider(BaseDataProvider):
    """模拟数据提供者（用于演示和测试）"""

    def __init__(self):
        self._initialized = False

    async def initialize(self):
        """初始化"""
        if not self._initialized:
            logger.info("Initializing mock data provider")
            self._initialized = True
            # 预生成一些模拟 K 线数据
            for stock in MOCK_STOCKS:
                start = date(2024, 1, 1)
                end = date(2025, 12, 31)
                base_price = random.uniform(10, 500)
                MOCK_KLINES_CACHE[stock['code']] = _generate_random_klines(
                    stock['code'], start, end, base_price
                )

    async def close(self):
        """关闭"""
        pass

    async def get_quote(self, code: str) -> Optional[Quote]:
        """获取模拟实时行情"""
        try:
            stock = next((s for s in MOCK_STOCKS if s['code'] == code), None)
            if not stock:
                return None

            # 获取最新的 K 线作为基准
            klines = MOCK_KLINES_CACHE.get(code, [])
            if not klines:
                return None

            last_kline = klines[-1]
            now = datetime.now()

            # 计算模拟的涨跌幅
            change_pct = random.uniform(-0.03, 0.03)
            current_price = last_kline.close * (1 + change_pct)
            change = current_price - last_kline.close

            return Quote(
                code=code,
                name=stock['name'],
                price=current_price,
                change=change,
                change_pct=change_pct,
                volume=int(last_kline.volume * random.uniform(0.5, 2.0)),
                amount=current_price * int(last_kline.volume),
                timestamp=now
            )
        except Exception as e:
            logger.error(f"Failed to get mock quote for {code}: {e}")
            return None

    async def get_klines(
        self,
        code: str,
        start_date: date,
        end_date: date,
        interval: str = '1d'
    ) -> List[KLine]:
        """获取模拟 K 线数据"""
        try:
            # 检查缓存
            if code in MOCK_KLINES_CACHE:
                klines = MOCK_KLINES_CACHE[code]
                # 过滤日期范围
                filtered = [
                    k for k in klines
                    if start_date <= datetime.strptime(k.date, '%Y-%m-%d').date() <= end_date
                ]
                return filtered

            # 生成新数据
            klines = _generate_random_klines(code, start_date, end_date)
            return klines
        except Exception as e:
            logger.error(f"Failed to get mock klines for {code}: {e}")
            return []

    async def get_stock_list(self, exchange: str = None, limit: int = 1000) -> List[Dict]:
        """获取股票列表"""
        stocks = MOCK_STOCKS
        if exchange:
            stocks = [s for s in MOCK_STOCKS if s['exchange'] == exchange]
        return stocks[:limit]
