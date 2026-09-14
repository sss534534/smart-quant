"""
pytest配置文件
提供测试夹具和配置
"""
import pytest
from typing import Generator, Dict, Any
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# 测试数据库URL
TEST_DATABASE_URL = "sqlite:///./test.db"

# 创建测试数据库引擎
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()


@pytest.fixture(scope="session")
def anyio_backend():
    """异步后端配置"""
    return "asyncio"


@pytest.fixture(scope="function")
def db_session() -> Generator:
    """数据库会话夹具"""
    # 创建表
    Base.metadata.create_all(bind=engine)
    
    # 创建会话
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        # 清理表
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session) -> Generator:
    """测试客户端夹具"""
    from fastapi import FastAPI
    
    # 创建测试应用
    app = FastAPI()
    
    # 添加路由（根据需要导入）
    # from app.routers import market, strategy, etc.
    
    # 使用测试数据库
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    # 这里需要根据实际应用调整
    # app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_strategy_data() -> Dict[str, Any]:
    """示例策略数据"""
    return {
        "name": "Test Strategy",
        "code": "test_001",
        "type": "technical",
        "description": "Test strategy description",
        "params": {
            "short_window": 5,
            "long_window": 20
        }
    }


@pytest.fixture
def sample_order_data() -> Dict[str, Any]:
    """示例订单数据"""
    return {
        "code": "000001",
        "direction": "buy",
        "order_type": "limit",
        "price": 10.5,
        "quantity": 100
    }


@pytest.fixture
def sample_backtest_data() -> Dict[str, Any]:
    """示例回测数据"""
    return {
        "name": "Test Backtest",
        "strategy_id": 1,
        "code_list": ["000001", "000002"],
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "initial_capital": 100000,
        "commission_rate": 0.0003,
        "slip_rate": 0.001
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
        "enabled": True
    }