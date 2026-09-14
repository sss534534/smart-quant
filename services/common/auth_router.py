"""
认证路由模块
提供登录、注册、刷新 token、获取当前用户、登出等端点
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional

from common.auth import auth_service, UserRole, User
from common.auth_dependency import get_current_user, bearer_scheme

router = APIRouter()


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    email: Optional[str] = Field(None, max_length=100)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    user: dict


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """用户登录"""
    result = await auth_service.authenticate(req.username, req.password)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    return TokenResponse(
        access_token=result["access_token"]["token"],
        refresh_token=result["refresh_token"]["token"],
        user=result["user"],
    )


@router.post("/register", response_model=dict)
async def register(req: RegisterRequest):
    """用户注册"""
    try:
        user = await auth_service.create_user(
            username=req.username,
            password=req.password,
            email=req.email,
            role=UserRole.USER,
        )
        return {"status": "ok", "user": user.to_dict()}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/refresh")
async def refresh_token(req: RefreshRequest):
    """刷新 access token"""
    result = await auth_service.refresh_access_token(req.refresh_token)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="refresh token 无效或已过期",
        )
    return {
        "access_token": result["access_token"]["token"],
        "refresh_token": result["refresh_token"]["token"],
        "token_type": "Bearer",
    }


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user.to_dict()


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    """登出（撤销当前 token）"""
    if credentials:
        await auth_service.logout(credentials.credentials)
    return {"status": "ok", "message": "已登出"}


@router.get("/users")
async def list_users(current_user: User = Depends(get_current_user)):
    """列出所有用户（仅管理员）"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅管理员可查看用户列表",
        )
    return [u.to_dict() for u in auth_service.list_users()]
