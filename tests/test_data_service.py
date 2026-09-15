"""
数据服务测试
"""
import pytest
from fastapi.testclient import TestClient


class TestDataAPI:
    """数据服务 API 测试"""

    def test_get_quote(self, data_client: TestClient):
        """测试获取实时行情"""
        response = data_client.get("/api/v1/market/quote/600000", params={"provider": "mock"})
        assert response.status_code == 200
        data = response.json()
        assert "code" in data
        assert "price" in data
        assert data["code"] == "600000"

    def test_get_quote_with_invalid_code(self, data_client: TestClient):
        """测试获取不存在的股票行情"""
        response = data_client.get("/api/v1/market/quote/INVALID_CODE", params={"provider": "mock"})
        # mock provider 应该仍然返回数据或返回 404
        assert response.status_code in (200, 404)

    def test_get_kline(self, data_client: TestClient):
        """测试获取 K 线数据"""
        response = data_client.get(
            "/api/v1/market/kline/600000",
            params={
                "start_date": "2024-01-01",
                "end_date": "2024-06-30",
                "interval": "1d",
                "provider": "mock",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            item = data[0]
            assert "date" in item
            assert "open" in item
            assert "close" in item
            assert "high" in item
            assert "low" in item
            assert "volume" in item

    def test_get_kline_with_interval(self, data_client: TestClient):
        """测试不同周期 K 线"""
        for interval in ["1d", "1w"]:
            response = data_client.get(
                "/api/v1/market/kline/600000",
                params={"interval": interval, "provider": "mock"},
            )
            assert response.status_code == 200
            assert isinstance(response.json(), list)

    def test_get_stocks(self, data_client: TestClient):
        """测试获取股票列表"""
        response = data_client.get("/api/v1/market/stocks", params={"limit": 10})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            item = data[0]
            assert "code" in item
            assert "name" in item

    def test_health_check(self, data_client: TestClient):
        """测试健康检查端点"""
        response = data_client.get("/health")
        assert response.status_code in (200, 503)
