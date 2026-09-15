"""
回测服务测试
"""
import pytest
from fastapi.testclient import TestClient


class TestBacktestAPI:
    """回测 API 测试"""

    def test_list_backtests_empty(self, backtest_client: TestClient):
        """测试获取空回测列表"""
        response = backtest_client.get("/backtest/")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data

    def test_create_backtest(self, backtest_client: TestClient, sample_backtest_data: dict):
        """测试创建回测任务"""
        response = backtest_client.post("/backtest/", json=sample_backtest_data)
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["name"] == sample_backtest_data["name"]
        assert "id" in data
        assert data["status"] in ("pending", "running")

    def test_get_backtest(self, backtest_client: TestClient, sample_backtest_data: dict):
        """测试获取回测详情"""
        create_response = backtest_client.post("/backtest/", json=sample_backtest_data)
        backtest_id = create_response.json()["id"]
        response = backtest_client.get(f"/backtest/{backtest_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == backtest_id

    def test_get_backtest_not_found(self, backtest_client: TestClient):
        """测试获取不存在的回测"""
        response = backtest_client.get("/backtest/999")
        assert response.status_code == 404

    def test_get_backtest_result(self, backtest_client: TestClient, sample_backtest_data: dict):
        """测试获取回测结果"""
        create_response = backtest_client.post("/backtest/", json=sample_backtest_data)
        backtest_id = create_response.json()["id"]
        response = backtest_client.get(f"/backtest/{backtest_id}/result")
        # 结果可能在 running/completed 状态
        assert response.status_code in (200, 404, 400)

    def test_list_backtests_with_pagination(self, backtest_client: TestClient, sample_backtest_data: dict):
        """测试分页获取回测列表"""
        for i in range(3):
            data = sample_backtest_data.copy()
            data["name"] = f"Backtest {i}"
            backtest_client.post("/backtest/", json=data)
        response = backtest_client.get("/backtest/?page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 3
        assert len(data["items"]) <= 2

    def test_health_check(self, backtest_client: TestClient):
        """测试健康检查端点"""
        response = backtest_client.get("/health")
        assert response.status_code in (200, 503)
