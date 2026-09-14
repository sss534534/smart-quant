"""
认证和授权模块
提供用户认证、Token管理、权限控制等功能
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import hashlib
import secrets
import logging

logger = logging.getLogger(__name__)


class UserRole(str, Enum):
    """用户角色"""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class Permission(str, Enum):
    """权限"""
    # 策略权限
    STRATEGY_READ = "strategy:read"
    STRATEGY_WRITE = "strategy:write"
    STRATEGY_DELETE = "strategy:delete"
    STRATEGY_RUN = "strategy:run"
    
    # 回测权限
    BACKTEST_READ = "backtest:read"
    BACKTEST_WRITE = "backtest:write"
    BACKTEST_RUN = "backtest:run"
    
    # 交易权限
    TRADING_READ = "trading:read"
    TRADING_WRITE = "trading:write"
    
    # 风控权限
    RISK_READ = "risk:read"
    RISK_WRITE = "risk:write"
    
    # 用户权限
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    
    # 系统权限
    SYSTEM_ADMIN = "system:admin"


# 角色权限映射
ROLE_PERMISSIONS: Dict[UserRole, List[Permission]] = {
    UserRole.ADMIN: list(Permission),  # 管理员拥有所有权限
    UserRole.USER: [
        Permission.STRATEGY_READ,
        Permission.STRATEGY_WRITE,
        Permission.STRATEGY_RUN,
        Permission.BACKTEST_READ,
        Permission.BACKTEST_WRITE,
        Permission.BACKTEST_RUN,
        Permission.TRADING_READ,
        Permission.TRADING_WRITE,
        Permission.RISK_READ,
        Permission.USER_READ,
    ],
    UserRole.VIEWER: [
        Permission.STRATEGY_READ,
        Permission.BACKTEST_READ,
        Permission.TRADING_READ,
        Permission.RISK_READ,
        Permission.USER_READ,
    ],
}


@dataclass
class User:
    """用户"""
    user_id: int
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: UserRole = UserRole.USER
    status: str = "active"
    created_at: datetime = None
    updated_at: datetime = None
    last_login_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "phone": self.phone,
            "role": self.role.value,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }


@dataclass
class Token:
    """Token"""
    token: str
    user_id: int
    token_type: str = "access"
    expires_at: datetime = None
    created_at: datetime = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "token": self.token,
            "user_id": self.user_id,
            "token_type": self.token_type,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @property
    def is_expired(self) -> bool:
        """是否过期"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


class PasswordHasher:
    """密码哈希器"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        哈希密码
        
        Args:
            password: 明文密码
        
        Returns:
            哈希后的密码
        """
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return f"{salt}:{password_hash.hex()}"
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """
        验证密码
        
        Args:
            password: 明文密码
            password_hash: 哈希后的密码
        
        Returns:
            是否匹配
        """
        try:
            salt, hash_hex = password_hash.split(':')
            password_hash_bytes = bytes.fromhex(hash_hex)
            new_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                100000
            )
            return new_hash == password_hash_bytes
        except Exception:
            return False


