"""
回测服务路由
提供回测任务管理、执行和结果查询
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
import pandas as pd
import numpy as np
import io
import csv
import json
import zipfile

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


@router.get("/{backtest_id}/report")
async def get_backtest_report(
    backtest_id: int,
    db: Session = Depends(get_db)
):
    """
    获取完整回测分析报告

    在基础指标之上，计算月度收益矩阵、回撤分析、
    风险指标（波动率、下行波动率、索提诺比率、卡尔玛比率）等。

    Returns:
        dict: 完整回测分析报告
    """
    from common.models.backtest import Backtest, BacktestResult, BacktestTrade, EquityCurve

    backtest = db.query(Backtest).filter(Backtest.id == backtest_id).first()
    if not backtest:
        raise_not_found("Backtest", backtest_id)

    if backtest.status != "completed":
        raise_validation_error("回测未完成")

    result = db.query(BacktestResult).filter(BacktestResult.backtest_id == backtest_id).first()
    trades = db.query(BacktestTrade).filter(BacktestTrade.backtest_id == backtest_id).all()
    equity_rows = db.query(EquityCurve).filter(EquityCurve.backtest_id == backtest_id).order_by(EquityCurve.date.asc()).all()

    metrics = result.__dict__ if result else {}

    # ---------- 月度收益矩阵 ----------
    monthly_matrix = {}
    monthly_series = []
    if equity_rows:
        eq_df = pd.DataFrame([
            {"date": r.date, "equity": r.equity, "cum_return": r.cumulative_return}
            for r in equity_rows
        ])
        eq_df["ym"] = eq_df["date"].dt.strftime("%Y-%m")
        # 每月末累计收益
        month_end = eq_df.groupby("ym").tail(1)
        prev_cum = month_end["cum_return"].shift(1).fillna(0.0)
        month_returns = month_end["cum_return"] - prev_cum
        for ym, r in zip(eq_df["ym"].drop_duplicates(), month_returns):
            year, mon = ym.split("-")
            monthly_matrix.setdefault(year, {})[mon] = round(float(r), 4)
            monthly_series.append({"year": year, "month": mon, "return": round(float(r), 4)})

    # ---------- 回撤分析 ----------
    drawdown_analysis = {}
    if equity_rows:
        equity_vals = [r.equity for r in equity_rows]
        dates_vals = [r.date for r in equity_rows]
        peak = equity_vals[0]
        peak_date = dates_vals[0]
        max_dd = 0.0
        max_dd_start = dates_vals[0].isoformat()
        max_dd_end = dates_vals[0].isoformat()
        current_start = dates_vals[0]
        current_dd = 0.0
        in_drawdown = False
        for i, eq in enumerate(equity_vals):
            if eq >= peak:
                peak = eq
                peak_date = dates_vals[i]
                current_dd = 0.0
                in_drawdown = False
            else:
                dd = (peak - eq) / peak
                if not in_drawdown:
                    current_start = dates_vals[i]
                    in_drawdown = True
                if dd > current_dd:
                    current_dd = dd
                    max_dd = max(max_dd, current_dd)
                    max_dd_start = current_start.isoformat()
                    max_dd_end = dates_vals[i].isoformat()

        # 回撤持续时间（自然日）
        dd_days = 0
        if max_dd > 0:
            try:
                dd_days = (datetime.fromisoformat(max_dd_end) - datetime.fromisoformat(max_dd_start)).days
            except Exception:
                dd_days = 0

        drawdown_analysis = {
            "max_drawdown": round(max_dd, 4),
            "start_date": max_dd_start,
            "end_date": max_dd_end,
            "duration_days": dd_days,
        }

    # ---------- 风险指标 ----------
    risk_metrics = {}
    if equity_rows:
        eq_df = pd.DataFrame([{"date": r.date, "equity": r.equity} for r in equity_rows])
        daily_returns = eq_df["equity"].pct_change().dropna()
        if len(daily_returns) > 1:
            ann_vol = float(daily_returns.std() * np.sqrt(252))
            downside = daily_returns[daily_returns < 0]
            downside_vol = float(downside.std() * np.sqrt(252)) if len(downside) else 0.0
            total_return = (eq_df["equity"].iloc[-1] - eq_df["equity"].iloc[0]) / eq_df["equity"].iloc[0]
            days = (eq_df["date"].iloc[-1] - eq_df["date"].iloc[0]).days
            annual_return = (1 + total_return) ** (365 / max(days, 1)) - 1
            sharpe = float(daily_returns.mean() / daily_returns.std() * np.sqrt(252)) if daily_returns.std() > 0 else 0.0
            sortino = float(daily_returns.mean() / downside.std() * np.sqrt(252)) if downside_vol > 0 else 0.0
            max_dd = metrics.get("max_drawdown") or drawdown_analysis.get("max_drawdown") or 0.0
            calmar = float(annual_return / max_dd) if max_dd else 0.0

            risk_metrics = {
                "annual_volatility": round(ann_vol, 4),
                "downside_volatility": round(downside_vol, 4),
                "sharpe_ratio": round(sharpe, 4),
                "sortino_ratio": round(sortino, 4),
                "calmar_ratio": round(calmar, 4),
            }

    # ---------- 交易统计 ----------
    trade_stats = {}
    if trades:
        buy_trades = [t for t in trades if t.direction == "buy"]
        sell_trades = [t for t in trades if t.direction == "sell"]
        won = [t for t in sell_trades if (t.pnl or 0) > 0]
        lost = [t for t in sell_trades if (t.pnl or 0) <= 0]
        by_code = {}
        for t in trades:
            d = by_code.setdefault(t.code, {"buy": 0, "sell": 0, "pnl": 0.0})
            d[t.direction] = d.get(t.direction, 0) + 1
            d["pnl"] += t.pnl or 0
        trade_stats = {
            "buy_count": len(buy_trades),
            "sell_count": len(sell_trades),
            "won_count": len(won),
            "lost_count": len(lost),
            "win_rate": round(len(won) / len(sell_trades), 4) if sell_trades else 0.0,
            "avg_trade_interval_days": round(days / max(len(trades), 1), 2) if equity_rows and days > 0 else 0.0,
            "by_code": [
                {"code": c, "buy": v["buy"], "sell": v["sell"], "pnl": round(v["pnl"], 2)}
                for c, v in sorted(by_code.items(), key=lambda kv: kv[1]["pnl"], reverse=True)
            ],
        }

    # ---------- 关键指标汇总 ----------
    capability = {}
    if metrics:
        def fmt_metric(v, as_pct=True):
            if v is None:
                return None
            return round(float(v), 4)

        capability = {
            "total_return": fmt_metric(metrics.get("total_return")),
            "annual_return": fmt_metric(metrics.get("annual_return")),
            "sharpe_ratio": fmt_metric(metrics.get("sharpe_ratio"), as_pct=False),
            "max_drawdown": fmt_metric(metrics.get("max_drawdown")),
            "win_rate": fmt_metric(metrics.get("win_rate")),
            "profit_factor": fmt_metric(metrics.get("profit_factor"), as_pct=False),
            "total_trades": metrics.get("total_trades"),
            "start_balance": metrics.get("start_balance"),
            "end_balance": metrics.get("end_balance"),
        }

    return {
        "backtest_id": backtest_id,
        "name": backtest.name,
        "strategy_id": backtest.strategy_id,
        "start_date": backtest.start_date.isoformat(),
        "end_date": backtest.end_date.isoformat(),
        "initial_capital": backtest.initial_capital,
        "commission_rate": backtest.commission_rate,
        "slip_rate": backtest.slip_rate,
        "metrics": capability,
        "risk_metrics": risk_metrics,
        "drawdown_analysis": drawdown_analysis,
        "monthly_returns": {"matrix": monthly_matrix, "series": monthly_series},
        "trade_stats": trade_stats,
        "trades_count": len(trades),
        "equity_points": len(equity_rows),
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get("/{backtest_id}/export-csv")
async def export_backtest_csv(
    backtest_id: int,
    kind: str = Query("trades", description="导出类型：trades/equity"),
    db: Session = Depends(get_db)
):
    """
    导出回测数据为 CSV

    Args:
        backtest_id: 回测ID
        kind: 导出类型（trades/equity）

    Returns:
        StreamingResponse: CSV 文件
    """
    from common.models.backtest import Backtest, BacktestTrade, EquityCurve

    backtest = db.query(Backtest).filter(Backtest.id == backtest_id).first()
    if not backtest:
        raise_not_found("Backtest", backtest_id)

    buffer = io.StringIO()

    if kind == "equity":
        rows = db.query(EquityCurve).filter(EquityCurve.backtest_id == backtest_id).order_by(EquityCurve.date.asc()).all()
        writer = csv.writer(buffer)
        writer.writerow(["date", "equity", "cumulative_return", "drawdown"])
        for r in rows:
            writer.writerow([
                r.date.isoformat(),
                round(r.equity or 0, 4),
                round(r.cumulative_return or 0, 6),
                round(r.drawdown or 0, 6),
            ])
        filename = f"backtest_{backtest_id}_equity.csv"
    else:
        rows = db.query(BacktestTrade).filter(BacktestTrade.backtest_id == backtest_id).order_by(BacktestTrade.date.asc()).all()
        writer = csv.writer(buffer)
        writer.writerow(["code", "date", "direction", "price", "quantity", "commission", "slip", "pnl"])
        for r in rows:
            writer.writerow([
                r.code,
                r.date.isoformat(),
                r.direction,
                round(r.price or 0, 4),
                r.quantity,
                round(r.commission or 0, 4),
                round(r.slip or 0, 4),
                round(r.pnl or 0, 4),
            ])
        filename = f"backtest_{backtest_id}_trades.csv"

    buffer.seek(0)
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers=headers,
    )


@router.get("/{backtest_id}/export-report")
async def export_backtest_report(
    backtest_id: int,
    db: Session = Depends(get_db)
):
    """
    导出完整回测报告（ZIP）

    打包指标 JSON + 月度收益 + 交易明细 + 权益曲线。

    Returns:
        StreamingResponse: ZIP 文件
    """
    from common.models.backtest import Backtest, BacktestResult, BacktestTrade, EquityCurve

    backtest = db.query(Backtest).filter(Backtest.id == backtest_id).first()
    if not backtest:
        raise_not_found("Backtest", backtest_id)

    # 复用 report 计算
    report = await get_backtest_report(backtest_id, db)

    result = db.query(BacktestResult).filter(BacktestResult.backtest_id == backtest_id).first()
    trades = db.query(BacktestTrade).filter(BacktestTrade.backtest_id == backtest_id).all()
    equity_rows = db.query(EquityCurve).filter(EquityCurve.backtest_id == backtest_id).order_by(EquityCurve.date.asc()).all()

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("report_summary.json", json.dumps(report, ensure_ascii=False, indent=2, default=str))

        metrics_buf = io.StringIO()
        if result:
            md = result.__dict__
            for k in list(md.keys()):
                if k.startswith("_"):
                    del md[k]
            metrics_buf.write(json.dumps(md, ensure_ascii=False, indent=2, default=str))
        else:
            metrics_buf.write("{}")
        zf.writestr("metrics.json", metrics_buf.getvalue())

        trades_buf = io.StringIO()
        w = csv.writer(trades_buf)
        w.writerow(["code", "date", "direction", "price", "quantity", "commission", "slip", "pnl"])
        for r in trades:
            w.writerow([r.code, r.date.isoformat(), r.direction, round(r.price or 0, 4),
                        r.quantity, round(r.commission or 0, 4), round(r.slip or 0, 4), round(r.pnl or 0, 4)])
        zf.writestr("trades.csv", trades_buf.getvalue())

        equity_buf = io.StringIO()
        w = csv.writer(equity_buf)
        w.writerow(["date", "equity", "cumulative_return", "drawdown"])
        for r in equity_rows:
            w.writerow([r.date.isoformat(), round(r.equity or 0, 4),
                        round(r.cumulative_return or 0, 6), round(r.drawdown or 0, 6)])
        zf.writestr("equity_curve.csv", equity_buf.getvalue())

    zip_buffer.seek(0)
    filename = f"backtest_{backtest_id}_report.zip"
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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