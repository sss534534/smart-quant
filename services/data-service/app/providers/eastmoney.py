"""
东方财富数据提供者
无需 token，调用东方财富公开行情接口获取真实 A 股数据
"""
import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime, date

import httpx

from .base import BaseDataProvider, Quote, KLine

logger = logging.getLogger(__name__)

EM_PUSH2 = "https://push2.eastmoney.com/api/qt"
EM_PUSH2HIS = "https://push2his.eastmoney.com/api/qt"


def _to_secid(code: str) -> str:
    """A股代码转东财 secid：6/9 开头=上证(1)，其余=深市/北交(0)"""
    code = code.strip()
    if code.startswith(("6", "9")):
        return f"1.{code}"
    return f"0.{code}"


def _secids(codes: List[str]) -> str:
    return ",".join(_to_secid(c) for c in codes)


class EastmoneyDataProvider(BaseDataProvider):
    """东方财富数据提供者（免费实时行情 + K线 + 股票列表）"""

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._initialized = False

    async def initialize(self):
        if not self._initialized:
            self._client = httpx.AsyncClient(timeout=self.timeout)
            self._initialized = True
            logger.info("Initializing Eastmoney data provider")

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
        self._initialized = False

    async def get_quote(self, code: str) -> Optional[Quote]:
        """获取单只股票实时行情（push2 快照接口）"""
        try:
            url = f"{EM_PUSH2}/stock/get"
            params = {
                "secid": _to_secid(code),
                "fields": "f43,f44,f45,f46,f47,f48,f57,f58,f60,f169,f170,f171",
                "fltt": "2",
                "invt": "2",
            }
            resp = await self._client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json().get("data")
            if not data:
                return None

            price = _to_float(data.get("f43"))
            prev_close = _to_float(data.get("f60"))
            change = _to_float(data.get("f169"))
            change_pct = _to_float(data.get("f170"))
            if change is None and prev_close and price is not None:
                change = price - prev_close
            if change_pct is None and prev_close:
                change_pct = change / prev_close * 100

            return Quote(
                code=data.get("f57") or code,
                name=data.get("f58") or code,
                price=price or 0.0,
                change=change or 0.0,
                change_pct=change_pct or 0.0,
                volume=int(_to_float(data.get("f47")) or 0),
                amount=_to_float(data.get("f48")) or 0.0,
                timestamp=datetime.now(),
            )
        except Exception as e:
            logger.error(f"EM quote failed for {code}: {e}")
            return None

    async def get_quotes(self, codes: List[str]) -> List[Quote]:
        """批量获取实时行情（ulist 批量接口）"""
        if not codes:
            return []
        try:
            url = f"{EM_PUSH2}/ulist.np/get"
            params = {
                "fltt": "2",
                "invt": "2",
                "secids": _secids(codes),
                "fields": "f2,f3,f4,f5,f6,f12,f13,f14,f15,f16,f17,f18",
            }
            resp = await self._client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json().get("data") or {}
            diff = data.get("diff") or []
            quotes = []
            for item in diff:
                code = item.get("f12")
                price = _to_float(item.get("f2"))
                prev_close = _to_float(item.get("f18"))
                change = _to_float(item.get("f4"))
                change_pct = _to_float(item.get("f3"))
                if change is None and prev_close and price is not None:
                    change = price - prev_close
                if change_pct is None and prev_close:
                    change_pct = change / prev_close * 100
                quotes.append(Quote(
                    code=code,
                    name=item.get("f14") or code,
                    price=price or 0.0,
                    change=change or 0.0,
                    change_pct=change_pct or 0.0,
                    volume=int(_to_float(item.get("f5")) or 0),
                    amount=_to_float(item.get("f6")) or 0.0,
                    timestamp=datetime.now(),
                ))
            return quotes
        except Exception as e:
            logger.error(f"EM batch quotes failed: {e}")
            return []

    async def get_klines(
        self,
        code: str,
        start_date: date,
        end_date: date,
        interval: str = '1d'
    ) -> List[KLine]:
        """获取K线数据（push2his kline 接口）"""
        try:
            klt = {
                '1m': '1', '5m': '5', '15m': '15',
                '30m': '30', '60m': '60',
                '1d': '101', '1w': '102', '1M': '103',
            }.get(interval, '101')

            url = f"{EM_PUSH2HIS}/stock/kline/get"
            params = {
                "secid": _to_secid(code),
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57",
                "klt": klt,
                "fqt": "1",  # 前复权
                "beg": start_date.strftime("%Y%m%d"),
                "end": end_date.strftime("%Y%m%d"),
            }
            resp = await self._client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json().get("data") or {}
            klines_str = data.get("klines") or []

            klines = []
            for line in klines_str:
                parts = line.split(",")
                if len(parts) < 7:
                    continue
                klines.append(KLine(
                    code=data.get("code") or code,
                    date=parts[0],
                    open=float(parts[1]),
                    close=float(parts[2]),
                    high=float(parts[3]),
                    low=float(parts[4]),
                    volume=int(float(parts[5])),
                ))
            return klines
        except Exception as e:
            logger.error(f"EM klines failed for {code}: {e}")
            return []

    async def get_stock_list(self, exchange: str = None, limit: int = 1000) -> List[Dict]:
        """获取股票列表（clist 接口，fs 按交易所过滤）"""
        fs_map = {
            "SSE": "m:1+t:2,m:1+t:23",           # 沪市A股 + 科创板
            "SZSE": "m:0+t:6,m:0+t:80",          # 深市A股 + 创业板
            "BSE": "m:0+t:81+s:2048",            # 北交所
            None: "m:1+t:2,m:1+t:23,m:0+t:6,m:0+t:80,m:0+t:81+s:2048",
        }
        fs = fs_map.get(exchange)
        if not fs:
            return []

        try:
            url = f"{EM_PUSH2}/clist/get"
            params = {
                "pn": "1",
                "pz": str(min(limit, 5000)),
                "po": "1",
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "fid": "f12",
                "fs": fs,
                "fields": "f12,f14,f13",
            }
            resp = await self._client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json().get("data") or {}
            diff = data.get("diff") or []
            exchange_map = {0: "SZSE", 1: "SSE"}
            return [
                {
                    "code": item.get("f12"),
                    "name": item.get("f14"),
                    "exchange": exchange_map.get(int(item.get("f13", 0)), ""),
                }
                for item in diff
            ]
        except Exception as e:
            logger.error(f"EM stock list failed: {e}")
            return []


def _to_float(v) -> Optional[float]:
    """东财接口 fltt=2 下部分字段返回字符串，统一转 float"""
    if v is None or v == "" or v == "-":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# 全局实例
eastmoney_provider = EastmoneyDataProvider()