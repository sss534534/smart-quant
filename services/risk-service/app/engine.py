"""
风控引擎
提供风险检查、限额管理、风险监控等功能
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from dataclasses import dataclass, field
from enum import Enum
import logging
import numpy as np

logger = logging.getLogger(__name__)


class RiskType(str, Enum):
    """风险类型"""
    POSITION_LIMIT = "position_limit"
    SINGLE_TRADE_LIMIT = "single_trade_limit"
    DAILY_LIMIT = "daily_limit"
    MAX_LOSS_LIMIT = "max_loss_limit"
    MAX_POSITION_LOSS = "max_position_loss"
    POSITION_PERCENTAGE = "position_percentage"
    RISK_VALUE = "risk_value"
    DRAWDOWN = "drawdown"


class RiskLevel(str, Enum):
    """风险等级"""
    NORMAL = "normal"
    WARNING = "warning"
    DANGER = "danger"
    BLOCKED = "blocked"


@dataclass
class RiskLimit:
    """风控限额"""
    limit_id: str
    limit_name: str
    risk_type: RiskType
    limit_value: float
    warning_value: Optional[float] = None
    description: Optional[str] = None
    enabled: bool = True
    update_time: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "limit_id": self.limit_id,
            "limit_name": self.limit_name,
            "risk_type": self.risk_type.value,
            "limit_value": self.limit_value,
            "warning_value": self.warning_value,
            "description": self.description,
            "enabled": self.enabled,
            "update_time": self.update_time.isoformat(),
        }


@dataclass
class RiskCheckResult:
    """风控检查结果"""
    passed: bool
    risk_type: RiskType
    level: RiskLevel
    limit_value: float
    actual_value: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "risk_type": self.risk_type.value,
            "level": self.level.value,
            "limit_value": self.limit_value,
            "actual_value": self.actual_value,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class RiskAlert:
    """风险预警"""
    alert_id: str
    risk_type: RiskType
    level: RiskLevel
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "risk_type": self.risk_type.value,
            "level": self.level.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


class RiskEngine:
    """风控引擎"""
    
    def __init__(self):
        """初始化风控引擎"""
        self._limits: Dict[str, RiskLimit] = {}
        self._alerts: List[RiskAlert] = []
        self._check_history: List[RiskCheckResult] = []
        
        # 默认限额
        self._default_limits = {
            RiskType.POSITION_LIMIT: 0.3,  # 单只股票最大持仓比例
            RiskType.SINGLE_TRADE_LIMIT: 0.1,  # 单笔交易最大比例
            RiskType.DAILY_LIMIT: 0.05,  # 每日最大亏损比例
            RiskType.MAX_LOSS_LIMIT: 0.2,  # 最大亏损比例
            RiskType.DRAWDOWN: 0.15,  # 最大回撤比例
        }
        
        self._initialized = False
        self._running = False
        
    async def initialize(self):
        """初始化风控引擎"""
        # 加载默认限额
        for risk_type, limit_value in self._default_limits.items():
            limit = RiskLimit(
                limit_id=f"default_{risk_type.value}",
                limit_name=f"Default {risk_type.value}",
                risk_type=risk_type,
                limit_value=limit_value,
                warning_value=limit_value * 0.8,
                description=f"Default limit for {risk_type.value}",
            )
            self._limits[limit.limit_id] = limit
        
        self._initialized = True
        self._running = True
        
        logger.info("Risk engine initialized")
    
    async def shutdown(self):
        """关闭风控引擎"""
        self._running = False
        logger.info("Risk engine shutdown")
    
    def add_limit(self, limit: RiskLimit):
        """添加风控限额"""
        self._limits[limit.limit_id] = limit
        logger.info(f"Risk limit added: {limit.limit_id}")
    
    def update_limit(self, limit_id: str, updates: Dict[str, Any]) -> bool:
        """更新风控限额"""
        limit = self._limits.get(limit_id)
        if not limit:
            return False
        
        for key, value in updates.items():
            if hasattr(limit, key):
                setattr(limit, key, value)
        
        limit.update_time = datetime.now()
        return True
    
    def remove_limit(self, limit_id: str) -> bool:
        """删除风控限额"""
        if limit_id in self._limits:
            del self._limits[limit_id]
            return True
        return False
    
    def get_limits(self) -> List[RiskLimit]:
        """获取所有风控限额"""
        return list(self._limits.values())
    
    def get_limit(self, limit_id: str) -> Optional[RiskLimit]:
        """获取单个风控限额"""
        return self._limits.get(limit_id)
    
    def check_position_limit(
        self,
        code: str,
        quantity: int,
        price: float,
        total_capital: float,
        current_positions: Dict[str, Dict[str, Any]],
    ) -> RiskCheckResult:
        """
        检查持仓限额
        
        Args:
            code: 股票代码
            quantity: 交易数量
            price: 交易价格
            total_capital: 总资金
            current_positions: 当前持仓
        
        Returns:
            风控检查结果
        """
        # 计算交易金额
        trade_amount = quantity * price
        
        # 计算当前持仓市值
        current_position_value = sum(
            pos.get("quantity", 0) * pos.get("current_price", pos.get("avg_price", 0))
            for pos in current_positions.values()
        )
        
        # 计算交易后的持仓比例
        current_stock_value = current_positions.get(code, {}).get("quantity", 0) * price
        new_stock_value = current_stock_value + trade_amount
        new_position_ratio = new_stock_value / total_capital if total_capital > 0 else 0
        
        # 获取限额
        limit = None
        for l in self._limits.values():
            if l.risk_type == RiskType.POSITION_LIMIT and l.enabled:
                limit = l
                break
        
        limit_value = limit.limit_value if limit else self._default_limits[RiskType.POSITION_LIMIT]
        warning_value = limit.warning_value if limit else limit_value * 0.8
        
        # 检查是否超过限额
        passed = new_position_ratio <= limit_value
        level = RiskLevel.NORMAL
        
        if new_position_ratio > limit_value:
            level = RiskLevel.BLOCKED
            message = f"持仓比例 {new_position_ratio:.2%} 超过限额 {limit_value:.2%}"
        elif new_position_ratio > warning_value:
            level = RiskLevel.WARNING
            message = f"持仓比例 {new_position_ratio:.2%} 接近限额 {limit_value:.2%}"
            passed = True
        else:
            message = f"持仓比例 {new_position_ratio:.2%} 正常"
        
        result = RiskCheckResult(
            passed=passed,
            risk_type=RiskType.POSITION_LIMIT,
            level=level,
            limit_value=limit_value,
            actual_value=new_position_ratio,
            message=message,
            details={
                "code": code,
                "trade_amount": trade_amount,
                "new_stock_value": new_stock_value,
                "new_position_ratio": new_position_ratio,
            }
        )
        
        self._check_history.append(result)
        
        if level in [RiskLevel.WARNING, RiskLevel.DANGER, RiskLevel.BLOCKED]:
            self._add_alert(result)
        
        return result
    
    def check_single_trade_limit(
        self,
        code: str,
        quantity: int,
        price: float,
        total_capital: float,
    ) -> RiskCheckResult:
        """
        检查单笔交易限额
        
        Args:
            code: 股票代码
            quantity: 交易数量
            price: 交易价格
            total_capital: 总资金
        
        Returns:
            风控检查结果
        """
        trade_amount = quantity * price
        trade_ratio = trade_amount / total_capital if total_capital > 0 else 0
        
        # 获取限额
        limit = None
        for l in self._limits.values():
            if l.risk_type == RiskType.SINGLE_TRADE_LIMIT and l.enabled:
                limit = l
                break
        
        limit_value = limit.limit_value if limit else self._default_limits[RiskType.SINGLE_TRADE_LIMIT]
        warning_value = limit.warning_value if limit else limit_value * 0.8
        
        # 检查是否超过限额
        passed = trade_ratio <= limit_value
        level = RiskLevel.NORMAL
        
        if trade_ratio > limit_value:
            level = RiskLevel.BLOCKED
            message = f"单笔交易比例 {trade_ratio:.2%} 超过限额 {limit_value:.2%}"
        elif trade_ratio > warning_value:
            level = RiskLevel.WARNING
            message = f"单笔交易比例 {trade_ratio:.2%} 接近限额 {limit_value:.2%}"
            passed = True
        else:
            message = f"单笔交易比例 {trade_ratio:.2%} 正常"
        
        result = RiskCheckResult(
            passed=passed,
            risk_type=RiskType.SINGLE_TRADE_LIMIT,
            level=level,
            limit_value=limit_value,
            actual_value=trade_ratio,
            message=message,
            details={
                "code": code,
                "trade_amount": trade_amount,
                "trade_ratio": trade_ratio,
            }
        )
        
        self._check_history.append(result)
        
        if level in [RiskLevel.WARNING, RiskLevel.DANGER, RiskLevel.BLOCKED]:
            self._add_alert(result)
        
        return result
    
    def check_daily_loss_limit(
        self,
        current_pnl: float,
        total_capital: float,
    ) -> RiskCheckResult:
        """
        检查每日亏损限额
        
        Args:
            current_pnl: 当日盈亏
            total_capital: 总资金
        
        Returns:
            风控检查结果
        """
        loss_ratio = abs(current_pnl) / total_capital if total_capital > 0 and current_pnl < 0 else 0
        
        # 获取限额
        limit = None
        for l in self._limits.values():
            if l.risk_type == RiskType.DAILY_LIMIT and l.enabled:
                limit = l
                break
        
        limit_value = limit.limit_value if limit else self._default_limits[RiskType.DAILY_LIMIT]
        warning_value = limit.warning_value if limit else limit_value * 0.8
        
        # 检查是否超过限额
        passed = loss_ratio <= limit_value
        level = RiskLevel.NORMAL
        
        if loss_ratio > limit_value:
            level = RiskLevel.BLOCKED
            message = f"当日亏损比例 {loss_ratio:.2%} 超过限额 {limit_value:.2%}"
        elif loss_ratio > warning_value:
            level = RiskLevel.WARNING
            message = f"当日亏损比例 {loss_ratio:.2%} 接近限额 {limit_value:.2%}"
            passed = True
        else:
            message = f"当日亏损比例 {loss_ratio:.2%} 正常"
        
        result = RiskCheckResult(
            passed=passed,
            risk_type=RiskType.DAILY_LIMIT,
            level=level,
            limit_value=limit_value,
            actual_value=loss_ratio,
            message=message,
            details={
                "current_pnl": current_pnl,
                "loss_ratio": loss_ratio,
            }
        )
        
        self._check_history.append(result)
        
        if level in [RiskLevel.WARNING, RiskLevel.DANGER, RiskLevel.BLOCKED]:
            self._add_alert(result)
        
        return result
    
    def check_drawdown(
        self,
        current_equity: float,
        peak_equity: float,
    ) -> RiskCheckResult:
        """
        检查回撤
        
        Args:
            current_equity: 当前权益
            peak_equity: 历史最高权益
        
        Returns:
            风控检查结果
        """
        drawdown = (peak_equity - current_equity) / peak_equity if peak_equity > 0 else 0
        
        # 获取限额
        limit = None
        for l in self._limits.values():
            if l.risk_type == RiskType.DRAWDOWN and l.enabled:
                limit = l
                break
        
        limit_value = limit.limit_value if limit else self._default_limits[RiskType.DRAWDOWN]
        warning_value = limit.warning_value if limit else limit_value * 0.8
        
        # 检查是否超过限额
        passed = drawdown <= limit_value
        level = RiskLevel.NORMAL
        
        if drawdown > limit_value:
            level = RiskLevel.BLOCKED
            message = f"回撤 {drawdown:.2%} 超过限额 {limit_value:.2%}"
        elif drawdown > warning_value:
            level = RiskLevel.WARNING
            message = f"回撤 {drawdown:.2%} 接近限额 {limit_value:.2%}"
            passed = True
        else:
            message = f"回撤 {drawdown:.2%} 正常"
        
        result = RiskCheckResult(
            passed=passed,
            risk_type=RiskType.DRAWDOWN,
            level=level,
            limit_value=limit_value,
            actual_value=drawdown,
            message=message,
            details={
                "current_equity": current_equity,
                "peak_equity": peak_equity,
                "drawdown": drawdown,
            }
        )
        
        self._check_history.append(result)
        
        if level in [RiskLevel.WARNING, RiskLevel.DANGER, RiskLevel.BLOCKED]:
            self._add_alert(result)
        
        return result
    
    def calculate_var(
        self,
        returns: List[float],
        confidence: float = 0.95,
        period: int = 1,
    ) -> float:
        """
        计算VaR（在险价值）
        
        Args:
            returns: 收益率序列
            confidence: 置信水平
            period: 持有期
        
        Returns:
            VaR值
        """
        if not returns:
            return 0.0
        
        returns_array = np.array(returns)
        
        # 使用历史模拟法
        var = np.percentile(returns_array, (1 - confidence) * 100)
        
        # 调整持有期
        var = var * np.sqrt(period)
        
        return abs(var)
    
    def calculate_sharpe_ratio(
        self,
        returns: List[float],
        risk_free_rate: float = 0.03,
    ) -> float:
        """
        计算夏普比率
        
        Args:
            returns: 收益率序列
            risk_free_rate: 无风险利率
        
        Returns:
            夏普比率
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        returns_array = np.array(returns)
        
        # 计算年化收益率
        mean_return = np.mean(returns_array) * 252
        
        # 计算年化波动率
        std_return = np.std(returns_array) * np.sqrt(252)
        
        # 计算夏普比率
        sharpe = (mean_return - risk_free_rate) / std_return if std_return > 0 else 0
        
        return sharpe
    
    def _add_alert(self, result: RiskCheckResult):
        """添加风险预警"""
        import uuid
        
        alert = RiskAlert(
            alert_id=str(uuid.uuid4()),
            risk_type=result.risk_type,
            level=result.level,
            message=result.message,
            details=result.details,
        )
        
        self._alerts.append(alert)
        logger.warning(f"Risk alert: {alert.message}")
    
    def get_alerts(
        self,
        risk_type: Optional[RiskType] = None,
        level: Optional[RiskLevel] = None,
        limit: int = 100,
    ) -> List[RiskAlert]:
        """获取风险预警"""
        alerts = self._alerts.copy()
        
        if risk_type:
            alerts = [a for a in alerts if a.risk_type == risk_type]
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        # 按时间倒序
        alerts.sort(key=lambda a: a.timestamp, reverse=True)
        
        return alerts[:limit]
    
    def get_check_history(
        self,
        risk_type: Optional[RiskType] = None,
        limit: int = 100,
    ) -> List[RiskCheckResult]:
        """获取检查历史"""
        history = self._check_history.copy()
        
        if risk_type:
            history = [h for h in history if h.risk_type == risk_type]
        
        return history[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_limits": len(self._limits),
            "enabled_limits": len([l for l in self._limits.values() if l.enabled]),
            "total_alerts": len(self._alerts),
            "total_checks": len(self._check_history),
            "blocked_checks": len([c for c in self._check_history if not c.passed]),
        }


# 全局风控引擎实例
risk_engine = RiskEngine()