"""
组合持久化：账户/持仓/流水 双写 DB 及启动时恢复
"""
import logging
from datetime import datetime

from common import SessionLocal, get_logger
from common.models.portfolio import (
    Position as PositionRow,
    Account as AccountRow,
    AccountLog as AccountLogRow,
    PositionDirection as PositionDirectionRow,
    PositionStatus as PositionStatusRow,
)

from app.engine import PositionDirection, PositionStatus

logger = get_logger("portfolio-service")

DEFAULT_ACCOUNT_NO = "DEFAULT-001"
DEFAULT_ACCOUNT_TYPE = "cash"
DEFAULT_ACCOUNT_STATUS = "active"

DEFAULT_POSITION_DIRECTION = PositionDirection.LONG
DEFAULT_POSITION_STATUS = PositionStatus.ACTIVE


def save_state(engine, db_factory=SessionLocal):
    """把引擎当前账户/持仓/流水写库（账户与持仓 UPSERT，新增流水去重追加）"""
    db = db_factory()
    try:
        account = engine.get_account()
        acc = db.query(AccountRow).filter_by(account_no=account.account_no).first()
        if acc is None:
            acc = AccountRow(account_no=account.account_no)
            db.add(acc)
        acc.account_type = account.account_type or DEFAULT_ACCOUNT_TYPE
        acc.balance = account.balance or 0.0
        acc.frozen_balance = account.frozen_balance or 0.0
        acc.total_deposited = account.total_deposited or 0.0
        acc.total_withdrawn = account.total_withdrawn or 0.0
        acc.total_profit = account.total_profit or 0.0
        acc.status = account.status or DEFAULT_ACCOUNT_STATUS
        db.flush()

        for pos in engine.get_positions():
            prow = db.query(PositionRow).filter_by(
                code=pos.code, status=pos.status.value
            ).first()
            if prow is None:
                prow = PositionRow(code=pos.code, status=pos.status.value)
                db.add(prow)
            prow.name = pos.name or ""
            prow.direction = pos.direction.value
            prow.quantity = int(pos.quantity)
            prow.avg_cost = pos.avg_cost
            prow.avg_price = pos.avg_price
            prow.current_price = pos.current_price
            prow.frozen_quantity = int(pos.frozen_quantity)
            prow.updated_at = pos.updated_at or datetime.now()
            prow.extra = {
                "realized_pnl": pos.realized_pnl,
                "total_buy_amount": pos.total_buy_amount,
                "total_sell_amount": pos.total_sell_amount,
                "total_commission": pos.total_commission,
                "total_tax": pos.total_tax,
            }

        # 追加新流水（按 related_order_no + type + amount 判重）
        existing = {
            (r.account_no, r.related_order_no, r.type, r.amount)
            for r in db.query(AccountLogRow).filter_by(account_no=account.account_no).all()
        }
        for log in engine.get_logs(limit=100000):
            key = (log.account_no, log.related_order_no, log.type, log.amount)
            if key in existing:
                continue
            db.add(AccountLogRow(
                account_no=log.account_no,
                type=log.type,
                amount=log.amount,
                balance_after=log.balance_after,
                description=log.description,
                related_order_no=log.related_order_no,
                created_at=log.created_at or datetime.now(),
            ))
        db.commit()
        logger.info("Portfolio state saved", account=account.account_no)
    finally:
        db.close()


def load_state(engine, db_factory=SessionLocal):
    """启动时/测试时从 DB 恢复账户与持仓"""
    from app.engine import Position, Account, AccountLog, PositionDirection, PositionStatus

    db = db_factory()
    try:
        acc = db.query(AccountRow).filter_by(account_no=DEFAULT_ACCOUNT_NO).first()
        pos_rows = db.query(PositionRow).all()
    finally:
        db.close()

    if acc is not None:
        from common.models.portfolio import Account as AccountRowModel

        engine._account = Account(
            account_no=acc.account_no,
            account_type=acc.account_type or DEFAULT_ACCOUNT_TYPE,
            balance=acc.balance or 0.0,
            frozen_balance=acc.frozen_balance or 0.0,
            total_deposited=acc.total_deposited or 0.0,
            total_withdrawn=acc.total_withdrawn or 0.0,
            total_profit=acc.total_profit or 0.0,
            status=acc.status or DEFAULT_ACCOUNT_STATUS,
        )
        engine._initial_capital = engine._account.balance + (engine._account.total_withdrawn or 0)
    else:
        from app.engine import Account as EngineAccount

        engine._account = EngineAccount(
            account_no=DEFAULT_ACCOUNT_NO,
            balance=engine._initial_capital,
            total_deposited=engine._initial_capital,
        )

    for p in pos_rows:
        pos = Position(
            code=p.code,
            name=p.name or "",
            direction=PositionDirection(p.direction.value),
            quantity=int(p.quantity or 0),
            avg_cost=p.avg_cost or 0.0,
            avg_price=p.avg_price or 0.0,
            current_price=p.current_price or 0.0,
            frozen_quantity=int(p.frozen_quantity or 0),
            status=PositionStatus(p.status.value),
            created_at=p.created_at or datetime.now(),
            updated_at=p.updated_at or datetime.now(),
            closed_at=p.closed_at,
        )
        extra = p.extra or {}
        pos.realized_pnl = float(extra.get("realized_pnl", 0.0))
        pos.total_buy_amount = float(extra.get("total_buy_amount", 0.0))
        pos.total_sell_amount = float(extra.get("total_sell_amount", 0.0))
        pos.total_commission = float(extra.get("total_commission", 0.0))
        pos.total_tax = float(extra.get("total_tax", 0.0))
        engine._positions[p.code] = pos
    engine._initialized = True
    engine._running = True
    logger.info("Portfolio engine restored from DB", positions=len(pos_rows))
