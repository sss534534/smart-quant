import enum
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Enum, JSON, BigInteger, Boolean
from datetime import datetime

from common.database import Base


class RiskType(enum.Enum):
    POSITION_LIMIT = 'position_limit'
    SINGLE_TRADE_LIMIT = 'single_trade_limit'
    DAILY_LIMIT = 'daily_limit'
    MAX_LOSS_LIMIT = 'max_loss_limit'
    MAX_POSITION_LOSS = 'max_position_loss'
    POSITION_PERCENTAGE = 'position_percentage'
    RISK_VALUE = 'risk_value'
    DRAWDOWN = 'drawdown'


class RiskLevel(enum.Enum):
    NORMAL = 'normal'
    WARNING = 'warning'
    DANGER = 'danger'
    BLOCKED = 'blocked'


class RiskLimit(Base):
    """风控限额模型"""
    __tablename__ = 'risk_limits'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键 ID')
    limit_name = Column(String(100), nullable=False, comment='限额名称')
    risk_type = Column(Enum(RiskType, values_callable=lambda x: [e.value for e in x]), nullable=False, comment='风险类型')
    limit_value = Column(Float, nullable=False, comment='限额值')
    warning_value = Column(Float, comment='警告值')
    description = Column(Text, comment='描述')
    enabled = Column(Boolean, default=True, comment='是否启用')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        {'sqlite_autoincrement': True},
    )

    def __repr__(self):
        return f'<RiskLimit(id={self.id}, limit_name={self.limit_name}, type={self.risk_type.value})>'


class RiskCheck(Base):
    """风控检查记录模型"""
    __tablename__ = 'risk_checks'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键 ID')
    order_no = Column(String(64), comment='订单号')
    code = Column(String(50), nullable=False, comment='股票代码')
    direction = Column(String(20), nullable=False, comment='方向')
    price = Column(Float, nullable=False, comment='价格')
    quantity = Column(Integer, nullable=False, comment='数量')
    risk_type = Column(Enum(RiskType, values_callable=lambda x: [e.value for e in x]), nullable=False, comment='检查类型')
    limit_value = Column(Float, comment='限额值')
    actual_value = Column(Float, comment='实际值')
    passed = Column(Boolean, nullable=False, comment='是否通过')
    level = Column(Enum(RiskLevel, values_callable=lambda x: [e.value for e in x]), default=RiskLevel.NORMAL, comment='风险等级')
    message = Column(Text, comment='检查信息')
    created_at = Column(DateTime, default=datetime.now, comment='检查时间')

    __table_args__ = (
        {'sqlite_autoincrement': True},
    )

    def __repr__(self):
        return f'<RiskCheck(id={self.id}, order_no={self.order_no}, passed={self.passed})>'


class RiskReport(Base):
    """风控日报模型"""
    __tablename__ = 'risk_reports'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键 ID')
    report_date = Column(DateTime, nullable=False, unique=True, comment='报告日期')
    total_trades = Column(Integer, default=0, comment='总交易笔数')
    risk_alerts = Column(Integer, default=0, comment='风险预警次数')
    risk_blocked = Column(Integer, default=0, comment='风控拦截次数')
    total_position_value = Column(Float, default=0, comment='总持仓市值')
    total_pnl = Column(Float, default=0, comment='总盈亏')
    max_position_pct = Column(Float, default=0, comment='最大持仓占比')
    max_single_trade_pct = Column(Float, default=0, comment='最大单笔占比')
    daily_loss_limit = Column(Float, default=0, comment='当日亏损限额')
    current_daily_loss = Column(Float, default=0, comment='当日累计亏损')
    risk_value = Column(Float, default=0, comment='在险价值 VaR')
    created_at = Column(DateTime, default=datetime.now, comment='报告时间')

    __table_args__ = (
        {'sqlite_autoincrement': True},
    )

    def __repr__(self):
        return f'<RiskReport(id={self.id}, report_date={self.report_date})>'
