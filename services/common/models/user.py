"""用户模型"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from datetime import datetime

from common.database import Base


class User(Base):
    """用户模型"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键 ID')
    username = Column(String(50), unique=True, nullable=False, comment='用户名')
    email = Column(String(100), unique=True, nullable=False, comment='邮箱')
    hashed_password = Column(String(255), nullable=False, comment='密码哈希')
    is_active = Column(Boolean, default=True, comment='是否启用')
    is_admin = Column(Boolean, default=False, comment='是否管理员')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    last_login_at = Column(DateTime, comment='最后登录时间')

    def __repr__(self):
        return f'<User(id={self.id}, username={self.username})>'
