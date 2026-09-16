import enum
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, JSON, BigInteger, Boolean
from datetime import datetime, date

from common.database import Base


class MarketDataType(enum.Enum):
    QUOTE = 'quote'
    KLINE_1M = 'kline_1m'
    KLINE_5M = 'kline_5m'
    KLINE_15M = 'kline_15m'
    KLINE_30M = 'kline_30m'
    KLINE_1H = 'kline_1h'
    KLINE_4H = 'kline_4h'
    KLINE_1D = 'kline_1d'
    KLINE_1W = 'kline_1w'


class MarketData(Base):
    """市场数据模型"""
    __tablename__ = 'market_data'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键 ID')
    code = Column(String(50), nullable=False, comment='股票代码')
    data_type = Column(Enum(MarketDataType, values_callable=lambda x: [e.value for e in x]), nullable=False, comment='数据类型')
    timestamp = Column(DateTime, nullable=False, comment='时间戳')
    open = Column(Float, comment='开盘价')
    high = Column(Float, comment='最高价')
    low = Column(Float, comment='最低价')
    close = Column(Float, nullable=False, comment='收盘价')
    volume = Column(BigInteger, comment='成交量')
    amount = Column(Float, comment='成交额')
    open_interest = Column(Float, comment='持仓量')
    vwap = Column(Float, comment='加权均价')
    extra = Column(JSON, comment='扩展数据')

    __table_args__ = (
        {'sqlite_autoincrement': True},
    )

    def __repr__(self):
        return f'<MarketData(id={self.id}, code={self.code}, timestamp={self.timestamp})>'


class StockInfo(Base):
    """股票信息模型"""
    __tablename__ = 'stock_info'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键 ID')
    code = Column(String(50), unique=True, nullable=False, comment='股票代码')
    name = Column(String(100), nullable=False, comment='股票名称')
    exchange = Column(String(50), nullable=False, comment='交易所：SSE/SZSE/BSE')
    sector = Column(String(100), comment='所属行业')
    market_cap = Column(Float, comment='总市值')
    total_shares = Column(Float, comment='总股本')
    float_shares = Column(Float, comment='流通股本')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        {'sqlite_autoincrement': True},
    )

    def __repr__(self):
        return f'<StockInfo(id={self.id}, code={self.code}, name={self.name})>'


class Calendar(Base):
    """交易日日历模型"""
    __tablename__ = 'calendar'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键 ID')
    trade_date = Column(DateTime, unique=True, nullable=False, comment='交易日期')
    is_holiday = Column(Boolean, default=False, comment='是否节假日')
    market_status = Column(String(50), default='open', comment='市场状态：open/closed')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        {'sqlite_autoincrement': True},
    )

    def __repr__(self):
        return f'<Calendar(id={self.id}, trade_date={self.trade_date})>'


class Watchlist(Base):
    """自选股模型"""
    __tablename__ = 'watchlist'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键 ID')
    user_id = Column(Integer, nullable=False, default=0, comment='用户 ID')
    code = Column(String(50), nullable=False, comment='股票代码')
    name = Column(String(100), comment='股票名称')
    remark = Column(String(200), comment='备注')
    sort_order = Column(Integer, default=0, comment='排序')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        {'sqlite_autoincrement': True},
    )

    def __repr__(self):
        return f'<Watchlist(id={self.id}, user_id={self.user_id}, code={self.code})>'
