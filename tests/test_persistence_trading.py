import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, "services")
sys.path.insert(0, "services/trading-service")

from common import Base, models  # noqa: F401 注册表
from app.engine import TradingEngine, OrderDirection, OrderType
from common.models.order import OrderStatus


@pytest.fixture
def db_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.mark.asyncio
async def test_order_flow_persisted_and_rebuilt(db_factory):
    from app.persistence import save_order, save_trade, rebuild_engine

    engine = TradingEngine()
    await engine.initialize(initial_capital=100000.0)
    engine._positions = {}
    order = engine.create_order("600000", OrderDirection.BUY, OrderType.MARKET, 10.0, 100)

    # 手工模拟成交状态变更（不调用 submit_order，以免 httpx 请求外部服务）
    order.filled_quantity = 100
    order.avg_price = 10.01
    order.status = OrderStatus.FILLED
    order.submit_time = order.create_time
    order.filled_time = order.create_time
    engine._orders[order.order_id] = order

    save_order(order, db_factory=db_factory)

    db = db_factory()
    assert db.query(models.Order).count() == 1
    db.close()

    # 重建
    e2 = TradingEngine()
    rebuild_engine(e2, db_factory=db_factory)
    assert e2.get_order(order.order_id) is not None