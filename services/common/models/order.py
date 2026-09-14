import enum
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Enum, JSON
from datetime import datetime

from common.database import Base


class OrderStatus(enum.Enum):
    PENDING = 'pending'
    SUBMITTED = 'submitted'
    PARTIALLY_FILLED = 'partially_filled'
    FILLED = 'filled'
    CANCELLED = 'cancelled'
    REJECTED = 'rejected'


class OrderDirection(enum.Enum):
    BUY = 'buy'
    SELL = 'sell'


class OrderType(enum.Enum):
    LIMIT = 'limit'
    MARKET = 'market'


class Order(Base):
    """订单模型"""
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键 ID')
    order_no = Column(String(64), unique=True, nullable=False, comment='订单号')
    strategy_id = Column(Integer, comment='策略 ID')
    code = Column(String(50), nullable=False, comment='股票代码')
    direction = Column(Enum(OrderDirection, values_callable=lambda x: [e.value for e in x]), nullable=False, comment='交易方向')
    order_type = Column(Enum(OrderType, values_callable=lambda x: [e.value for e in x]), default=OrderType.LIMIT, comment='订单类型')
    price = Column(Float, comment='委托价格')
    quantity = Column(Integer, nullable=False, comment='委托数量')
    filled_quantity = Column(Integer, default=0, comment='成交数量')
    avg_price = Column(Float, comment='成交均价')
    status = Column(Enum(OrderStatus, values_callable=lambda x: [e.value for e in x]), default=OrderStatus.PENDING, comment='订单状态')
    submit_time = Column(DateTime, default=datetime.now, comment='提交时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    filled_time = Column(DateTime, comment='成交时间')
    reject_reason = Column(Text, comment='拒绝原因')
    extra = Column(JSON, comment='扩展信息')

    __table_args__ = (
        {'sqlite_autoincrement': True},
    )

    def __repr__(self):
        return f'<Order(id={self.id}, order_no={self.order_no}, code={self.code}, direction={self.direction.value})>'


class Trade(Base):
    """成交模型"""
    __tablename__ = 'trades'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键 ID')
    order_no = Column(String(64), nullable=False, comment='订单号')
    code = Column(String(50), nullable=False, comment='股票代码')
    direction = Column(Enum(OrderDirection, values_callable=lambda x: [e.value for e in x]), nullable=False, comment='交易方向')
    price = Column(Float, nullable=False, comment='成交价格')
    quantity = Column(Integer, nullable=False, comment='成交数量')
    commission = Column(Float, default=0, comment='佣金')
    slip = Column(Float, default=0, comment='滑点')
    submit_time = Column(DateTime, default=datetime.now, comment='提交时间')
    trade_time = Column(DateTime, default=datetime.now, comment='成交时间')
    extra = Column(JSON, comment='扩展信息')

    __table_args__ = (
        {'sqlite_autoincrement': True},
    )

    def __repr__(self):
        return f'<Trade(id={self.id}, order_no={self.order_no}, code={self.code}, price={self.price})>'
