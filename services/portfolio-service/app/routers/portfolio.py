"""
组合服务路由
提供持仓管理、资金账户、组合分析、流水查询等功能
"""
from fastapi import APIRouter, Depends, Query
from typing import List, Optional, Dict, Any
from datetime import datetime

from common import (
    get_logger,
    raise_not_found,
    raise_validation_error,
    raise_portfolio_error,
    get_current_user,
    AuthUser,
)
from app.engine import portfolio_engine, Position, PositionStatus
from app.persistence import save_state

router = APIRouter()
logger = get_logger("portfolio-service")


@router.get("/positions")
async def get_positions(
    status: Optional[str] = Query(None, description="持仓状态过滤"),
):
    """获取持仓列表"""
    positions = portfolio_engine.get_positions(status=status)
    return [p.to_dict() for p in positions]


@router.get("/positions/{code}")
async def get_position(code: str):
    """获取单只股票持仓"""
    pos = portfolio_engine.get_position(code)
    if not pos:
        raise_not_found("Position", code)
    return pos.to_dict()


@router.get("/summary")
async def get_summary(
    prices: Optional[str] = Query(None, description="价格快照，格式：code1:price1,code2:price2"),
):
    """账户总览"""
    price_dict: Optional[Dict[str, float]] = None
    if prices:
        try:
            price_dict = {}
            for kv in prices.split(","):
                k, v = kv.split(":")
                price_dict[k.strip()] = float(v)
        except Exception:
            raise_validation_error("prices 参数格式应为 code1:price1,code2:price2")
    return portfolio_engine.get_summary(prices=price_dict)


@router.get("/account")
async def get_account():
    """获取资金账户"""
    return portfolio_engine.get_account().to_dict()


@router.get("/logs")
async def get_logs(
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    type: Optional[str] = Query(None, description="流水类型"),
):
    """获取资金流水"""
    logs = portfolio_engine.get_logs(limit=limit, log_type=type)
    return [l.to_dict() for l in logs]


@router.get("/analysis")
async def get_analysis(
    prices: Optional[str] = Query(None, description="价格快照，格式：code1:price1,code2:price2"),
):
    """组合归因分析"""
    price_dict: Optional[Dict[str, float]] = None
    if prices:
        try:
            price_dict = {}
            for kv in prices.split(","):
                k, v = kv.split(":")
                price_dict[k.strip()] = float(v)
        except Exception:
            raise_validation_error("prices 参数格式应为 code1:price1,code2:price2")
    return portfolio_engine.get_attribution(prices=price_dict)


@router.post("/deposit")
async def deposit(
    amount: float = Query(..., gt=0, description="存入金额"),
    description: str = Query("现金存入", description="备注"),
    current_user: AuthUser = Depends(get_current_user),
):
    """入金"""
    if not portfolio_engine.deposit(amount, description):
        raise_portfolio_error("入金失败", "金额必须大于 0")
    save_state(portfolio_engine)
    return {"status": "ok", "balance": portfolio_engine.get_account().balance}


@router.post("/withdraw")
async def withdraw(
    amount: float = Query(..., gt=0, description="取出金额"),
    description: str = Query("现金取出", description="备注"),
    current_user: AuthUser = Depends(get_current_user),
):
    """出金"""
    if not portfolio_engine.withdraw(amount, description):
        raise_portfolio_error("出金失败", "余额不足或金额无效")
    save_state(portfolio_engine)
    return {"status": "ok", "balance": portfolio_engine.get_account().balance}


@router.post("/update-prices")
async def update_prices(prices: Dict[str, float]):
    """批量更新当前价"""
    portfolio_engine.update_prices(prices)
    save_state(portfolio_engine)
    return {"status": "ok", "updated": len(prices)}


@router.post("/rebuild")
async def rebuild_from_trades(trades: List[Dict[str, Any]]):
    """从成交记录重建持仓"""
    portfolio_engine.rebuild_from_trades(trades)
    return {"status": "ok", "stats": portfolio_engine.get_stats()}


@router.post("/process-trade")
async def process_trade(trade: Dict[str, Any]):
    """增量处理单笔成交，更新持仓与账户"""
    try:
        pos, realized_pnl = portfolio_engine.process_trade(
            code=trade["code"],
            direction=trade["direction"],
            price=float(trade["price"]),
            quantity=int(trade["quantity"]),
            commission=float(trade.get("commission", 0)),
            tax=float(trade.get("tax", 0)),
            name=trade.get("name", ""),
            order_no=trade.get("order_no") or trade.get("order_id", ""),
            trade_time=trade.get("trade_time"),
        )
        save_state(portfolio_engine)
        return {
            "status": "ok",
            "position": pos.to_dict(),
            "realized_pnl": round(realized_pnl, 2),
        }
    except Exception as e:
        raise_portfolio_error("处理成交失败", str(e))


@router.get("/stats")
async def get_stats():
    """获取组合统计"""
    return portfolio_engine.get_stats()


@router.get("/status")
async def get_status():
    """获取服务状态"""
    return {
        "status": "running",
        "initialized": portfolio_engine._initialized,
        "stats": portfolio_engine.get_stats(),
    }


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "portfolio-service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }
