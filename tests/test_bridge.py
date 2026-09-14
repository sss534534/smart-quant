import asyncio
import sys

import pytest

sys.path.insert(0, "services")
sys.path.insert(0, "services/strategy-engine")

from strategies.base import StrategySignal, SignalAction


@pytest.mark.asyncio
async def test_bridge_persists_signal_and_posts_order(monkeypatch):
    from app import bridge
    from common import settings

    monkeypatch.setattr(settings.trading, "TRADING_ENABLED", True)

    seen = {}
    posted = {"calls": []}

    class FakeSession:
        def __init__(self, **kw):
            self.rows = []
            self._closed = False

        def add(self, row):
            self.rows.append(row)

        def commit(self):
            seen["rows"] = self.rows

        def close(self):
            self._closed = True

    monkeypatch.setattr(bridge, "SessionLocal", FakeSession)

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json=None, headers=None):
            posted["calls"].append((url, json))

            class R:
                status_code = 201

            return R()

    monkeypatch.setattr("httpx.AsyncClient", FakeClient)

    sig = StrategySignal(
        strategy_id="S000001", code="600000", action=SignalAction.BUY,
        price=10.0, quantity=100, reason="test",
    )
    await bridge.handle_signal(sig)

    assert len(seen["rows"]) == 1   # strategy_signals 落一行
    assert posted["calls"], "应 POST 到 trading-service"
    url, payload = posted["calls"][0]
    assert "/trading/order" in url
    assert payload["code"] == "600000"
    assert payload["quantity"] == 100