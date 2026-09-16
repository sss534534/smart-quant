"""
市场数据路由
提供股票行情、K线数据、股票列表等接口
"""
from fastapi import APIRouter, Depends, Query, Path, Body, HTTPException
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
    raise_validation_error,
    raise_data_error,
    market_cache,
    get_optional_user,
    AuthUser,
)
from common.models.market import MarketData, StockInfo, Calendar, Watchlist
from app.providers.base import Quote
from app.providers.tushare import TushareDataProvider
from app.providers.eastmoney import EastmoneyDataProvider
from app.providers.mock import MockDataProvider

from common import settings
router = APIRouter()
logger = get_logger("data-service")


# 数据提供者
tushare_provider = TushareDataProvider(
    token=settings.tushare.TUSHARE_TOKEN or ""  # 从配置加载
)
eastmoney_provider = EastmoneyDataProvider()
mock_provider = MockDataProvider()

PROVIDER_MAP = {
    "mock": mock_provider,
    "eastmoney": eastmoney_provider,
    "em": eastmoney_provider,
    "tushare": tushare_provider,
}

DEFAULT_PROVIDER = "eastmoney"


def _resolve_provider(provider: str):
    """按名称解析数据提供者，默认使用东财真实数据"""
    name = (provider or DEFAULT_PROVIDER).strip().lower()
    return PROVIDER_MAP.get(name, eastmoney_provider)


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
        provider_instance = _resolve_provider(provider)
        
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
        provider_instance = _resolve_provider(provider)
        
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
    provider: str = Query(default=DEFAULT_PROVIDER, description="数据提供者"),
    db: Session = Depends(get_db)
):
    """
    获取股票列表
    
    Args:
        exchange: 交易所（SSE/SZSE/BSE）
        limit: 返回数量限制
        provider: 数据提供者
    
    Returns:
        list: 股票列表
    """
    try:
        # 检查缓存
        cache_key = f"stocks:{exchange}:{limit}:{provider}"
        cached = market_cache.get(cache_key)
        if cached:
            logger.info("Cache hit for stock list")
            return cached
        
        # 获取股票列表
        provider_instance = _resolve_provider(provider)
        await provider_instance.initialize()
        
        stocks = await provider_instance.get_stock_list(exchange, limit)
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


@router.get("/board")
async def get_market_board(
    codes: str = Query("", description="股票代码列表，逗号分隔，留空返回默认看板"),
    provider: str = Query(default=DEFAULT_PROVIDER, description="数据提供者"),
    db: Session = Depends(get_db)
):
    """
    行情看板：批量获取多只股票的最新行情
    
    Args:
        codes: 股票代码列表，逗号分隔（如 "600000,000001,300750"）
        provider: 数据提供者
    
    Returns:
        dict: 行情看板（每只股票的实时行情快照）
    """
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    if not code_list:
        code_list = ["600519", "601318", "600036", "000001", "000858", "300750", "002415", "601127"]

    # 选择数据提供者
    provider_instance = _resolve_provider(provider)
    await provider_instance.initialize()

    results = []
    for code in code_list:
        try:
            cache_key = f"board:{code}:{provider}"
            cached = market_cache.get(cache_key)
            if cached:
                results.append(cached)
                continue
            quote = await provider_instance.get_quote(code)
            if quote:
                data = quote.__dict__
                data["code"] = data.get("code") or code
                data["provider"] = provider
                market_cache.set(cache_key, data, ttl=10)
                results.append(data)
        except Exception:
            continue

    return {
        "count": len(results),
        "quotes": results,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/watchlist")
async def get_watchlist(
    current_user: AuthUser = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    获取自选股列表
    
    按用户隔离自选股列表，未登录时返回默认列表。
    同时附带每只股票的最新行情快照。
    """
    user_id = current_user.user_id if current_user else 0

    items = db.query(Watchlist) \
        .filter(Watchlist.user_id == user_id) \
        .order_by(Watchlist.sort_order.asc(), Watchlist.created_at.desc()) \
        .all()

    # 批量获取行情（东财真实数据）
    provider_instance = _resolve_provider(DEFAULT_PROVIDER)
    await provider_instance.initialize()
    for item in items:
        try:
            cache_key = f"board:{item.code}:{DEFAULT_PROVIDER}"
            cached = market_cache.get(cache_key)
            if cached:
                item.latest_price = cached.get("price")
                item.change_percent = cached.get("change_percent")
            else:
                quote = await provider_instance.get_quote(item.code)
                if quote:
                    item.latest_price = quote.price
                    item.change_percent = getattr(quote, "change_pct", 0)
                    market_cache.set(cache_key, quote.__dict__, ttl=10)
                else:
                    item.latest_price = None
                    item.change_percent = None
        except Exception:
            item.latest_price = None
            item.change_percent = None

    return [
        {
            "code": item.code,
            "name": item.name,
            "remark": item.remark,
            "sort_order": item.sort_order,
            "latest_price": item.latest_price,
            "change_percent": item.change_percent,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in items
    ]


@router.post("/watchlist")
async def add_to_watchlist(
    data: dict = Body(..., example={"code": "600000", "remark": "浦发银行自选"}),
    current_user: AuthUser = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    添加自选股
    
    body: {"code": "股票代码", "remark": "备注（可选）"}
    """
    code = (data.get("code") or "").strip()
    remark = (data.get("remark") or "").strip()
    if not code or len(code) not in (6, 8):
        raise_validation_error("股票代码必须为6位或8位")

    user_id = current_user.user_id if current_user else 0

    # 查重
    existing = db.query(Watchlist).filter(Watchlist.user_id == user_id, Watchlist.code == code).first()
    if existing:
        raise_validation_error(f"股票 {code} 已在自选股中")

    # 查股票名称
    stock_info = db.query(StockInfo).filter(StockInfo.code == code).first()
    name = stock_info.name if stock_info else ""

    item = Watchlist(
        user_id=user_id,
        code=code,
        name=name,
        remark=remark,
        sort_order=0,
    )
    db.add(item)
    db.commit()

    logger.info("Watchlist add", user_id=user_id, code=code)
    return {"code": code, "name": name, "remark": remark, "created_at": item.created_at.isoformat()}


@router.delete("/watchlist/{code}")
async def remove_from_watchlist(
    code: str,
    current_user: AuthUser = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """删除自选股"""
    user_id = current_user.user_id if current_user else 0

    item = db.query(Watchlist).filter(Watchlist.user_id == user_id, Watchlist.code == code).first()
    if not item:
        raise_not_found("Watchlist", code)

    db.delete(item)
    db.commit()
    logger.info("Watchlist remove", user_id=user_id, code=code)
    return {"code": code, "message": "已删除"}


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