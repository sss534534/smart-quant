import enum
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Enum, JSON, BigInteger
from datetime import datetime

from common.database import Base


class PositionDirection(enum.Enum):
    LONG = 'long'
    SHORT = 'short'


class PositionStatus(enum.Enum):
    ACTIVE = 'active'
    CLOSED = 'closed'
    LIQUIDATED = 'liquidated'


class Position(Base):
    """持仓模型"""
    __tablename__ = 'positions'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键 ID')
    code = Column(String(50), nullable=False, comment='股票代码')
    name = Column(String(100), comment='股票名称')
    direction = Column(Enum(PositionDirection, values_callable=lambda x: [e.value for e in x]), default=PositionDirection.LONG, comment='持仓方向')
    quantity = Column(Integer, default=0, comment='持仓数量')
    avg_cost = Column(Float, comment='持仓成本')
    avg_price = Column(Float, comment='持仓均价')
    current_price = Column(Float, comment='当前价格')
    frozen_quantity = Column(Integer, default=0, comment='冻结数量')
    status = Column(Enum(PositionStatus, values_callable=lambda x: [e.value for e in x]), default=PositionStatus.ACTIVE, comment='持仓状态')
    created_at = Column(DateTime, default=datetime.now, comment='开仓时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    closed_at = Column(DateTime, comment='平仓时间')
    extra = Column(JSON, comment='扩展信息')

    __table_args__ = (
        {'sqlite_autoincrement': True},
    )

    def __repr__(self):
        return f'<Position(id={self.id}, code={self.code}, quantity={self.quantity})>'


class Account(Base):
    """资金账户模型"""
    __tablename__ = 'accounts'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键 ID')
    account_no = Column(String(64), unique=True, nullable=False, comment='账户号')
    account_type = Column(String(50), default='cash', comment='账户类型：cash/margin')
    balance = Column(Float, default=0, comment='可用资金')
    frozen_balance = Column(Float, default=0, comment='冻结资金')
    total_deposited = Column(Float, default=0, comment='累计入金')
    total_withdrawn = Column(Float, default=0, comment='累计出金')
    total_profit = Column(Float, default=0, comment='累计盈亏')
    status = Column(String(20), default='active', comment='账户状态')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        {'sqlite_autoincrement': True},
    )

    def __repr__(self):
        return f'<Account(id={self.id}, account_no={self.account_no}, balance={self.balance})>'


class AccountLog(Base):
    """资金流水模型"""
    __tablename__ = 'account_logs'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键 ID')
    account_no = Column(String(64), nullable=False, comment='账户号')
    type = Column(String(50), nullable=False, comment='类型：deposit/withdraw/trade/fee/dividend')
    amount = Column(Float, comment='金额')
    balance_after = Column(Float, comment='变更后余额')
    description = Column(Text, comment='描述')
    related_order_no = Column(String(64), comment='关联订单号')
    created_at = Column(DateTime, default=datetime.now, comment='发生时间')

    __table_args__ = (
        {'sqlite_autoincrement': True},
    )

    def __repr__(self):
        return f'<AccountLog(id={self.id}, type={self.type}, amount={self.amount})>'
