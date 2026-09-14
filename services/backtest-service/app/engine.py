"""
回测引擎
提供完整的策略回测功能
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Type
from datetime import datetime, date
from dataclasses import dataclass, field
import logging
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """回测配置"""
    start_date: date
    end_date: date
    initial_capital: float = 100000.0
    commission_rate: float = 0.0003
    slippage_rate: float = 0.001
    stamp_tax_rate: float = 0.001  # 印花税（卖出时）
    min_commission: float = 5.0  # 最低佣金


@dataclass
class Trade:
    """交易记录"""
    trade_id: str
    code: str
    direction: str  # buy/sell
    price: float
    quantity: int
    amount: float
    commission: float
    slippage: float
    tax: float
    timestamp: datetime
    pnl: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "code": self.code,
            "direction": self.direction,
            "price": self.price,
            "quantity": self.quantity,
            "amount": self.amount,
            "commission": self.commission,
            "slippage": self.slippage,
            "tax": self.tax,
            "timestamp": self.timestamp.isoformat(),
            "pnl": self.pnl,
        }


@dataclass
class Position:
    """持仓"""
    code: str
    quantity: int
    avg_price: float
    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    
    def update_price(self, price: float):
        """更新价格"""
        self.current_price = price
        self.market_value = self.quantity * price
        self.unrealized_pnl = (price - self.avg_price) * self.quantity


@dataclass
class BacktestState:
    """回测状态"""
    capital: float
    positions: Dict[str, Position]
    trades: List[Trade]
    equity_curve: List[Dict[str, Any]]
    daily_returns: List[float]
    
    def get_total_value(self) -> float:
        """获取总资产"""
        position_value = sum(pos.market_value for pos in self.positions.values())
        return self.capital + position_value
    
    def get_position_value(self) -> float:
        """获取持仓市值"""
        return sum(pos.market_value for pos in self.positions.values())


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, config: BacktestConfig):
        """
        初始化回测引擎
        
        Args:
            config: 回测配置
        """
        self.config = config
        self.state = BacktestState(
            capital=config.initial_capital,
            positions={},
            trades=[],
            equity_curve=[],
            daily_returns=[],
        )
        self._trade_counter = 0
        self._initialized = False
        
    def initialize(self):
        """初始化回测"""
        self.state = BacktestState(
            capital=self.config.initial_capital,
            positions={},
            trades=[],
            equity_curve=[],
            daily_returns=[],
        )
        self._trade_counter = 0
        self._initialized = True
        
        logger.info(
            f"Backtest initialized: {self.config.start_date} to {self.config.end_date}, "
            f"capital: {self.config.initial_capital}"
        )
    
    def calculate_commission(self, amount: float, direction: str) -> float:
        """
        计算佣金
        
        Args:
            amount: 交易金额
            direction: 交易方向
        
        Returns:
            佣金金额
        """
        commission = amount * self.config.commission_rate
        return max(commission, self.config.min_commission)
    
    def calculate_slippage(self, price: float, direction: str) -> float:
        """
        计算滑点
        
        Args:
            price: 价格
            direction: 交易方向
        
        Returns:
            滑点金额
        """
        slippage = price * self.config.slippage_rate
        return slippage
    
    def calculate_tax(self, amount: float, direction: str) -> float:
        """
        计算印花税
        
        Args:
            amount: 交易金额
            direction: 交易方向
        
        Returns:
            印花税金额
        """
        if direction == "sell":
            return amount * self.config.stamp_tax_rate
        return 0.0
    
    def execute_trade(
        self,
        code: str,
        direction: str,
        price: float,
        quantity: int,
        timestamp: datetime
    ) -> Optional[Trade]:
        """
        执行交易
        
        Args:
            code: 股票代码
            direction: 交易方向
            price: 价格
            quantity: 数量
            timestamp: 时间戳
        
        Returns:
            交易记录（失败返回None）
        """
        if not self._initialized:
            logger.error("Backtest not initialized")
            return None
        
        # 计算滑点后的价格
        slippage = self.calculate_slippage(price, direction)
        if direction == "buy":
            exec_price = price + slippage
        else:
            exec_price = price - slippage
        
        # 计算交易金额
        amount = exec_price * quantity
        
        # 计算费用
        commission = self.calculate_commission(amount, direction)
        tax = self.calculate_tax(amount, direction)
        total_cost = amount + commission + tax
        
        # 检查资金是否充足
        if direction == "buy":
            if total_cost > self.state.capital:
                logger.warning(f"Insufficient capital: {self.state.capital} < {total_cost}")
                return None
            
            # 更新持仓
            if code in self.state.positions:
                pos = self.state.positions[code]
                total_quantity = pos.quantity + quantity
                pos.avg_price = (pos.avg_price * pos.quantity + exec_price * quantity) / total_quantity
                pos.quantity = total_quantity
            else:
                self.state.positions[code] = Position(
                    code=code,
                    quantity=quantity,
                    avg_price=exec_price
                )
            
            # 扣减资金
            self.state.capital -= total_cost
            
        elif direction == "sell":
            # 检查持仓是否充足
            if code not in self.state.positions or self.state.positions[code].quantity < quantity:
                logger.warning(f"Insufficient position: {code}")
                return None
            
            # 计算盈亏
            pos = self.state.positions[code]
            pnl = (exec_price - pos.avg_price) * quantity - commission - tax
            
            # 更新持仓
            pos.quantity -= quantity
            if pos.quantity == 0:
                del self.state.positions[code]
            
            # 增加资金
            self.state.capital += amount - commission - tax
        
        # 创建交易记录
        self._trade_counter += 1
        trade = Trade(
            trade_id=f"T{self._trade_counter:06d}",
            code=code,
            direction=direction,
            price=exec_price,
            quantity=quantity,
            amount=amount,
            commission=commission,
            slippage=slippage,
            tax=tax,
            timestamp=timestamp,
            pnl=pnl if direction == "sell" else 0.0,
        )
        
        self.state.trades.append(trade)
        logger.debug(f"Trade executed: {trade.direction} {trade.code} at {trade.price}")
        
        return trade
    
    def update_positions(self, prices: Dict[str, float], timestamp: datetime):
        """
        更新持仓价格
        
        Args:
            prices: 价格字典 {code: price}
            timestamp: 时间戳
        """
        for code, price in prices.items():
            if code in self.state.positions:
                self.state.positions[code].update_price(price)
        
        # 记录权益曲线
        total_value = self.state.get_total_value()
        self.state.equity_curve.append({
            "timestamp": timestamp.isoformat(),
            "equity": total_value,
            "capital": self.state.capital,
            "position_value": self.state.get_position_value(),
        })
        
        # 计算日收益率
        if len(self.state.equity_curve) > 1:
            prev_equity = self.state.equity_curve[-2]["equity"]
            daily_return = (total_value - prev_equity) / prev_equity
            self.state.daily_returns.append(daily_return)
    
    def calculate_metrics(self) -> Dict[str, Any]:
        """
        计算回测指标
        
        Returns:
            回测指标字典
        """
        if not self.state.equity_curve:
            return {}
        
        # 基本指标
        initial_capital = self.config.initial_capital
        final_equity = self.state.get_total_value()
        total_return = (final_equity - initial_capital) / initial_capital
        
        # 年化收益率
        days = (self.config.end_date - self.config.start_date).days
        annual_return = (1 + total_return) ** (365 / max(days, 1)) - 1
        
        # 夏普比率
        if self.state.daily_returns:
            daily_returns = np.array(self.state.daily_returns)
            sharpe_ratio = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252) if np.std(daily_returns) > 0 else 0
        else:
            sharpe_ratio = 0
        
        # 最大回撤
        equity_values = [e["equity"] for e in self.state.equity_curve]
        if equity_values:
            peak = equity_values[0]
            max_drawdown = 0
            max_drawdown_duration = 0
            current_drawdown_duration = 0
            
            for equity in equity_values:
                if equity >= peak:
                    peak = equity
                    current_drawdown_duration = 0
                else:
                    drawdown = (peak - equity) / peak
                    max_drawdown = max(max_drawdown, drawdown)
                    current_drawdown_duration += 1
                    max_drawdown_duration = max(max_drawdown_duration, current_drawdown_duration)
        else:
            max_drawdown = 0
            max_drawdown_duration = 0
        
        # 胜率
        trades = self.state.trades
        sell_trades = [t for t in trades if t.direction == "sell"]
        winning_trades = [t for t in sell_trades if t.pnl > 0]
        win_rate = len(winning_trades) / len(sell_trades) if sell_trades else 0
        
        # 盈亏比
        winning_pnl = sum(t.pnl for t in winning_trades)
        losing_trades = [t for t in sell_trades if t.pnl <= 0]
        losing_pnl = abs(sum(t.pnl for t in losing_trades))
        profit_factor = winning_pnl / losing_pnl if losing_pnl > 0 else float('inf')
        
        # 平均盈亏
        avg_win = winning_pnl / len(winning_trades) if winning_trades else 0
        avg_loss = losing_pnl / len(losing_trades) if losing_trades else 0
        
        # 最大单笔盈亏
        largest_win = max([t.pnl for t in winning_trades]) if winning_trades else 0
        largest_loss = min([t.pnl for t in losing_trades]) if losing_trades else 0
        
        return {
            "total_return": total_return,
            "annual_return": annual_return,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "max_drawdown_duration": max_drawdown_duration,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "largest_win": largest_win,
            "largest_loss": largest_loss,
            "total_trades": len(trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "start_balance": initial_capital,
            "end_balance": final_equity,
        }
    
    def get_trades(self) -> List[Dict[str, Any]]:
        """获取交易记录"""
        return [trade.to_dict() for trade in self.state.trades]
    
    def get_equity_curve(self) -> List[Dict[str, Any]]:
        """获取权益曲线"""
        return self.state.equity_curve
    
    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """获取当前持仓"""
        return {
            code: {
                "quantity": pos.quantity,
                "avg_price": pos.avg_price,
                "current_price": pos.current_price,
                "market_value": pos.market_value,
                "unrealized_pnl": pos.unrealized_pnl,
            }
            for code, pos in self.state.positions.items()
        }


class BacktestRunner:
    """回测运行器"""
    
    def __init__(self):
        self.engines: Dict[str, BacktestEngine] = {}
        self._running: Dict[str, bool] = {}
    
    async def run_backtest(
        self,
        backtest_id: str,
        strategy_class: Type,
        strategy_params: Dict[str, Any],
        config: BacktestConfig,
        market_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        运行回测
        
        Args:
            backtest_id: 回测ID
            strategy_class: 策略类
            strategy_params: 策略参数
            config: 回测配置
            market_data: 市场数据
        
        Returns:
            回测结果
        """
        # 创建回测引擎
        engine = BacktestEngine(config)
        engine.initialize()
        self.engines[backtest_id] = engine
        self._running[backtest_id] = True
        
        # 创建策略实例
        strategy = strategy_class(backtest_id, strategy_params)
        strategy.initialize(strategy_params)
        
        try:
            # 按日期遍历
            dates = market_data["timestamp"].dt.date.unique()
            
            for current_date in dates:
                if not self._running.get(backtest_id, False):
                    break
                
                # 获取当日数据
                daily_data = market_data[market_data["timestamp"].dt.date == current_date]
                
                # 遍历每只股票
                for _, row in daily_data.iterrows():
                    # 创建BarData
                    from strategies.base import BarData
                    bar = BarData(
                        code=row["code"],
                        timestamp=row["timestamp"],
                        open=row["open"],
                        high=row["high"],
                        low=row["low"],
                        close=row["close"],
                        volume=row["volume"],
                        amount=row.get("amount", 0),
                    )
                    
                    # 更新策略历史数据
                    strategy.update_bar_history(bar)
                    
                    # 获取策略信号
                    signal = strategy.on_bar(bar)
                    
                    # 执行交易
                    if signal:
                        if signal.action.value == "buy":
                            engine.execute_trade(
                                code=signal.code,
                                direction="buy",
                                price=signal.price,
                                quantity=signal.quantity,
                                timestamp=bar.timestamp,
                            )
                        elif signal.action.value == "sell":
                            engine.execute_trade(
                                code=signal.code,
                                direction="sell",
                                price=signal.price,
                                quantity=signal.quantity,
                                timestamp=bar.timestamp,
                            )
                
                # 更新持仓价格
                prices = {}
                for _, row in daily_data.iterrows():
                    prices[row["code"]] = row["close"]
                engine.update_positions(prices, datetime.combine(current_date, datetime.min.time()))
            
            # 计算回测指标
            metrics = engine.calculate_metrics()
            
            return {
                "backtest_id": backtest_id,
                "status": "completed",
                "metrics": metrics,
                "trades": engine.get_trades(),
                "equity_curve": engine.get_equity_curve(),
                "positions": engine.get_positions(),
            }
            
        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            return {
                "backtest_id": backtest_id,
                "status": "failed",
                "error": str(e),
            }
        finally:
            self._running[backtest_id] = False
    
    def stop_backtest(self, backtest_id: str) -> bool:
        """停止回测"""
        if backtest_id in self._running:
            self._running[backtest_id] = False
            return True
        return False
    
    def get_backtest_status(self, backtest_id: str) -> Dict[str, Any]:
        """获取回测状态"""
        return {
            "backtest_id": backtest_id,
            "is_running": self._running.get(backtest_id, False),
            "has_engine": backtest_id in self.engines,
        }


# 全局回测运行器
backtest_runner = BacktestRunner()