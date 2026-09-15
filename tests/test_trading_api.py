"""
交易服务测试
"""
import pytest
from fastapi.testclient import TestClient


class TestTradingAPI:
    """交易 API 测试"""

    def test_get_orders_empty(self, trading_client: TestClient):
        """测试获取空订单列表"""
        response = trading_client.get("/trading/orders")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_create_order(self, trading_client: TestClient, sample_order_data: dict):
        """测试创建订单"""
        response = trading_client.post("/trading/order", json=sample_order_data)
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["code"] == sample_order_data["code"]
        assert data["direction"] == sample_order_data["direction"]
        assert "order_no" in data or "id" in data

    def test_create_order_missing_fields(self, trading_client: TestClient):
        """测试创建订单缺少必填字段"""
        response = trading_client.post("/trading/order", json={"code": "600000"})
        assert response.status_code == 422

    def test_get_orders_after_create(self, trading_client: TestClient, sample_order_data: dict):
        """测试创建后获取订单列表"""
        trading_client.post("/trading/order", json=sample_order_data)
        response = trading_client.get("/trading/orders")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_positions_empty(self, trading_client: TestClient):
        """测试获取空持仓列表"""
        response = trading_client.get("/trading/positions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_capital(self, trading_client: TestClient):
        """测试获取资金账户"""
        response = trading_client.get("/trading/capital")
        assert response.status_code == 200

    def test_cancel_order_not_found(self, trading_client: TestClient):
        """测试撤回不存在的订单"""
        response = trading_client.post("/trading/order/nonexistent/cancel")
        assert response.status_code in (404, 400)

    def test_health_check(self, trading_client: TestClient):
        """测试健康检查端点"""
        response = trading_client.get("/health")
        assert response.status_code in (200, 503)
