"""
风控服务路由
提供风险检查、限额管理、风险监控等功能
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from collections import Counter

from common import (
    get_db,
    get_logger,
    RiskLimitCreateRequest,
    RiskCheckRequest,
    RiskLimitResponse,
    PaginationRequest,
    PaginationResponse,
    raise_not_found,
    raise_validation_error,
    raise_risk_error,
    get_current_user,
    get_optional_user,
    AuthUser,
)
from app.engine import (
    risk_engine,
    RiskType,
    RiskLevel,
    RiskLimit,
)

router = APIRouter()
logger = get_logger("risk-service")


@router.get("/dashboard")
async def get_risk_dashboard(user: AuthUser = Depends(get_current_user)):
    """
    风控仪表盘
    限额概况 + 预警统计 + 预警分布 + 风控检查统计
    """
    limits = risk_engine.get_limits()
    alerts = risk_engine.get_alerts(limit=500)
    stats = risk_engine.get_stats()

    # 限额概况
    limit_summary = {
        "total": len(limits),
        "enabled": len([l for l in limits if l.enabled]),
        "disabled": len([l for l in limits if not l.enabled]),
        "types": list(set(l.risk_type.value for l in limits)),
    }

    # 预警统计
    alert_stats = {
        "total": stats["total_alerts"],
        "by_level": dict(Counter(a.level.value for a in alerts)),
        "by_type": dict(Counter(a.risk_type.value for a in alerts)),
    }

    # 最近预警
    recent_alerts = [a.to_dict() for a in alerts[:20]]

    # 检查统计
    check_stats = {
        "total": stats["total_checks"],
        "blocked": stats["blocked_checks"],
        "pass_rate": (1 - stats["blocked_checks"] / stats["total_checks"]) * 100 if stats["total_checks"] > 0 else 100,
    }

    # 风险类型分布
    risk_type_dist = {}
    for lt in RiskType:
        count = len([l for l in limits if l.risk_type == lt])
        if count > 0:
            risk_type_dist[lt.value] = count

    return {
        "limit_summary": limit_summary,
        "alert_stats": alert_stats,
        "recent_alerts": recent_alerts,
        "check_stats": check_stats,
        "risk_type_distribution": risk_type_dist,
    }


@router.post("/check")
async def check_risk(
    request: RiskCheckRequest,
    total_capital: float = Query(100000, description="总资金"),
    current_user: Optional[AuthUser] = Depends(get_optional_user),
):
    """
    风控检查
    
    Args:
        request: 风控检查请求
        total_capital: 总资金
    
    Returns:
        dict: 风控检查结果
    """
    try:
        # 检查持仓限额
        position_result = risk_engine.check_position_limit(
            code=request.code,
            quantity=request.quantity,
            price=request.price,
            total_capital=total_capital,
            current_positions={},
        )
        
        # 检查单笔交易限额
        trade_result = risk_engine.check_single_trade_limit(
            code=request.code,
            quantity=request.quantity,
            price=request.price,
            total_capital=total_capital,
        )
        
        # 汇总结果
        all_passed = position_result.passed and trade_result.passed
        overall_level = RiskLevel.NORMAL
        
        if not all_passed:
            overall_level = RiskLevel.BLOCKED
        elif position_result.level == RiskLevel.WARNING or trade_result.level == RiskLevel.WARNING:
            overall_level = RiskLevel.WARNING
        
        return {
            "passed": all_passed,
            "level": overall_level.value,
            "checks": [
                position_result.to_dict(),
                trade_result.to_dict(),
            ],
            "message": "风控检查通过" if all_passed else "风控检查未通过",
        }
        
    except Exception as e:
        logger.error("Risk check failed", error=str(e))
        raise_risk_error("风控检查失败", str(e))


@router.get("/limits", response_model=List[RiskLimitResponse])
async def get_limits(
    risk_type: Optional[str] = Query(None, description="风险类型"),
    enabled: Optional[bool] = Query(None, description="是否启用"),
):
    """
    获取风控限额列表
    
    Returns:
        List[RiskLimitResponse]: 限额列表
    """
    limits = risk_engine.get_limits()
    
    if risk_type:
        limits = [l for l in limits if l.risk_type.value == risk_type]
    if enabled is not None:
        limits = [l for l in limits if l.enabled == enabled]
    
    return [
        RiskLimitResponse(
            id=0,
            limit_name=l.limit_name,
            risk_type=l.risk_type,
            limit_value=l.limit_value,
            warning_value=l.warning_value,
            description=l.description,
            enabled=l.enabled,
            updated_at=l.update_time,
        )
        for l in limits
    ]


@router.post("/limits", response_model=RiskLimitResponse, status_code=201)
async def create_limit(
    request: RiskLimitCreateRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    创建风控限额
    
    Args:
        request: 限额创建请求
    
    Returns:
        RiskLimitResponse: 创建的限额
    """
    import uuid
    
    limit = RiskLimit(
        limit_id=str(uuid.uuid4()),
        limit_name=request.limit_name,
        risk_type=request.risk_type,
        limit_value=request.limit_value,
        warning_value=request.warning_value,
        description=request.description,
        enabled=request.enabled,
    )
    
    risk_engine.add_limit(limit)
    
    logger.info("Risk limit created", limit_id=limit.limit_id, name=limit.limit_name)
    
    return RiskLimitResponse(
        id=0,
        limit_name=limit.limit_name,
        risk_type=limit.risk_type,
        limit_value=limit.limit_value,
        warning_value=limit.warning_value,
        description=limit.description,
        enabled=limit.enabled,
        updated_at=limit.update_time,
    )


