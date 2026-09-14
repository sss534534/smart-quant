"""
市场数据路由
提供股票行情、K线数据、股票列表等接口
"""
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date

from common import (
    get_db,
    get_logger,
    MarketDataQueryRequest,
    StockCodeRequest,
    PaginationRequest,
    PaginationResponse,
    raise_not_found,
    raise_data_error,
    market_cache,
)
from app.models.market import MarketData, StockInfo, Calendar
from app.providers.base import Quote
from app.providers.tushare import TushareDataProvider
from app.providers.mock import MockDataProvider

router = APIRouter()
logger = get_logger("data-service")


# 数据提供者
tushare_provider = TushareDataProvider(
    token=""  # TODO: 从配置加载
)
mock_provider = MockDataProvider()


@router.get("/quote/{code}")
async def get_quote(
    code: str = Path(..., min_length=6, max_length=6, description="股票代码"),
    provider: str = Query(default="mock", description="数据提供者"),
    db: Session = Depends(get_db)
):
    """
    获取实时行情
    
    Args:
        code: 股票代码
        provider: 数据提供者（mock/tushare）
    
    Returns:
        dict: 行情数据
    """
    try:
        # 检查缓存
        cache_key = f"quote:{code}"
        cached = market_cache.get(cache_key)
        if cached:
            logger.info("Cache hit for quote", code=code)
            return cached
        
        # 选择数据提供者
        if provider == "mock":
            provider_instance = mock_provider
        else:
            provider_instance = tushare_provider
        
        await provider_instance.initialize()
        
        # 获取行情数据
        quote = await provider_instance.get_quote(code)
        if not quote:
            raise_not_found("Stock", code)
        
        # 缓存结果
        market_cache.set(cache_key, quote.__dict__, ttl=30)
        
        logger.info("Quote retrieved", code=code, provider=provider)
        
        return quote.__dict__
        
    except Exception as e:
        logger.error("Failed to get quote", code=code, error=str(e))
        raise


@router.get("/kline/{code}")
async def get_klines(
    code: str = Path(..., min_length=6, max_length=6, description="股票代码"),
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    interval: str = Query(default="1d", description="时间间隔"),
    provider: str = Query(default="mock", description="数据提供者"),
    db: Session = Depends(get_db)
):
    """
    获取K线数据
    
    Args:
        code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        interval: 时间间隔
        provider: 数据提供者
    
    Returns:
        list: K线数据列表
    """
    try:
        # 检查缓存
        cache_key = f"kline:{code}:{start_date}:{end_date}:{interval}"
        cached = market_cache.get(cache_key)
        if cached:
            logger.info("Cache hit for kline", code=code)
            return cached
        
        # 选择数据提供者
        if provider == "mock":
            provider_instance = mock_provider
        else:
            provider_instance = tushare_provider
        
        await provider_instance.initialize()
        
        # 获取K线数据
        klines = await provider_instance.get_klines(code, start_date, end_date, interval)
        
        # 转换为字典列表
        result = [kline.__dict__ for kline in klines]
        
        # 缓存结果
        market_cache.set(cache_key, result, ttl=300)  # 5分钟缓存
        
        logger.info("Klines retrieved", code=code, count=len(result))
        
        return result
        
    except Exception as e:
        logger.error("Failed to get klines", code=code, error=str(e))
        raise


@router.get("/stocks")
async def get_stock_list(
    exchange: Optional[str] = Query(None, description="交易所"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    db: Session = Depends(get_db)
):
    """
    获取股票列表
    
    Args:
        exchange: 交易所（SSE/SZSE/BSE）
        limit: 返回数量限制
    
    Returns:
        list: 股票列表
    """
    try:
        # 检查缓存
        cache_key = f"stocks:{exchange}:{limit}"
        cached = market_cache.get(cache_key)
        if cached:
            logger.info("Cache hit for stock list")
            return cached
        
        # 获取股票列表
        provider_instance = mock_provider
        await provider_instance.initialize()
        
        stocks = await provider_instance.get_stock_list(exchange)
        result = stocks[:limit]
        
        # 缓存结果
        market_cache.set(cache_key, result, ttl=600)  # 10分钟缓存
        
        logger.info("Stock list retrieved", count=len(result))
        
        return result
        
    except Exception as e:
        logger.error("Failed to get stock list", error=str(e))
        raise


@router.get("/calendar")
async def get_calendar(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db: Session = Depends(get_db)
):
    """
    获取交易日日历
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
    
    Returns:
        list: 交易日列表
    """
    try:
        # 生成最近30个交易日
        from datetime import timedelta
        
        calendars = []
        current = datetime.now().date()
        
        # 跳过周末
        while current.weekday() >= 5:
            current -= timedelta(days=1)
        
        for _ in range(30):
            date_str = current.strftime('%Y-%m-%d')
            calendars.append({
                "trade_date": date_str,
                "is_holiday": False,
                "market_status": "open"
            })
            current += timedelta(days=1)
            
            # 跳过周末
            if current.weekday() >= 5:
                continue
        
        logger.info("Calendar retrieved", count=len(calendars))
        
        return calendars
        
    except Exception as e:
        logger.error("Failed to get calendar", error=str(e))
        raise


@router.get("/health")
async def health_check():
    """健康检查"""
    from datetime import datetime
    return {
        "status": "healthy",
        "service": "data-service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }