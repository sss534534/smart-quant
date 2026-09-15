"""
风控服务测试
"""
import pytest
from fastapi.testclient import TestClient


class TestRiskAPI:
    """风控 API 测试"""

    def test_get_limits(self, risk_client: TestClient):
        """测试获取风控限额列表"""
        response = risk_client.get("/risk/limits")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_create_limit(self, risk_client: TestClient, sample_risk_limit_data: dict):
        """测试创建风控限额"""
        response = risk_client.post("/risk/limits", json=sample_risk_limit_data)
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["limit_name"] == sample_risk_limit_data["limit_name"]

    def test_get_limits_after_create(self, risk_client: TestClient, sample_risk_limit_data: dict):
        """测试创建后获取限额列表"""
        risk_client.post("/risk/limits", json=sample_risk_limit_data)
        response = risk_client.get("/risk/limits")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_alerts(self, risk_client: TestClient):
        """测试获取风险预警"""
        response = risk_client.get("/risk/alerts")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_checks(self, risk_client: TestClient):
        """测试获取风控检查记录"""
        response = risk_client.get("/risk/checks")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_stats(self, risk_client: TestClient):
        """测试获取风控统计"""
        response = risk_client.get("/risk/stats")
        assert response.status_code == 200

    def test_calc_var(self, risk_client: TestClient):
        """测试 VaR 计算"""
        returns = [0.01, -0.02, 0.03, -0.01, 0.02, -0.03, 0.01, -0.01, 0.02, -0.02]
        response = risk_client.post(
            "/risk/var",
            json=returns,
            params={"confidence": 0.95, "period": 1},
        )
        assert response.status_code == 200
        data = response.json()
        assert "var" in data or "value" in data

    def test_health_check(self, risk_client: TestClient):
        """测试健康检查端点"""
        response = risk_client.get("/health")
        assert response.status_code in (200, 503)
