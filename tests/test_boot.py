import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "services"))


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