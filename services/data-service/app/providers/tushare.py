import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime, date
from .base import BaseDataProvider, Quote, KLine
import tushare as ts
import pandas as pd

logger = logging.getLogger(__name__)


class TushareDataProvider(BaseDataProvider):
    """Tushare 数据提供者"""

    def __init__(self, token: str):
        self.token = token
        self.ts = ts.pro_api(token)
        self._initialized = False

    async def initialize(self):
        """初始化连接"""
        if not self._initialized:
            logger.info("Initializing Tushare data provider")
            self._initialized = True

    async def close(self):
        """关闭连接"""
        logger.info("Closing Tushare data provider")

    async def get_quote(self, code: str) -> Optional[Quote]:
        """获取实时行情"""
        try:
            # 获取实时行情
            df = self.ts.query("quote", list=code)
            if df.empty:
                return None

            row = df.iloc[0]
            now = datetime.now()

            return Quote(
                code=row['ts_code'],
                name=row['name'],
                price=float(row['price']),
                change=float(row['p']),
                change_pct=float(row['pct_change']),
                volume=int(row['volume']),
                amount=float(row['amount']),
                timestamp=now
            )
        except Exception as e:
            logger.error(f"Failed to get quote for {code}: {e}")
            return None

    async def get_klines(
        self,
        code: str,
        start_date: date,
        end_date: date,
        interval: str = '1d'
    ) -> List[KLine]:
        """获取 K 线数据"""
        try:
            # 映射 interval 参数
            interval_map = {
                '1m': '1min',
                '5m': '5min',
                '15m': '15min',
                '30m': '30min',
                '1h': '1hour',
                '4h': '4hour',
                '1d': 'daily',
                '1w': 'weekly',
            }
            ts_interval = interval_map.get(interval, 'daily')

            # 获取 K 线数据
            df = self.ts.kline(
                code=code,
                start=str(start_date),
                end=str(end_date),
                interval=ts_interval,
                fields='close,volume,open,high,low'
            )

            if df.empty:
                return []

            # 转换为 KLine 对象列表
            klines = []
            for _, row in df.iterrows():
                klines.append(KLine(
                    code=row['code'],
                    date=row['dt'],
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=int(row['vol'])
                ))

            return klines
        except Exception as e:
            logger.error(f"Failed to get klines for {code}: {e}")
            return []

    async def get_stock_list(self, exchange: str = None) -> List[Dict]:
        """获取股票列表"""
        try:
            if exchange:
                df = self.ts.query("stock_basic", exchange=exchange)
            else:
                df = self.ts.query("stock_basic")

            stocks = []
            for _, row in df.iterrows():
                stocks.append({
                    'code': row['ts_code'],
                    'name': row['name'],
                    'exchange': row['exchange'],
                    'sector': row['industry'],
                    'market_cap': float(row['total_mv']),
                    'total_shares': float(row['total_share']),
                    'float_shares': float(row['float_share'])
                })

            return stocks
        except Exception as e:
            logger.error(f"Failed to get stock list: {e}")
            return []
