import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "services"))
_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _import_service_app(service_dir):
    """各服务模块名都是 app.main，同进程会互相覆盖 sys.modules；
    用快照把已缓存的 app 包临时移除后导入，再恢复。"""
    sys.path.insert(0, str(_ROOT / "services" / service_dir))
    import importlib
    saved = {m: sys.modules.pop(m) for m in list(sys.modules) if m == "app" or m.startswith("app.")}
    try:
        main = importlib.import_module("app.main")
        return main.app
    finally:
        sys.modules.update(saved)


def test_settings_secret_key_valid():
    from common.config import settings
    assert len(settings.security.SECRET_KEY) >= 32


def test_auth_init_idempotent():
    import asyncio
    from common.auth import auth_service

    async def run():
        await auth_service.initialize(secret_key="dev-secret-key-quant-system-2026")
        before = len(auth_service._token_manager._tokens) if auth_service._token_manager else 0
        await auth_service.initialize(secret_key="dev-secret-key-quant-system-2026")
        after = len(auth_service._token_manager._tokens) if auth_service._token_manager else 0
        assert before == after

    asyncio.run(run())


def test_strategy_manager_importable():
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "services" / "strategy-engine"))
    from app.engine.manager import strategy_manager
    assert strategy_manager is not None
    assert hasattr(strategy_manager, "register_signal_callback")


def test_data_service_app_importable():
    app = _import_service_app("data-service")
    assert app.title == "Data Service"


def test_init_db_creates_all_tables():
    from common import models  # noqa: F401 注册所有表
    from sqlalchemy import create_engine, inspect
    from sqlalchemy.pool import StaticPool
    from common import Base
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    names = sorted(inspect(engine).get_table_names())
    for expected in ("orders", "positions", "accounts", "strategy_signals", "risk_limits", "risk_checks", "backtests"):
        assert expected in names, names


def _rebind_common_db_to_sqlite():
    """本地无 MySQL（docker 内部 hostname 不可达），测试把 common 引擎换成内存 SQLite，
    使 lifespan 的 init_db() 落在 SQLite 上。"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    import common
    import common.database as _db

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    common.engine = engine
    _db.engine = engine
    common.SessionLocal = _db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    from common import models  # noqa: F401 注册所有表
    common.Base.metadata.create_all(bind=engine)
    return engine


def test_risk_check_allows_no_token():
    from fastapi.testclient import TestClient
    _rebind_common_db_to_sqlite()

    app = _import_service_app("risk-service")
    with TestClient(app) as client:
        resp = client.post("/risk/check", json={
            "order_no": "O-TEST-001",
            "code": "600000",
            "direction": "buy",
            "price": 10.0,
            "quantity": 100,
        })
    assert resp.status_code == 200
    assert "passed" in resp.json()