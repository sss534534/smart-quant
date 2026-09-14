from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Boolean
from datetime import datetime

from common.database import Base


class Strategy(Base):
    """策略模型"""
    __tablename__ = 'strategies'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键 ID')
    name = Column(String(100), nullable=False, comment='策略名称')
    code = Column(String(50), unique=True, nullable=False, comment='策略代码')
    type = Column(String(50), nullable=False, comment='策略类型：technical/factor/grid')
    description = Column(Text, comment='策略描述')
    params = Column(JSON, nullable=False, default={}, comment='策略参数')
    status = Column(String(20), default='active', comment='状态：active/inactive/deleted')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    def __repr__(self):
        return f'<Strategy(id={self.id}, name={self.name}, code={self.code})>'


class StrategySignal(Base):
    """策略信号模型"""
    __tablename__ = 'strategy_signals'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键 ID')
    strategy_id = Column(Integer, nullable=False, comment='策略 ID')
    code = Column(String(50), nullable=False, comment='股票代码')
    action = Column(String(20), nullable=False, comment='操作：buy/sell/hold')
    price = Column(Float, nullable=False, comment='触发价格')
    quantity = Column(Integer, default=100, comment='建议数量')
    reason = Column(Text, comment='信号理由')
    strength = Column(Float, default=1.0, comment='信号强度：0-1')
    created_at = Column(DateTime, default=datetime.now, comment='信号产生时间')

    __table_args__ = (
        {'sqlite_autoincrement': True},
    )

    def __repr__(self):
        return f'<StrategySignal(id={self.id}, strategy_id={self.strategy_id}, code={self.code}, action={self.action})>'
