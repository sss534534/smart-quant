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
    get_optional_user,
    AuthUser,
)
from app.engine import portfolio_engine, Position, PositionStatus
from app.persistence import save_state

router = APIRouter()
logger = get_logger("portfolio-service")


@router.get("/report")
async def get_portfolio_report():
    """
    完整组合分析报告
    汇总指标 + 收益分解 + 集中度 + 持仓明细 + 资金曲线
    """
    positions = portfolio_engine.get_positions()
    account = portfolio_engine.get_account()
    logs = portfolio_engine.get_logs(limit=1000)

    # 持仓市值
    active_positions = [p for p in positions if p.status == PositionStatus.ACTIVE and p.quantity > 0]
    total_position_value = sum(p.quantity * (p.current_price or p.avg_cost) for p in active_positions)
    total_assets = account.balance + total_position_value

    # 收益分解
    realized_pnl = sum(p.realized_pnl or 0 for p in positions)
    unrealized_pnl = sum(p.unrealized_pnl or 0 for p in active_positions)

    # 集中度
    holdings_sorted = sorted(
        active_positions, key=lambda p: p.quantity * (p.current_price or p.avg_cost), reverse=True
    )
    top1_value = holdings_sorted[0].quantity * (holdings_sorted[0].current_price or holdings_sorted[0].avg_cost) if holdings_sorted else 0
    top5_value = sum(p.quantity * (p.current_price or p.avg_cost) for p in holdings_sorted[:5])
    top1_pct = top1_value / total_assets if total_assets > 0 else 0
    top5_pct = top5_value / total_assets if total_assets > 0 else 0

    # HHI 集中度指数
    if total_assets > 0:
        shares = [(p.quantity * (p.current_price or p.avg_cost)) / total_assets for p in active_positions]
        hhi = sum(s ** 2 for s in shares)
    else:
        hhi = 0

    # 持仓明细
    holdings_detail = []
    for p in active_positions:
        mv = p.quantity * (p.current_price or p.avg_cost)
        pnl = (p.current_price or p.avg_cost) - p.avg_cost
        holdings_detail.append({
            "code": p.code,
            "name": p.name,
            "quantity": p.quantity,
            "avg_price": p.avg_price,
            "avg_cost": p.avg_cost,
            "current_price": p.current_price,
            "market_value": mv,
            "pnl": pnl,
            "pnl_pct": pnl / p.avg_cost * 100 if p.avg_cost > 0 else 0,
            "weight": mv / total_assets if total_assets > 0 else 0,
        })

    # 资金曲线（按时间正序）
    equity_curve = []
    for log in sorted(logs, key=lambda l: l.created_at):
        equity_curve.append({
            "balance": log.balance_after,
            "date": log.created_at.strftime("%Y-%m-%d %H:%M") if hasattr(log.created_at, 'strftime') else str(log.created_at),
            "reason": log.description,
        })

    summary = portfolio_engine.get_summary()

    return {
        "total_assets": total_assets,
        "cash": account.balance,
        "position_value": total_position_value,
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "total_return": summary.get("total_profit_pct", 0),
        "concentration": {
            "top1_pct": top1_pct,
            "top5_pct": top5_pct,
            "hhi": hhi,
            "stock_count": len(active_positions),
        },
        "holdings": holdings_detail,
        "equity_curve": equity_curve[:50],
        "initial_capital": summary.get("initial_capital", 0),
    }


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
