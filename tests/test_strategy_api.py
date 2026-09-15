"""
策略服务测试
"""
import pytest
from fastapi.testclient import TestClient


class TestStrategyAPI:
    """策略 API 测试"""

    def test_list_strategies_empty(self, strategy_client: TestClient):
        """测试获取空策略列表"""
        response = strategy_client.get("/api/v1/strategy/")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert data["total"] == 0
        assert len(data["items"]) == 0

    def test_create_strategy(self, strategy_client: TestClient, sample_strategy_data: dict):
        """测试创建策略"""
        response = strategy_client.post("/api/v1/strategy/", json=sample_strategy_data)
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["name"] == sample_strategy_data["name"]
        assert data["code"] == sample_strategy_data["code"]
        assert "id" in data

    def test_create_strategy_duplicate_code(self, strategy_client: TestClient, sample_strategy_data: dict):
        """测试创建重复代码的策略"""
        strategy_client.post("/api/v1/strategy/", json=sample_strategy_data)
        response = strategy_client.post("/api/v1/strategy/", json=sample_strategy_data)
        assert response.status_code in (400, 409, 500)

    def test_get_strategy(self, strategy_client: TestClient, sample_strategy_data: dict):
        """测试获取策略详情"""
        create_response = strategy_client.post("/api/v1/strategy/", json=sample_strategy_data)
        strategy_id = create_response.json()["id"]
        response = strategy_client.get(f"/api/v1/strategy/{strategy_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == strategy_id
        assert data["name"] == sample_strategy_data["name"]

    def test_get_strategy_not_found(self, strategy_client: TestClient):
        """测试获取不存在的策略"""
        response = strategy_client.get("/api/v1/strategy/999")
        assert response.status_code == 404

    def test_update_strategy(self, strategy_client: TestClient, sample_strategy_data: dict):
        """测试更新策略"""
        create_response = strategy_client.post("/api/v1/strategy/", json=sample_strategy_data)
        strategy_id = create_response.json()["id"]
        update_data = {"name": "Updated Strategy", "description": "Updated description"}
        response = strategy_client.put(f"/api/v1/strategy/{strategy_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]

    def test_delete_strategy(self, strategy_client: TestClient, sample_strategy_data: dict):
        """测试删除策略"""
        create_response = strategy_client.post("/api/v1/strategy/", json=sample_strategy_data)
        strategy_id = create_response.json()["id"]
        response = strategy_client.delete(f"/api/v1/strategy/{strategy_id}")
        assert response.status_code == 200
        get_response = strategy_client.get(f"/api/v1/strategy/{strategy_id}")
        assert get_response.status_code == 404

    def test_list_strategies_with_pagination(self, strategy_client: TestClient, sample_strategy_data: dict):
        """测试分页获取策略列表"""
        for i in range(5):
            data = sample_strategy_data.copy()
            data["code"] = f"test_{i:03d}"
            data["name"] = f"Strategy {i}"
            strategy_client.post("/api/v1/strategy/", json=data)
        response = strategy_client.get("/api/v1/strategy/?page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2

    def test_health_check(self, strategy_client: TestClient):
        """测试健康检查端点"""
        response = strategy_client.get("/health")
        assert response.status_code in (200, 503)
