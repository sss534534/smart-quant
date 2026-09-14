from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, BigInteger
from datetime import datetime

from common.database import Base


class Backtest(Base):
    """回测任务模型"""
    __tablename__ = 'backtests'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键 ID')
    name = Column(String(200), nullable=False, comment='回测名称')
    strategy_id = Column(Integer, nullable=False, comment='策略 ID')
    code_list = Column(JSON, default=[], comment='测试股票列表')
    start_date = Column(DateTime, nullable=False, comment='开始日期')
    end_date = Column(DateTime, nullable=False, comment='结束日期')
    initial_capital = Column(Float, default=100000, comment='初始资金')
    commission_rate = Column(Float, default=0.0003, comment='佣金率')
    slip_rate = Column(Float, default=0.001, comment='滑点率')
    status = Column(String(50), default='running', comment='状态：pending/running/completed/failed')
    progress = Column(Integer, default=0, comment='进度：0-100')
    params = Column(JSON, default={}, comment='回测参数')
    created_by = Column(String(100), comment='创建者')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    completed_at = Column(DateTime, comment='完成时间')
    error_msg = Column(Text, comment='错误信息')

    __table_args__ = (
        {'sqlite_autoincrement': True},
    )

    def __repr__(self):
        return f'<Backtest(id={self.id}, name={self.name}, status={self.status})>'


class BacktestResult(Base):
    """回测结果模型"""
    __tablename__ = 'backtest_results'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键 ID')
    backtest_id = Column(Integer, nullable=False, comment='回测 ID')
    total_return = Column(Float, comment='总收益率')
    annual_return = Column(Float, comment='年化收益率')
    sharpe_ratio = Column(Float, comment='夏普比率')
    sortino_ratio = Column(Float, comment='索提诺比率')
    calmar_ratio = Column(Float, comment='卡尔玛比率')
    max_drawdown = Column(Float, comment='最大回撤')
    max_drawdown_duration = Column(Integer, comment='最大回撤持续时间（交易日）')
    win_rate = Column(Float, comment='胜率')
    profit_factor = Column(Float, comment='盈利因子')
    avg_win = Column(Float, comment='平均盈利')
    avg_loss = Column(Float, comment='平均亏损')
    largest_win = Column(Float, comment='最大单笔盈利')
    largest_loss = Column(Float, comment='最大单笔亏损')
    total_trades = Column(Integer, comment='总交易次数')
    winning_trades = Column(Integer, default=0, comment='盈利次数')
    losing_trades = Column(Integer, default=0, comment='亏损次数')
    start_balance = Column(Float, comment='起始资金')
    end_balance = Column(Float, comment='结束资金')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        {'sqlite_autoincrement': True},
    )

    def __repr__(self):
        return f'<BacktestResult(id={self.id}, backtest_id={self.backtest_id}, total_return={self.total_return})>'


class BacktestTrade(Base):
    """回测交易记录模型"""
    __tablename__ = 'backtest_trades'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键 ID')
    backtest_id = Column(Integer, nullable=False, comment='回测 ID')
    code = Column(String(50), nullable=False, comment='股票代码')
    date = Column(DateTime, nullable=False, comment='交易日期')
    direction = Column(String(10), nullable=False, comment='方向：buy/sell')
    price = Column(Float, nullable=False, comment='价格')
    quantity = Column(Integer, nullable=False, comment='数量')
    commission = Column(Float, default=0, comment='佣金')
    slip = Column(Float, default=0, comment='滑点')
    pnl = Column(Float, comment='盈亏')
    equity = Column(Float, comment='累计权益')
    drawdown = Column(Float, comment='当前回撤')

    __table_args__ = (
        {'sqlite_autoincrement': True},
    )

    def __repr__(self):
        return f'<BacktestTrade(id={self.id}, backtest_id={self.backtest_id}, code={self.code}, date={self.date})>'


class EquityCurve(Base):
    """权益曲线模型"""
    __tablename__ = 'equity_curves'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键 ID')
    backtest_id = Column(Integer, nullable=False, comment='回测 ID')
    date = Column(DateTime, nullable=False, comment='日期')
    equity = Column(Float, comment='累计权益')
    cumulative_return = Column(Float, comment='累计收益率')
    drawdown = Column(Float, comment='当前回撤')

    __table_args__ = (
        {'sqlite_autoincrement': True},
    )

    def __repr__(self):
        return f'<EquityCurve(id={self.id}, backtest_id={self.backtest_id}, date={self.date})>'