class TokenManager:
    """Token管理器"""
    
    def __init__(
        self,
        secret_key: str,
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ):
        """
        初始化Token管理器
        
        Args:
            secret_key: 密钥
            access_token_expire_minutes: 访问Token过期时间（分钟）
            refresh_token_expire_days: 刷新Token过期时间（天）
        """
        self.secret_key = secret_key
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self._tokens: Dict[str, Token] = {}
    
    def generate_token(self, user_id: int, token_type: str = "access") -> Token:
        """
        生成Token
        
        Args:
            user_id: 用户ID
            token_type: Token类型
        
        Returns:
            Token对象
        """
        token_string = secrets.token_urlsafe(32)
        
        if token_type == "access":
            expires_at = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        else:
            expires_at = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        token = Token(
            token=token_string,
            user_id=user_id,
            token_type=token_type,
            expires_at=expires_at,
            created_at=datetime.utcnow(),
        )
        
        self._tokens[token_string] = token
        
        logger.info(f"Token generated for user {user_id}, type: {token_type}")
        
        return token
    
    def validate_token(self, token_string: str) -> Optional[Token]:
        """
        验证Token
        
        Args:
            token_string: Token字符串
        
        Returns:
            Token对象（验证失败返回None）
        """
        token = self._tokens.get(token_string)
        
        if token is None:
            return None
        
        if token.is_expired:
            del self._tokens[token_string]
            return None
        
        return token
    
    def revoke_token(self, token_string: str) -> bool:
        """
        撤销Token
        
        Args:
            token_string: Token字符串
        
        Returns:
            是否成功
        """
        if token_string in self._tokens:
            del self._tokens[token_string]
            logger.info(f"Token revoked")
            return True
        return False
    
    def revoke_all_user_tokens(self, user_id: int) -> int:
        """
        撤销用户所有Token
        
        Args:
            user_id: 用户ID
        
        Returns:
            撤销的Token数量
        """
        count = 0
        tokens_to_remove = []
        
        for token_string, token in self._tokens.items():
            if token.user_id == user_id:
                tokens_to_remove.append(token_string)
        
        for token_string in tokens_to_remove:
            del self._tokens[token_string]
            count += 1
        
        logger.info(f"Revoked {count} tokens for user {user_id}")
        
        return count
    
    def get_user_tokens(self, user_id: int) -> List[Token]:
        """获取用户所有Token"""
        return [t for t in self._tokens.values() if t.user_id == user_id]


