"""
回测服务路由
提供回测任务管理、执行和结果查询
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
import pandas as pd

from common import (
    get_db,
    get_logger,
    BacktestCreateRequest,
    BacktestResponse,
    PaginationRequest,
    PaginationResponse,
    raise_not_found,
    raise_validation_error,
    raise_backtest_error,
    get_current_user,
    AuthUser,
)
from app.engine import BacktestEngine, BacktestConfig, backtest_runner

router = APIRouter()
logger = get_logger("backtest-service")


@router.get("/", response_model=PaginationResponse)
async def list_backtests(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="回测状态"),
    db: Session = Depends(get_db)
):
    """
    获取回测列表
    
    Returns:
        PaginationResponse: 分页回测列表
    """
    from common.models.backtest import Backtest
    
    query = db.query(Backtest)
    
    if status:
        query = query.filter(Backtest.status == status)
    
    total = query.count()
    backtests = query.order_by(Backtest.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()
    
    return PaginationResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[BacktestResponse.model_validate(b) for b in backtests]
    )


@router.get("/{backtest_id}", response_model=BacktestResponse)
async def get_backtest(
    backtest_id: int,
    db: Session = Depends(get_db)
):
    """
    获取回测详情
    
    Args:
        backtest_id: 回测ID
    
    Returns:
        BacktestResponse: 回测详情
    """
    from common.models.backtest import Backtest
    
    backtest = db.query(Backtest).filter(Backtest.id == backtest_id).first()
    if not backtest:
        raise_not_found("Backtest", backtest_id)
    
    return BacktestResponse.model_validate(backtest)


@router.post("/", response_model=BacktestResponse, status_code=201)
async def create_backtest(
    request: BacktestCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """
    创建回测任务
    
    Args:
        request: 回测创建请求
    
    Returns:
        BacktestResponse: 创建的回测
    """
    from common.models.backtest import Backtest
    
    # 验证策略是否存在
    from common.models.strategy import Strategy
    strategy = db.query(Strategy).filter(Strategy.id == request.strategy_id).first()
    if not strategy:
        raise_validation_error(f"策略 {request.strategy_id} 不存在")
    
    # 创建回测记录
    backtest = Backtest(
        name=request.name,
        strategy_id=request.strategy_id,
        code_list=request.code_list,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_capital=request.initial_capital,
        commission_rate=request.commission_rate,
        slip_rate=request.slip_rate,
        status="pending",
        params=request.params,
    )
    
    db.add(backtest)
    db.commit()
    db.refresh(backtest)
    
    logger.info("Backtest created", backtest_id=backtest.id, name=backtest.name)
    
    # 后台执行回测
    background_tasks.add_task(
        execute_backtest_task,
        backtest_id=backtest.id,
        strategy_id=request.strategy_id,
        strategy_type=strategy.type,
        strategy_params=strategy.params,
        code_list=request.code_list,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_capital=request.initial_capital,
        commission_rate=request.commission_rate,
        slip_rate=request.slip_rate,
    )
    
    return BacktestResponse.model_validate(backtest)


@router.post("/{backtest_id}/run")
async def run_backtest(
    backtest_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    """
    运行回测
    
    Args:
        backtest_id: 回测ID
    
    Returns:
        dict: 运行状态
    """
    from common.models.backtest import Backtest
    from common.models.strategy import Strategy
    
    backtest = db.query(Backtest).filter(Backtest.id == backtest_id).first()
    if not backtest:
        raise_not_found("Backtest", backtest_id)
    
    if backtest.status == "running":
        raise_validation_error("回测正在运行中")
    
    strategy = db.query(Strategy).filter(Strategy.id == backtest.strategy_id).first()
    if not strategy:
        raise_validation_error("关联策略不存在")
    
    # 更新状态
    backtest.status = "running"
    backtest.progress = 0
    db.commit()
    
    # 后台执行回测
    background_tasks.add_task(
        execute_backtest_task,
        backtest_id=backtest.id,
        strategy_id=backtest.strategy_id,
        strategy_type=strategy.type,
        strategy_params=strategy.params,
        code_list=backtest.code_list,
        start_date=backtest.start_date,
        end_date=backtest.end_date,
        initial_capital=backtest.initial_capital,
        commission_rate=backtest.commission_rate,
        slip_rate=backtest.slip_rate,
    )
    
    logger.info("Backtest started", backtest_id=backtest_id)
    
    return {
        "status": "running",
        "backtest_id": backtest_id,
        "message": "回测已开始运行"
    }


@router.post("/{backtest_id}/stop")
async def stop_backtest(
    backtest_id: int,
    db: Session = Depends(get_db)
):
    """
    停止回测
    
    Args:
        backtest_id: 回测ID
    
    Returns:
        dict: 停止状态
    """
    from common.models.backtest import Backtest
    
    backtest = db.query(Backtest).filter(Backtest.id == backtest_id).first()
    if not backtest:
        raise_not_found("Backtest", backtest_id)
    
    if backtest.status != "running":
        raise_validation_error("回测未在运行中")
    
    # 停止回测
    backtest_runner.stop_backtest(str(backtest_id))
    
    # 更新状态
    backtest.status = "stopped"
    db.commit()
    
    logger.info("Backtest stopped", backtest_id=backtest_id)
    
    return {
        "status": "stopped",
        "backtest_id": backtest_id,
        "message": "回测已停止"
    }


@router.get("/{backtest_id}/result")
async def get_backtest_result(
    backtest_id: int,
    db: Session = Depends(get_db)
):
    """
    获取回测结果
    
    Args:
        backtest_id: 回测ID
    
    Returns:
        dict: 回测结果
    """
    from common.models.backtest import Backtest, BacktestResult, BacktestTrade, EquityCurve
    
    backtest = db.query(Backtest).filter(Backtest.id == backtest_id).first()
    if not backtest:
        raise_not_found("Backtest", backtest_id)
    
    if backtest.status != "completed":
        raise_validation_error("回测未完成")
    
    # 获取回测结果
    result = db.query(BacktestResult).filter(BacktestResult.backtest_id == backtest_id).first()
    trades = db.query(BacktestTrade).filter(BacktestTrade.backtest_id == backtest_id).all()
    equity_curve = db.query(EquityCurve).filter(EquityCurve.backtest_id == backtest_id).all()
    
    return {
        "backtest_id": backtest_id,
        "status": backtest.status,
        "metrics": result.__dict__ if result else {},
        "trades": [t.__dict__ for t in trades],
        "equity_curve": [e.__dict__ for e in equity_curve],
    }


@router.get("/{backtest_id}/status")
async def get_backtest_status(
    backtest_id: int,
    db: Session = Depends(get_db)
):
    """
    获取回测状态
    
    Args:
        backtest_id: 回测ID
    
    Returns:
        dict: 回测状态
    """
    from common.models.backtest import Backtest
    
    backtest = db.query(Backtest).filter(Backtest.id == backtest_id).first()
    if not backtest:
        raise_not_found("Backtest", backtest_id)
    
    # 获取运行状态
    runner_status = backtest_runner.get_backtest_status(str(backtest_id))
    
    return {
        "backtest_id": backtest_id,
        "status": backtest.status,
        "progress": backtest.progress,
        "is_running": runner_status["is_running"],
    }


async def execute_backtest_task(
    backtest_id: int,
    strategy_id: int,
    strategy_type: str,
    strategy_params: dict,
    code_list: list,
    start_date: date,
    end_date: date,
    initial_capital: float,
    commission_rate: float,
    slip_rate: float,
):
    """
    后台执行回测任务 - 通过 HTTP 调用 data-service 获取真实 K 线数据
    """
    from common.database import SessionLocal
    from common.models.backtest import Backtest, BacktestResult, BacktestTrade, EquityCurve
    import httpx
    
    db = SessionLocal()
    
    try:
        # 更新状态为运行中
        backtest = db.query(Backtest).filter(Backtest.id == backtest_id).first()
        if backtest:
            backtest.status = "running"
            backtest.progress = 0
            db.commit()
        
        # 创建回测配置
        config = BacktestConfig(
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            commission_rate=commission_rate,
            slippage_rate=slip_rate,
        )
        
        # 通过 httpx 异步调用 data-service 获取真实 K 线数据
        all_data = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for code in code_list:
                try:
                    resp = await client.get(
                        f"http://data-service:8006/api/v1/market/kline/{code}",
                        params={
                            "start_date": start_date.isoformat(),
                            "end_date": end_date.isoformat(),
                            "interval": "1d",
                            "provider": "mock",
                        },
                    )
                    if resp.status_code != 200:
                        logger.warning(f"Failed to fetch kline for {code}: {resp.status_code} {resp.text}")
                        continue
                    klines = resp.json()
                    for k in klines:
                        # data-service 返回 KLine 字段：code/date/open/high/low/close/volume
                        kdate = k.get("date")
                        if isinstance(kdate, str):
                            try:
                                ts = pd.to_datetime(kdate)
                            except Exception:
                                continue
                        else:
                            ts = pd.to_datetime(kdate)
                        all_data.append({
                            "code": k.get("code", code),
                            "timestamp": ts,
                            "open": float(k.get("open", 0)),
                            "high": float(k.get("high", 0)),
                            "low": float(k.get("low", 0)),
                            "close": float(k.get("close", 0)),
                            "volume": int(k.get("volume", 0) or 0),
                        })
                except Exception as e:
                    logger.error(f"Error fetching kline for {code}: {e}")
                    continue
        
        if not all_data:
            backtest = db.query(Backtest).filter(Backtest.id == backtest_id).first()
            if backtest:
                backtest.status = "failed"
                backtest.error_msg = "无法获取市场数据"
                db.commit()
            return
        
        market_data = pd.DataFrame(all_data)
        
        # 获取策略类
        from strategies.builtin import DualMAStrategy, RSIMeanReversionStrategy, MACDStrategy
        
        strategy_classes = {
            "dual_ma": DualMAStrategy,
            "rsi_mean_reversion": RSIMeanReversionStrategy,
            "macd": MACDStrategy,
        }
        
        strategy_class = strategy_classes.get(strategy_type, DualMAStrategy)
        
        # 运行回测
        result = await backtest_runner.run_backtest(
            backtest_id=str(backtest_id),
            strategy_class=strategy_class,
            strategy_params=strategy_params,
            config=config,
            market_data=market_data,
        )
        
        # 保存结果
        if result["status"] == "completed":
            # 保存回测结果
            metrics = result["metrics"]
            backtest_result = BacktestResult(
                backtest_id=backtest_id,
                total_return=metrics.get("total_return"),
                annual_return=metrics.get("annual_return"),
                sharpe_ratio=metrics.get("sharpe_ratio"),
                max_drawdown=metrics.get("max_drawdown"),
                max_drawdown_duration=metrics.get("max_drawdown_duration"),
                win_rate=metrics.get("win_rate"),
                profit_factor=metrics.get("profit_factor"),
                avg_win=metrics.get("avg_win"),
                avg_loss=metrics.get("avg_loss"),
                largest_win=metrics.get("largest_win"),
                largest_loss=metrics.get("largest_loss"),
                total_trades=metrics.get("total_trades"),
                winning_trades=metrics.get("winning_trades"),
                losing_trades=metrics.get("losing_trades"),
                start_balance=metrics.get("start_balance"),
                end_balance=metrics.get("end_balance"),
            )
            db.add(backtest_result)
            
            # 保存交易记录
            for trade in result.get("trades", []):
                backtest_trade = BacktestTrade(
                    backtest_id=backtest_id,
                    code=trade["code"],
                    date=datetime.fromisoformat(trade["timestamp"].replace("Z", "+00:00")),
                    direction=trade["direction"],
                    price=trade["price"],
                    quantity=trade["quantity"],
                    commission=trade["commission"],
                    slip=trade["slippage"],
                    pnl=trade["pnl"],
                )
                db.add(backtest_trade)
            
            # 保存权益曲线
            for point in result.get("equity_curve", []):
                equity_point = EquityCurve(
                    backtest_id=backtest_id,
                    date=datetime.fromisoformat(point["timestamp"].replace("Z", "+00:00")),
                    equity=point["equity"],
                    cumulative_return=(point["equity"] - initial_capital) / initial_capital,
                )
                db.add(equity_point)
            
            # 更新回测状态
            backtest.status = "completed"
            backtest.progress = 100
            backtest.completed_at = datetime.utcnow()
            
        else:
            # 回测失败
            backtest.status = "failed"
            backtest.error_msg = result.get("error", "Unknown error")
        
        db.commit()
        
        logger.info(f"Backtest {backtest_id} completed with status: {result['status']}")
        
    except Exception as e:
        logger.error(f"Backtest task failed: {e}")
        
        # 更新状态为失败
        backtest = db.query(Backtest).filter(Backtest.id == backtest_id).first()
        if backtest:
            backtest.status = "failed"
            backtest.error_msg = str(e)
            db.commit()
    
    finally:
        db.close()