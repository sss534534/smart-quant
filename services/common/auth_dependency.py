"""
FastAPI 认证依赖
基于 common.auth 的 auth_service，提供 get_current_user 依赖
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from common.auth import auth_service, User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> User:
    """获取当前登录用户（必须带有效 Bearer token）"""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证 token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = auth_service.validate_token(credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token 无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[User]:
    """可选认证：无 token 时返回 None，不报错"""
    if credentials is None or not credentials.credentials:
        return None
    return auth_service.validate_token(credentials.credentials)