class AuthService:
    """认证服务"""
    
    def __init__(self):
        self._users: Dict[int, User] = {}
        self._username_index: Dict[str, int] = {}
        self._password_hashes: Dict[int, str] = {}
        self._token_manager: Optional[TokenManager] = None
        self._user_counter: int = 0
        
    async def initialize(self, secret_key: str):
        """初始化认证服务"""
        self._token_manager = TokenManager(secret_key)
        
        # 创建默认管理员
        await self.create_user(
            username="admin",
            password="admin123",
            email="admin@quant.com",
            role=UserRole.ADMIN,
        )
        
        logger.info("Auth service initialized")
    
    async def create_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        role: UserRole = UserRole.USER,
    ) -> User:
        """
        创建用户
        
        Args:
            username: 用户名
            password: 密码
            email: 邮箱
            phone: 手机号
            role: 角色
        
        Returns:
            用户对象
        """
        if username in self._username_index:
            raise ValueError(f"Username {username} already exists")
        
        self._user_counter += 1
        
        user = User(
            user_id=self._user_counter,
            username=username,
            email=email,
            phone=phone,
            role=role,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        self._users[user.user_id] = user
        self._username_index[username] = user.user_id
        self._password_hashes[user.user_id] = PasswordHasher.hash_password(password)
        
        logger.info(f"User created: {username} (ID: {user.user_id})")
        
        return user
    
    async def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        用户认证
        
        Args:
            username: 用户名
            password: 密码
        
        Returns:
            认证结果（包含Token）
        """
        user_id = self._username_index.get(username)
        if user_id is None:
            return None
        
        user = self._users.get(user_id)
        if user is None:
            return None
        
        if user.status != "active":
            return None
        
        password_hash = self._password_hashes.get(user_id)
        if password_hash is None:
            return None
        
        if not PasswordHasher.verify_password(password, password_hash):
            return None
        
        # 生成Token
        access_token = self._token_manager.generate_token(user_id, "access")
        refresh_token = self._token_manager.generate_token(user_id, "refresh")
        
        # 更新最后登录时间
        user.last_login_at = datetime.utcnow()
        
        return {
            "user": user.to_dict(),
            "access_token": access_token.to_dict(),
            "refresh_token": refresh_token.to_dict(),
        }
    
    async def refresh_access_token(self, refresh_token_string: str) -> Optional[Dict[str, Any]]:
        """
        刷新访问Token
        
        Args:
            refresh_token_string: 刷新Token
        
        Returns:
            新的Token
        """
        refresh_token = self._token_manager.validate_token(refresh_token_string)
        if refresh_token is None or refresh_token.token_type != "refresh":
            return None
        
        # 撤销旧的刷新Token
        self._token_manager.revoke_token(refresh_token_string)
        
        # 生成新的Token
        access_token = self._token_manager.generate_token(refresh_token.user_id, "access")
        new_refresh_token = self._token_manager.generate_token(refresh_token.user_id, "refresh")
        
        return {
            "access_token": access_token.to_dict(),
            "refresh_token": new_refresh_token.to_dict(),
        }
    
    async def logout(self, token_string: str) -> bool:
        """
        用户登出
        
        Args:
            token_string: Token
        
        Returns:
            是否成功
        """
        return self._token_manager.revoke_token(token_string)
    
    async def logout_all(self, user_id: int) -> int:
        """
        登出用户所有设备
        
        Args:
            user_id: 用户ID
        
        Returns:
            撤销的Token数量
        """
        return self._token_manager.revoke_all_user_tokens(user_id)
    
    def validate_token(self, token_string: str) -> Optional[User]:
        """
        验证Token并获取用户
        
        Args:
            token_string: Token
        
        Returns:
            用户对象（验证失败返回None）
        """
        token = self._token_manager.validate_token(token_string)
        if token is None:
            return None
        
        return self._users.get(token.user_id)
    
    def get_user(self, user_id: int) -> Optional[User]:
        """获取用户"""
        return self._users.get(user_id)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """通过用户名获取用户"""
        user_id = self._username_index.get(username)
        if user_id:
            return self._users.get(user_id)
        return None
    
    def list_users(self) -> List[User]:
        """获取用户列表"""
        return list(self._users.values())
    
    async def update_user(
        self,
        user_id: int,
        updates: Dict[str, Any],
    ) -> Optional[User]:
        """
        更新用户
        
        Args:
            user_id: 用户ID
            updates: 更新数据
        
        Returns:
            更新后的用户
        """
        user = self._users.get(user_id)
        if user is None:
            return None
        
        for key, value in updates.items():
            if key == "role":
                user.role = UserRole(value)
            elif key == "status":
                user.status = value
            elif hasattr(user, key):
                setattr(user, key, value)
        
        user.updated_at = datetime.utcnow()
        
        return user
    
    async def change_password(
        self,
        user_id: int,
        old_password: str,
        new_password: str,
    ) -> bool:
        """
        修改密码
        
        Args:
            user_id: 用户ID
            old_password: 旧密码
            new_password: 新密码
        
        Returns:
            是否成功
        """
        password_hash = self._password_hashes.get(user_id)
        if password_hash is None:
            return False
        
        if not PasswordHasher.verify_password(old_password, password_hash):
            return False
        
        self._password_hashes[user_id] = PasswordHasher.hash_password(new_password)
        
        # 撤销所有Token
        self._token_manager.revoke_all_user_tokens(user_id)
        
        return True
    
    async def reset_password(self, user_id: int) -> str:
        """
        重置密码
        
        Args:
            user_id: 用户ID
        
        Returns:
            新密码
        """
        new_password = secrets.token_urlsafe(12)
        self._password_hashes[user_id] = PasswordHasher.hash_password(new_password)
        
        # 撤销所有Token
        self._token_manager.revoke_all_user_tokens(user_id)
        
        return new_password


class PermissionChecker:
    """权限检查器"""
    
    @staticmethod
    def check_permission(user: User, permission: Permission) -> bool:
        """
        检查用户权限
        
        Args:
            user: 用户对象
            permission: 权限
        
        Returns:
            是否有权限
        """
        if user.role == UserRole.ADMIN:
            return True
        
        role_permissions = ROLE_PERMISSIONS.get(user.role, [])
        return permission in role_permissions
    
    @staticmethod
    def check_permissions(user: User, permissions: List[Permission]) -> bool:
        """
        检查用户多个权限
        
        Args:
            user: 用户对象
            permissions: 权限列表
        
        Returns:
            是否有所有权限
        """
        return all(
            PermissionChecker.check_permission(user, p)
            for p in permissions
        )
    
    @staticmethod
    def get_user_permissions(user: User) -> List[Permission]:
        """获取用户所有权限"""
        if user.role == UserRole.ADMIN:
            return list(Permission)
        return ROLE_PERMISSIONS.get(user.role, [])


# 全局认证服务实例
auth_service = AuthService()
permission_checker = PermissionChecker()