@router.put("/limits/{limit_id}", response_model=RiskLimitResponse)
async def update_limit(
    limit_id: str,
    updates: dict,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    更新风控限额
    
    Args:
        limit_id: 限额ID
        updates: 更新数据
    
    Returns:
        RiskLimitResponse: 更新后的限额
    """
    success = risk_engine.update_limit(limit_id, updates)
    
    if not success:
        raise_not_found("RiskLimit", limit_id)
    
    limit = risk_engine.get_limit(limit_id)
    
    logger.info("Risk limit updated", limit_id=limit_id)
    
    return RiskLimitResponse(
        id=0,
        limit_name=limit.limit_name,
        risk_type=limit.risk_type,
        limit_value=limit.limit_value,
        warning_value=limit.warning_value,
        description=limit.description,
        enabled=limit.enabled,
        updated_at=limit.update_time,
    )


@router.delete("/limits/{limit_id}")
async def delete_limit(
    limit_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    删除风控限额
    
    Args:
        limit_id: 限额ID
    
    Returns:
        dict: 删除结果
    """
    success = risk_engine.remove_limit(limit_id)
    
    if not success:
        raise_not_found("RiskLimit", limit_id)
    
    logger.info("Risk limit deleted", limit_id=limit_id)
    
    return {
        "status": "deleted",
        "limit_id": limit_id,
        "message": "限额已删除"
    }


@router.get("/alerts")
async def get_alerts(
    risk_type: Optional[str] = Query(None, description="风险类型"),
    level: Optional[str] = Query(None, description="风险等级"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
):
    """
    获取风险预警列表
    
    Returns:
        list: 预警列表
    """
    risk_type_enum = RiskType(risk_type) if risk_type else None
    level_enum = RiskLevel(level) if level else None
    
    alerts = risk_engine.get_alerts(
        risk_type=risk_type_enum,
        level=level_enum,
        limit=limit,
    )
    
    return [a.to_dict() for a in alerts]


@router.get("/checks")
async def get_check_history(
    risk_type: Optional[str] = Query(None, description="风险类型"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
):
    """
    获取风控检查历史
    
    Returns:
        list: 检查历史
    """
    risk_type_enum = RiskType(risk_type) if risk_type else None
    
    history = risk_engine.get_check_history(
        risk_type=risk_type_enum,
        limit=limit,
    )
    
    return [h.to_dict() for h in history]


@router.post("/var")
async def calculate_var(
    returns: List[float],
    confidence: float = Query(0.95, description="置信水平"),
    period: int = Query(1, description="持有期"),
):
    """
    计算VaR
    
    Args:
        returns: 收益率序列
        confidence: 置信水平
        period: 持有期
    
    Returns:
        dict: VaR计算结果
    """
    var = risk_engine.calculate_var(returns, confidence, period)
    
    return {
        "var": var,
        "confidence": confidence,
        "period": period,
    }


@router.get("/stats")
async def get_stats():
    """
    获取风控统计
    
    Returns:
        dict: 统计信息
    """
    return risk_engine.get_stats()


@router.get("/status")
async def get_status():
    """
    获取风控服务状态
    
    Returns:
        dict: 状态信息
    """
    return {
        "status": "running",
        "initialized": risk_engine._initialized,
        "stats": risk_engine.get_stats(),
    }


@router.get("/health")
async def health_check():
    """健康检查"""
    from datetime import datetime
    return {
        "status": "healthy",
        "service": "risk-service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }