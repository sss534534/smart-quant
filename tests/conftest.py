"""
pytest 配置文件
提供测试夹具和配置
"""
import sys
import os
from typing import Generator, Dict, Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import StaticPool

# 将 services 目录加入 sys.path 以便导入 common 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services'))

from common.database import Base
from common import models  # noqa: F401  确保所有模型被注册


# ============ 测试数据库（SQLite 内存） ============
TEST_DATABASE_URL = "sqlite://"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """覆盖 get_db 依赖，使用测试数据库"""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def db_session() -> Generator:
    """数据库会话夹具"""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


# ============ 客户端夹具 ============

@pytest.fixture(scope="function")
def strategy_client(db_session):
    """策略服务测试客户端"""
    from common.database import get_db
    from strategy_engine.app.main import app

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def data_client(db_session):
    """数据服务测试客户端"""
    from common.database import get_db
    from data_service.app.main import app

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def trading_client(db_session):
    """交易服务测试客户端"""
    from common.database import get_db
    from trading_service.app.main import app

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def portfolio_client(db_session):
    """组合服务测试客户端"""
    from common.database import get_db
    from portfolio_service.app.main import app

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def risk_client(db_session):
    """风控服务测试客户端"""
    from common.database import get_db
    from risk_service.app.main import app

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def backtest_client(db_session):
    """回测服务测试客户端"""
    from common.database import get_db
    from backtest_service.app.main import app

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


# ============ 测试数据夹具 ============

@pytest.fixture
def sample_strategy_data() -> Dict[str, Any]:
    """示例策略数据"""
    return {
        "name": "Test Strategy",
        "code": "test_001",
        "type": "dual_ma",
        "description": "Test strategy description",
        "params": {"short_window": 5, "long_window": 20},
    }


@pytest.fixture
def sample_order_data() -> Dict[str, Any]:
    """示例订单数据"""
    return {
        "code": "600000",
        "direction": "buy",
        "order_type": "limit",
        "price": 10.5,
        "quantity": 100,
    }


@pytest.fixture
def sample_backtest_data() -> Dict[str, Any]:
    """示例回测数据"""
    return {
        "name": "Test Backtest",
        "strategy_id": 1,
        "code_list": ["600000", "000001"],
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "initial_capital": 100000,
        "commission_rate": 0.0003,
        "slip_rate": 0.001,
    }


@pytest.fixture
def sample_risk_limit_data() -> Dict[str, Any]:
    """示例风控限额数据"""
    return {
        "limit_name": "Position Limit",
        "risk_type": "position_limit",
        "limit_value": 0.3,
        "warning_value": 0.25,
        "description": "Maximum position percentage",
        "enabled": True,
    }


@pytest.fixture
def sample_user_data() -> Dict[str, Any]:
    """示例用户数据"""
    return {
        "username": "testuser",
        "password": "testpass123",
        "email": "test@test.com",
    }
