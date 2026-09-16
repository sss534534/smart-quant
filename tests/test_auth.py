"""
认证系统测试
"""
import pytest
from fastapi.testclient import TestClient

from common.auth import auth_service, UserRole, PasswordHasher, TokenManager


class TestPasswordHashing:
    """密码哈希测试"""

    def test_hash_password(self):
        """测试密码哈希"""
        password = "testpass123"
        hashed = PasswordHasher.hash_password(password)
        assert hashed != password
        assert len(hashed) > 20

    def test_verify_password(self):
        """测试密码验证"""
        password = "testpass123"
        hashed = PasswordHasher.hash_password(password)
        assert PasswordHasher.verify_password(password, hashed)
        assert not PasswordHasher.verify_password("wrongpassword", hashed)


class TestTokenManagement:
    """Token 管理测试"""

    def test_create_and_validate_token(self):
        """测试创建和验证 token"""
        tm = TokenManager("test-secret-key-for-testing-1234567890")
        token = tm.generate_token(1, "access")
        assert token is not None
        assert hasattr(token, "token")
        assert len(token.token) > 20
        validated = tm.validate_token(token.token)
        assert validated is not None

    def test_invalid_token(self):
        """测试无效 token"""
        tm = TokenManager("test-secret-key-for-testing-1234567890")
        payload = tm.validate_token("invalid.token.here")
        assert payload is None


class TestAuthAPI:
    """认证 API 测试"""

    def test_register_user(self, strategy_client: TestClient, sample_user_data: dict):
        """测试用户注册"""
        response = strategy_client.post("/auth/register", json=sample_user_data)
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["status"] == "ok"
        assert "user" in data

    def test_register_duplicate(self, strategy_client: TestClient, sample_user_data: dict):
        """测试重复注册"""
        strategy_client.post("/auth/register", json=sample_user_data)
        response = strategy_client.post("/auth/register", json=sample_user_data)
        assert response.status_code == 400

    def test_login_success(self, strategy_client: TestClient, sample_user_data: dict):
        """测试登录成功"""
        strategy_client.post("/auth/register", json=sample_user_data)
        response = strategy_client.post("/auth/login", json={
            "username": sample_user_data["username"],
            "password": sample_user_data["password"],
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"

    def test_login_wrong_password(self, strategy_client: TestClient, sample_user_data: dict):
        """测试密码错误"""
        strategy_client.post("/auth/register", json=sample_user_data)
        response = strategy_client.post("/auth/login", json={
            "username": sample_user_data["username"],
            "password": "wrongpassword",
        })
        assert response.status_code == 401

    def test_me_without_token(self, strategy_client: TestClient):
        """测试无 token 访问 /auth/me"""
        response = strategy_client.get("/auth/me")
        assert response.status_code == 401

    def test_me_with_token(self, strategy_client: TestClient, sample_user_data: dict):
        """测试带 token 访问 /auth/me"""
        strategy_client.post("/auth/register", json=sample_user_data)
        login_resp = strategy_client.post("/auth/login", json={
            "username": sample_user_data["username"],
            "password": sample_user_data["password"],
        })
        token = login_resp.json()["access_token"]
        response = strategy_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == sample_user_data["username"]
