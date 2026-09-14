"""
交易服务路由
提供订单管理、成交查询、持仓管理等功能
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from common import (
    get_db,
    get_logger,
    OrderCreateRequest,
    OrderQueryRequest,
    OrderResponse,
    PaginationRequest,
    PaginationResponse,
    raise_not_found,
    raise_validation_error,
    raise_trading_error,
    get_current_user,
    AuthUser,
)
from app.engine import (
    trading_engine,
    OrderDirection,
    OrderType,
    OrderStatus,
)

router = APIRouter()
logger = get_logger("trading-service")


@router.post("/order", response_model=OrderResponse, status_code=201)
async def create_order(
    request: OrderCreateRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """
    创建订单
    
    Args:
        request: 订单创建请求
    
    Returns:
        OrderResponse: 创建的订单
    """
    try:
        # 创建订单
        order = trading_engine.create_order(
            code=request.code,
            direction=OrderDirection(request.direction.value),
            order_type=OrderType(request.order_type.value),
            price=request.price,
            quantity=request.quantity,
            strategy_id=request.strategy_id,
        )
        
        # 提交订单
        success = await trading_engine.submit_order(order.order_id)
        
        if not success:
            raise_trading_error("订单提交失败", order.reject_reason)
        
        logger.info("Order created", order_id=order.order_id, code=order.code)
        
        return OrderResponse(
            id=0,
            order_no=order.order_id,
            strategy_id=order.strategy_id,
            code=order.code,
            direction=order.direction,
            order_type=order.order_type,
            price=order.price,
            quantity=order.quantity,
            filled_quantity=order.filled_quantity,
            avg_price=order.avg_price,
            status=order.status,
            submit_time=order.submit_time or order.create_time,
            update_time=order.update_time,
            filled_time=order.filled_time,
            reject_reason=order.reject_reason,
        )
        
    except ValueError as e:
        raise_validation_error(str(e))
    except Exception as e:
        logger.error("Failed to create order", error=str(e))
        raise_trading_error("创建订单失败", str(e))


@router.get("/orders", response_model=List[OrderResponse])
async def list_orders(
    code: Optional[str] = Query(None, description="股票代码"),
    direction: Optional[str] = Query(None, description="交易方向"),
    status: Optional[str] = Query(None, description="订单状态"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
):
    """
    获取订单列表
    
    Returns:
        List[OrderResponse]: 订单列表
    """
    # 转换参数
    dir_enum = OrderDirection(direction) if direction else None
    status_enum = OrderStatus(status) if status else None
    
    # 获取订单列表
    orders = trading_engine.get_orders(
        code=code,
        direction=dir_enum,
        status=status_enum,
        limit=limit,
    )
    
    return [
        OrderResponse(
            id=0,
            order_no=o.order_id,
            strategy_id=o.strategy_id,
            code=o.code,
            direction=o.direction,
            order_type=o.order_type,
            price=o.price,
            quantity=o.quantity,
            filled_quantity=o.filled_quantity,
            avg_price=o.avg_price,
            status=o.status,
            submit_time=o.submit_time or o.create_time,
            update_time=o.update_time,
            filled_time=o.filled_time,
            reject_reason=o.reject_reason,
        )
        for o in orders
    ]


@router.get("/order/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
):
    """
    获取订单详情
    
    Args:
        order_id: 订单ID
    
    Returns:
        OrderResponse: 订单详情
    """
    order = trading_engine.get_order(order_id)
    if not order:
        raise_not_found("Order", order_id)
    
    return OrderResponse(
        id=0,
        order_no=order.order_id,
        strategy_id=order.strategy_id,
        code=order.code,
        direction=order.direction,
        order_type=order.order_type,
        price=order.price,
        quantity=order.quantity,
        filled_quantity=order.filled_quantity,
        avg_price=order.avg_price,
        status=order.status,
        submit_time=order.submit_time or order.create_time,
        update_time=order.update_time,
        filled_time=order.filled_time,
        reject_reason=order.reject_reason,
    )


@router.post("/order/{order_id}/cancel")
async def cancel_order(
    order_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    取消订单
    
    Args:
        order_id: 订单ID
    
    Returns:
        dict: 取消结果
    """
    success = await trading_engine.cancel_order(order_id)
    
    if not success:
        raise_trading_error("取消订单失败", f"订单 {order_id} 无法取消")
    
    logger.info("Order cancelled", order_id=order_id)
    
    return {
        "status": "cancelled",
        "order_id": order_id,
        "message": "订单已取消"
    }


@router.get("/trades")
async def list_trades(
    code: Optional[str] = Query(None, description="股票代码"),
    direction: Optional[str] = Query(None, description="交易方向"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
):
    """
    获取成交列表
    
    Returns:
        list: 成交列表
    """
    dir_enum = OrderDirection(direction) if direction else None
    
    trades = trading_engine.get_trades(
        code=code,
        direction=dir_enum,
        limit=limit,
    )
    
    return [t.to_dict() for t in trades]


@router.get("/positions")
async def get_positions():
    """
    获取持仓列表
    
    Returns:
        dict: 持仓列表
    """
    positions = trading_engine.get_positions()
    
    return {
        "positions": positions,
        "count": len(positions),
    }


@router.get("/position/{code}")
async def get_position(
    code: str,
):
    """
    获取单只股票持仓
    
    Args:
        code: 股票代码
    
    Returns:
        dict: 持仓信息
    """
    position = trading_engine.get_position(code)
    if not position:
        raise_not_found("Position", code)
    
    return position


@router.get("/capital")
async def get_capital():
    """
    获取可用资金
    
    Returns:
        dict: 资金信息
    """
    return {
        "capital": trading_engine.get_capital(),
    }


@router.get("/stats")
async def get_stats():
    """
    获取交易统计
    
    Returns:
        dict: 统计信息
    """
    return trading_engine.get_stats()


@router.get("/status")
async def get_status():
    """
    获取交易服务状态
    
    Returns:
        dict: 状态信息
    """
    return {
        "status": "running",
        "mode": "simulation",
        "initialized": trading_engine._initialized,
        "stats": trading_engine.get_stats(),
    }


@router.get("/health")
async def health_check():
    """健康检查"""
    from datetime import datetime
    return {
        "status": "healthy",
        "service": "trading-service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }