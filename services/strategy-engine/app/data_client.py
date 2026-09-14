"""
策略引擎的数据服务客户端
异步调用 data-service 获取行情、K线、股票列表
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import date
import httpx

logger = logging.getLogger(__name__)

DATA_SERVICE_URL = "http://data-service:8006"


class DataClient:
    """data-service 异步客户端"""

    def __init__(self, base_url: str = DATA_SERVICE_URL, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def get_quote(self, code: str, provider: str = "mock") -> Optional[Dict[str, Any]]:
        """获取实时行情"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.base_url}/api/v1/market/quote/{code}",
                    params={"provider": provider},
                )
                if resp.status_code == 200:
                    return resp.json()
                logger.warning(f"get_quote {code} failed: {resp.status_code}")
                return None
        except Exception as e:
            logger.error(f"get_quote {code} error: {e}")
            return None

    async def get_klines(
        self,
        code: str,
        start_date: date,
        end_date: date,
        interval: str = "1d",
        provider: str = "mock",
    ) -> List[Dict[str, Any]]:
        """获取 K 线数据"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.base_url}/api/v1/market/kline/{code}",
                    params={
                        "start_date": start_date.isoformat() if hasattr(start_date, "isoformat") else str(start_date),
                        "end_date": end_date.isoformat() if hasattr(end_date, "isoformat") else str(end_date),
                        "interval": interval,
                        "provider": provider,
                    },
                )
                if resp.status_code == 200:
                    return resp.json()
                logger.warning(f"get_klines {code} failed: {resp.status_code}")
                return []
        except Exception as e:
            logger.error(f"get_klines {code} error: {e}")
            return []

    async def get_stock_list(self, exchange: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """获取股票列表"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.base_url}/api/v1/market/stocks",
                    params={"exchange": exchange, "limit": limit},
                )
                if resp.status_code == 200:
                    return resp.json()
                return []
        except Exception as e:
            logger.error(f"get_stock_list error: {e}")
            return []


# 全局实例
data_client = DataClient()
