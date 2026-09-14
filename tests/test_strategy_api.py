"""
策略API测试
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestStrategyAPI:
    """策略API测试类"""
    
    def test_list_strategies_empty(self, client: TestClient):
        """测试获取空策略列表"""
        response = client.get("/strategy/")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert data["total"] == 0
        assert len(data["items"]) == 0
    
    def test_create_strategy(self, client: TestClient, sample_strategy_data: dict):
        """测试创建策略"""
        response = client.post("/strategy/", json=sample_strategy_data)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_strategy_data["name"]
        assert data["code"] == sample_strategy_data["code"]
        assert data["type"] == sample_strategy_data["type"]
        assert "id" in data
        assert "created_at" in data
    
    def test_create_strategy_duplicate_code(self, client: TestClient, sample_strategy_data: dict):
        """测试创建重复代码的策略"""
        # 创建第一个策略
        client.post("/strategy/", json=sample_strategy_data)
        
        # 创建第二个相同代码的策略
        response = client.post("/strategy/", json=sample_strategy_data)
        assert response.status_code == 400
        assert "已存在" in response.json()["message"]
    
    def test_get_strategy(self, client: TestClient, sample_strategy_data: dict):
        """测试获取策略详情"""
        # 创建策略
        create_response = client.post("/strategy/", json=sample_strategy_data)
        strategy_id = create_response.json()["id"]
        
        # 获取策略详情
        response = client.get(f"/strategy/{strategy_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == strategy_id
        assert data["name"] == sample_strategy_data["name"]
    
    def test_get_strategy_not_found(self, client: TestClient):
        """测试获取不存在的策略"""
        response = client.get("/strategy/999")
        assert response.status_code == 404
    
    def test_update_strategy(self, client: TestClient, sample_strategy_data: dict):
        """测试更新策略"""
        # 创建策略
        create_response = client.post("/strategy/", json=sample_strategy_data)
        strategy_id = create_response.json()["id"]
        
        # 更新策略
        update_data = {"name": "Updated Strategy", "description": "Updated description"}
        response = client.put(f"/strategy/{strategy_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
    
    def test_delete_strategy(self, client: TestClient, sample_strategy_data: dict):
        """测试删除策略"""
        # 创建策略
        create_response = client.post("/strategy/", json=sample_strategy_data)
        strategy_id = create_response.json()["id"]
        
        # 删除策略
        response = client.delete(f"/strategy/{strategy_id}")
        assert response.status_code == 200
        
        # 验证策略已删除
        get_response = client.get(f"/strategy/{strategy_id}")
        assert get_response.status_code == 404
    
    def test_run_strategy(self, client: TestClient, sample_strategy_data: dict):
        """测试运行策略"""
        # 创建策略
        create_response = client.post("/strategy/", json=sample_strategy_data)
        strategy_id = create_response.json()["id"]
        
        # 运行策略
        response = client.post(f"/strategy/{strategy_id}/run")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["strategy_id"] == strategy_id
    
    def test_stop_strategy(self, client: TestClient, sample_strategy_data: dict):
        """测试停止策略"""
        # 创建策略
        create_response = client.post("/strategy/", json=sample_strategy_data)
        strategy_id = create_response.json()["id"]
        
        # 停止策略
        response = client.post(f"/strategy/{strategy_id}/stop")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"
        assert data["strategy_id"] == strategy_id
    
    def test_list_strategies_with_pagination(self, client: TestClient, sample_strategy_data: dict):
        """测试分页获取策略列表"""
        # 创建多个策略
        for i in range(5):
            data = sample_strategy_data.copy()
            data["code"] = f"test_{i:03d}"
            data["name"] = f"Strategy {i}"
            client.post("/strategy/", json=data)
        
        # 获取第一页
        response = client.get("/strategy/?page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2
        
        # 获取第二页
        response = client.get("/strategy/?page=2&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        
        # 获取第三页
        response = client.get("/strategy/?page=3&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1