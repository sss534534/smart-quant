import importlib
import logging
from typing import Dict, List, Type, Optional
from .strategy import BaseStrategy, StrategyStatus

logger = logging.getLogger(__name__)


class StrategyFactory:
    """策略工厂 - 用于动态加载和创建策略实例"""

    _strategies: Dict[str, Type[BaseStrategy]] = {}
    _instances: Dict[str, BaseStrategy] = {}

    @classmethod
    def register(cls, strategy_class: Type[BaseStrategy]) -> Type[BaseStrategy]:
        """注册策略类"""
        name = strategy_class.name
        if name not in cls._strategies:
            cls._strategies[name] = strategy_class
            logger.info(f"Registered strategy: {name}")
        return strategy_class

    @classmethod
    def unregister(cls, name: str) -> bool:
        """注销策略类"""
        if name in cls._strategies:
            del cls._strategies[name]
            logger.info(f"Unregistered strategy: {name}")
            return True
        return False

    @classmethod
    def get_all(cls) -> Dict[str, Type[BaseStrategy]]:
        """获取所有已注册策略"""
        return cls._strategies.copy()

    @classmethod
    def create(
        cls,
        name: str,
        strategy_id: str,
        params: Dict = None
    ) -> Optional[BaseStrategy]:
        """创建策略实例"""
        strategy_class = cls._strategies.get(name)
        if not strategy_class:
            logger.error(f"Strategy not found: {name}")
            return None

        try:
            instance = strategy_class(strategy_id, params or {})
            cls._instances[strategy_id] = instance
            logger.info(f"Created strategy instance: {name} ({strategy_id})")
            return instance
        except Exception as e:
            logger.error(f"Failed to create strategy {name}: {e}")
            return None

    @classmethod
    def get_instance(cls, strategy_id: str) -> Optional[BaseStrategy]:
        """获取策略实例"""
        return cls._instances.get(strategy_id)

    @classmethod
    def remove_instance(cls, strategy_id: str) -> bool:
        """移除策略实例"""
        if strategy_id in cls._instances:
            del cls._instances[strategy_id]
            return True
        return False

    @classmethod
    def clear_all(cls):
        """清除所有实例"""
        cls._instances.clear()
        logger.info("Cleared all strategy instances")

    @classmethod
    def load_from_directory(cls, path: str) -> int:
        """从目录加载策略模块"""
        # TODO: 实现自动发现策略模块
        logger.warning(f"Loading strategies from {path} not yet implemented")
        return 0
