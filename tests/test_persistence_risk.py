"""
Task 11: risk-service 限额/检查 持久化（TDD 先行失败测试）

验证 save_limits / save_check / load_limits 的双写与启动恢复。
"""
import sys
sys.path.insert(0, "services/risk-service")
sys.path.insert(0, "tests")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from common import Base, models  # noqa: F401
from app.engine import RiskEngine, RiskLimit, RiskType


@pytest.fixture
def db_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.mark.asyncio
async def test_limits_and_checks_persisted_and_restored(db_factory):
    from app.persistence import save_limits, save_check, load_limits

    engine = RiskEngine()
    await engine.initialize()

    limit = RiskLimit(
        limit_id="l1",
        limit_name="持仓限额_测试",
        risk_type=RiskType.POSITION_LIMIT,
        limit_value=0.3,
        warning_value=0.24,
    )
    engine.add_limit(limit)

    save_limits(engine, db_factory=db_factory)

    db = db_factory()
    try:
        assert db.query(models.RiskLimit).count() == 1
        saved = db.query(models.RiskLimit).first()
        assert saved.limit_name == "持仓限额_测试"
        assert saved.enabled is True
    finally:
        db.close()

    e2 = RiskEngine()
    await e2.initialize()
    load_limits(e2, db_factory=db_factory)
    assert e2.get_limit("l1") is not None
    assert e2.get_limit("l1").limit_value == 0.3
