# tests/test_persistence_portfolio.py
import pytest
import sys
sys.path.insert(0, "services")
sys.path.insert(0, "services/portfolio-service")
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from common import Base, models  # noqa: F401
from app.engine import PortfolioEngine


@pytest.fixture
def db_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.mark.asyncio
async def test_portfolio_state_persisted_and_loaded(db_factory):
    from app.persistence import save_state, load_state

    engine = PortfolioEngine()
    await engine.initialize(initial_capital=100000.0)
    engine.process_trade("600000", "buy", 10.0, 1000, commission=5.0)
    engine.process_trade("600000", "sell", 12.0, 400, commission=5.0)
    save_state(engine, db_factory=db_factory)

    db = db_factory()
    assert db.query(models.Account).count() == 1
    assert db.query(models.Position).count() == 1
    db.close()

    e2 = PortfolioEngine()
    await e2.initialize(initial_capital=100000.0)
    load_state(e2, db_factory=db_factory)
    assert e2.get_position("600000") is not None
    assert e2.get_position("600000").quantity == 600
    summary = e2.get_summary()
    assert summary["cash"] < 99990.0  # 卖出后资金已包含部分回笼
