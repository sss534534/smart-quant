"""
策略管理路由
提供策略的CRUD操作和信号管理
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from collections import Counter

from common import (
    get_db,
    get_logger,
    StrategyCreateRequest,
    StrategyUpdateRequest,
    StrategyResponse,
    PaginationRequest,
    PaginationResponse,
    raise_not_found,
    raise_validation_error,
    raise_strategy_error,
    get_current_user,
    AuthUser,
)
from fastapi import Depends

router = APIRouter()
logger = get_logger("strategy-engine")


@router.get("/", response_model=PaginationResponse)
async def list_strategies(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="策略状态"),
    db: Session = Depends(get_db)
):
    """
    获取策略列表
    
    Returns:
        PaginationResponse: 分页策略列表
    """
    from common.models.strategy import Strategy
    
    query = db.query(Strategy).filter(Strategy.status != 'deleted')
    
    if status:
        query = query.filter(Strategy.status == status)
    
    total = query.count()
    strategies = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return PaginationResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[StrategyResponse.model_validate(s) for s in strategies]
    )


@router.get("/compare")
async def compare_strategies(
    ids: str = Query(..., description="策略ID列表，逗号分隔，如 1,2,3"),
    db: Session = Depends(get_db),
):
    """
    多策略对比分析
    
    比较多个策略的信号产出能力、运行状态与活跃度。
    
    Args:
        ids: 策略ID列表（逗号分隔）
        db: 数据库会话
    
    Returns:
        dict: 多策略对比结果
    """
    from common.models.strategy import Strategy, StrategySignal

    try:
        strategy_ids = [int(x.strip()) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise_validation_error("ids 参数必须为数字列表，如 1,2,3")

    result = []
    for sid in strategy_ids:
        strategy = db.query(Strategy).filter(Strategy.id == sid).first()
        if not strategy:
            continue

        # 信号统计
        signals = db.query(StrategySignal).filter(StrategySignal.strategy_id == sid).all()
        action_counts = Counter(s.action for s in signals)
        buy_signals = action_counts.get("buy", 0)
        sell_signals = action_counts.get("sell", 0)

        # 最近信号时间
        latest_signal = None
        if signals:
            latest_signal = max(s.created_at for s in signals).isoformat()

        signal_ids = [s.id for s in signals]
        result.append({
            "strategy_id": sid,
            "name": strategy.name,
            "type": strategy.type,
            "status": strategy.status,
            "total_signals": len(signals),
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "hold_signals": action_counts.get("hold", 0),
            "buy_sell_ratio": round(buy_signals / sell_signals, 2) if sell_signals else None,
            "last_signal_time": latest_signal,
            "signal_ids": signal_ids[:200],
        })

    return {
        "count": len(result),
        "strategies": result,
    }


@router.get("/{strategy_id}/analysis", response_model=dict)
async def analyze_strategy(
    strategy_id: int,
    days: int = Query(90, ge=7, le=730, description="分析窗口天数"),
    db: Session = Depends(get_db),
):
    """
    策略信号分析
    
    统计策略在指定时间窗口内的信号产出情况，包括：
    - 信号总量与操作分布
    - 按日期的信号趋势
    - 信号强度分布
    - 信号股票分布
    
    Args:
        strategy_id: 策略ID
        days: 分析窗口天数
    
    Returns:
        dict: 策略信号分析结果
    """
    from common.models.strategy import Strategy, StrategySignal

    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise_not_found("Strategy", strategy_id)

    since = datetime.utcnow() - timedelta(days=days)
    signals = db.query(StrategySignal)\
        .filter(StrategySignal.strategy_id == strategy_id)\
        .filter(StrategySignal.created_at >= since)\
        .order_by(StrategySignal.created_at.asc())\
        .all()

    # 操作分布
    action_counts = Counter(s.action for s in signals)
    total = len(signals)

    # 按日期趋势（最近 N 天）
    daily = Counter(s.created_at.date().isoformat() for s in signals)
    today = datetime.utcnow().date()
    trend = []
    for i in range(days, 0, -1):
        d = (today - timedelta(days=i)).isoformat()
        trend.append({"date": d, "count": daily.get(d, 0)})

    # 强度分布
    strength_buckets = {
        "high (>=0.8)": sum(1 for s in signals if (s.strength or 0) >= 0.8),
        "medium (0.5~0.8)": sum(1 for s in signals if 0.5 <= (s.strength or 0) < 0.8),
        "low (<0.5)": sum(1 for s in signals if (s.strength or 0) < 0.5),
    }

    # 标的分布
    code_dist = []
    for code, cnt in Counter(s.code for s in signals).most_common(10):
        code_dist.append({"code": code, "count": cnt})

    return {
        "strategy_id": strategy_id,
        "name": strategy.name,
        "days": days,
        "total_signals": total,
        "action_distribution": {
            "buy": action_counts.get("buy", 0),
            "sell": action_counts.get("sell", 0),
            "hold": action_counts.get("hold", 0),
        },
        "signal_rate_per_day": round(total / days, 2),
        "daily_trend": trend,
        "strength_distribution": strength_buckets,
        "code_distribution": code_dist,
        "avg_strength": round(sum((s.strength or 0) for s in signals) / total, 3) if total else 0,
        "latest_signals": [
            {
                "id": s.id,
                "code": s.code,
                "action": s.action,
                "price": s.price,
                "quantity": s.quantity,
                "reason": s.reason,
                "strength": s.strength,
                "created_at": s.created_at.isoformat(),
            }
            for s in signals[-20:]
        ],
    }


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: int,
    db: Session = Depends(get_db)
):
    """
    获取策略详情
    
    Args:
        strategy_id: 策略ID
    
    Returns:
        StrategyResponse: 策略详情
    """
    from common.models.strategy import Strategy
    
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise_not_found("Strategy", strategy_id)
    
    return StrategyResponse.model_validate(strategy)


@router.post("/", response_model=StrategyResponse, status_code=201)
async def create_strategy(
    request: StrategyCreateRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """
    创建新策略
    
    Args:
        request: 策略创建请求
    
    Returns:
        StrategyResponse: 创建的策略
    """
    from common.models.strategy import Strategy
    
    # 检查策略代码是否已存在
    existing = db.query(Strategy).filter(Strategy.code == request.code).first()
    if existing:
        raise_validation_error(f"策略代码 {request.code} 已存在")
    
    strategy = Strategy(
        name=request.name,
        code=request.code,
        type=request.type,
        description=request.description,
        params=request.params
    )
    
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    
    logger.info("Strategy created", strategy_id=strategy.id, name=strategy.name)
    
    return StrategyResponse.model_validate(strategy)


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: int,
    request: StrategyUpdateRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """
    更新策略
    
    Args:
        strategy_id: 策略ID
        request: 策略更新请求
    
    Returns:
        StrategyResponse: 更新后的策略
    """
    from common.models.strategy import Strategy
    
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise_not_found("Strategy", strategy_id)
    
    # 更新字段
    if request.name is not None:
        strategy.name = request.name
    if request.description is not None:
        strategy.description = request.description
    if request.params is not None:
        strategy.params = request.params
    if request.status is not None:
        strategy.status = request.status
    
    strategy.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(strategy)
    
    logger.info("Strategy updated", strategy_id=strategy.id)
    
    return StrategyResponse.model_validate(strategy)


@router.delete("/{strategy_id}")
async def delete_strategy(
    strategy_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """
    删除策略（软删除）
    
    Args:
        strategy_id: 策略ID
    
    Returns:
        dict: 操作结果
    """
    from common.models.strategy import Strategy
    
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise_not_found("Strategy", strategy_id)
    
    strategy.status = 'deleted'
    strategy.updated_at = datetime.utcnow()
    
    db.commit()
    
    logger.info("Strategy deleted", strategy_id=strategy.id)
    
    return {"message": "Strategy deleted successfully"}


@router.post("/{strategy_id}/run")
async def run_strategy(
    strategy_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """
    运行策略 - 实例化策略类、注册到 StrategyManager、启动后台运行
    """
    from common.models.strategy import Strategy, StrategySignal
    from app.engine.manager import strategy_manager
    from strategies.builtin import DualMAStrategy, RSIMeanReversionStrategy, MACDStrategy
    from app.data_client import data_client

    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise_not_found("Strategy", strategy_id)

    if strategy.status != 'active':
        raise_validation_error("策略未激活，无法运行")

    # 策略类映射
    strategy_classes = {
        "dual_ma": DualMAStrategy,
        "rsi_mean_reversion": RSIMeanReversionStrategy,
        "macd": MACDStrategy,
    }
    strategy_class = strategy_classes.get(strategy.type, DualMAStrategy)

    # 实例化策略
    sid = f"S{strategy_id:06d}"
    params = strategy.params or {}
    params.setdefault("code", "600000")
    inst = strategy_class(strategy_id=sid, params=params)
    inst.initialize(params)

    strategy_manager.add_strategy(inst)
    started = await strategy_manager.start(sid)

    if not started:
        raise_strategy_error("策略启动失败", f"无法启动策略 {strategy_id}")

    logger.info("Strategy started", strategy_id=strategy.id, name=strategy.name)
    return {
        "status": "running",
        "strategy_id": strategy_id,
        "instance_id": sid,
        "message": "Strategy started successfully"
    }


@router.post("/{strategy_id}/stop")
async def stop_strategy(
    strategy_id: int,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """停止策略"""
    from common.models.strategy import Strategy
    from app.engine.manager import strategy_manager

    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise_not_found("Strategy", strategy_id)

    sid = f"S{strategy_id:06d}"
    stopped = await strategy_manager.stop(sid)

    logger.info("Strategy stopped", strategy_id=strategy.id, ok=stopped)
    return {
        "status": "stopped",
        "strategy_id": strategy_id,
        "message": "Strategy stopped successfully"
    }


@router.get("/{strategy_id}/signals")
async def get_strategy_signals(
    strategy_id: int,
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    db: Session = Depends(get_db)
):
    """
    获取策略信号
    
    Args:
        strategy_id: 策略ID
        limit: 返回数量
    
    Returns:
        list: 信号列表
    """
    from common.models.strategy import Strategy, StrategySignal
    
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise_not_found("Strategy", strategy_id)
    
    signals = db.query(StrategySignal)\
        .filter(StrategySignal.strategy_id == strategy_id)\
        .order_by(StrategySignal.created_at.desc())\
        .limit(limit)\
        .all()
    
    return [
        {
            "id": s.id,
            "code": s.code,
            "action": s.action,
            "price": s.price,
            "quantity": s.quantity,
            "reason": s.reason,
            "strength": s.strength,
            "created_at": s.created_at.isoformat()
        }
        for s in signals
    ]