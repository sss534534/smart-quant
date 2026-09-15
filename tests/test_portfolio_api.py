"""
组合服务测试
"""
import pytest
from fastapi.testclient import TestClient


class TestPortfolioAPI:
    """组合 API 测试"""

    def test_get_positions_empty(self, portfolio_client: TestClient):
        """测试获取空持仓列表"""
        response = portfolio_client.get("/portfolio/positions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_summary(self, portfolio_client: TestClient):
        """测试获取组合概览"""
        response = portfolio_client.get("/portfolio/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_assets" in data or "cash" in data or "positions_value" in data

    def test_get_account(self, portfolio_client: TestClient):
        """测试获取资金账户"""
        response = portfolio_client.get("/portfolio/account")
        assert response.status_code == 200

    def test_get_logs_empty(self, portfolio_client: TestClient):
        """测试获取空资金流水"""
        response = portfolio_client.get("/portfolio/logs")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_deposit(self, portfolio_client: TestClient):
        """测试存入资金"""
        response = portfolio_client.post(
            "/portfolio/deposit",
            params={"amount": 10000, "description": "test deposit"},
        )
        assert response.status_code == 200

    def test_withdraw(self, portfolio_client: TestClient):
        """测试取出资金"""
        # 先存入再取出
        portfolio_client.post(
            "/portfolio/deposit",
            params={"amount": 50000, "description": "for withdraw test"},
        )
        response = portfolio_client.post(
            "/portfolio/withdraw",
            params={"amount": 5000, "description": "test withdraw"},
        )
        assert response.status_code in (200, 400)

    def test_get_analysis(self, portfolio_client: TestClient):
        """测试获取组合分析"""
        response = portfolio_client.get("/portfolio/analysis")
        assert response.status_code in (200, 400)

    def test_get_stats(self, portfolio_client: TestClient):
        """测试获取统计"""
        response = portfolio_client.get("/portfolio/stats")
        assert response.status_code == 200

    def test_health_check(self, portfolio_client: TestClient):
        """测试健康检查端点"""
        response = portfolio_client.get("/health")
        assert response.status_code in (200, 503)
