import asyncio
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime
from .strategy import BaseStrategy, StrategyStatus, StrategySignal, SignalAction

logger = logging.getLogger(__name__)


class StrategyManager:
    """策略管理器 - 管理所有策略实例"""

    def __init__(self):
        self._strategies: Dict[str, BaseStrategy] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._bar_queue: asyncio.Queue = asyncio.Queue()
        self._signal_callbacks: List[Callable] = []
        self._initialized = False

    async def initialize(self):
        """初始化管理器"""
        if self._initialized:
            return

        logger.info("Initializing StrategyManager")
        self._initialized = True

    async def close(self):
        """关闭管理器"""
        logger.info("Closing StrategyManager")
        # 停止所有策略
        for strategy_id in list(self._strategies.keys()):
            await self.stop(strategy_id)

        # 清空队列
        while not self._bar_queue.empty():
            try:
                self._bar_queue.get_nowait()
            except:
                break

    async def run(self, strategy_id: str, bar_data: Dict):
        """运行单个策略"""
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            logger.error(f"Strategy not found: {strategy_id}")
            return

        try:
            signal = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: strategy.on_bar(bar_data)
            )

            if signal:
                strategy.emit_signal(signal)

        except Exception as e:
            logger.error(f"Error processing bar for strategy {strategy_id}: {e}")
            strategy.notify("on_error", {"strategy_id": strategy_id, "error": str(e)})

    async def process_bars(self, bar_data: Dict):
        """处理 K 线数据，发送给所有运行中的策略"""
        if not self._initialized:
            await self.initialize()

        # 放入队列
        await self._bar_queue.put(bar_data)

        # 并发处理所有策略
        tasks = [
            self._process_single_strategy(strategy_id, bar_data)
            for strategy_id, strategy in self._strategies.items()
            if strategy._status == StrategyStatus.RUNNING
        ]

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_single_strategy(self, strategy_id: str, bar_data: Dict):
        """处理单个策略"""
        try:
            strategy = self._strategies[strategy_id]
            await self.run(strategy_id, bar_data)
        except Exception as e:
            logger.error(f"Error in _process_single_strategy {strategy_id}: {e}")

    async def start(self, strategy_id: str) -> bool:
        """启动策略"""
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            logger.error(f"Strategy not found: {strategy_id}")
            return False

        try:
            # 初始化策略
            if not strategy._initialized:
                strategy.initialize(strategy.params)

            strategy._status = StrategyStatus.RUNNING
            strategy._start_time = datetime.now()

            # 创建后台任务
            task = asyncio.create_task(self._run_loop(strategy_id))
            self._running_tasks[strategy_id] = task

            logger.info(f"Started strategy: {strategy_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to start strategy {strategy_id}: {e}")
            return False

    async def stop(self, strategy_id: str) -> bool:
        """停止策略"""
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            logger.error(f"Strategy not found: {strategy_id}")
            return False

        try:
            # 记录结束时间
            strategy._end_time = datetime.now()
            strategy._status = StrategyStatus.STOPPED

            # 取消后台任务
            if strategy_id in self._running_tasks:
                task = self._running_tasks[strategy_id]
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                del self._running_tasks[strategy_id]

            logger.info(f"Stopped strategy: {strategy_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop strategy {strategy_id}: {e}")
            return False

    async def pause(self, strategy_id: str) -> bool:
        """暂停策略"""
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return False

        strategy._status = StrategyStatus.PAUSED
        logger.info(f"Paused strategy: {strategy_id}")
        return True

    async def resume(self, strategy_id: str) -> bool:
        """恢复策略"""
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return False

        strategy._status = StrategyStatus.RUNNING
        logger.info(f"Resumed strategy: {strategy_id}")
        return True

    def add_strategy(self, strategy: BaseStrategy) -> bool:
        """添加策略"""
        if strategy.strategy_id in self._strategies:
            logger.warning(f"Strategy already exists: {strategy.strategy_id}")
            return False

        self._strategies[strategy.strategy_id] = strategy
        logger.info(f"Added strategy: {strategy.strategy_id}")
        return True

    def remove_strategy(self, strategy_id: str) -> bool:
        """移除策略"""
        if strategy_id in self._strategies:
            del self._strategies[strategy_id]
            if strategy_id in self._running_tasks:
                del self._running_tasks[strategy_id]
            logger.info(f"Removed strategy: {strategy_id}")
            return True
        return False

    def get_all_strategies(self) -> Dict[str, BaseStrategy]:
        """获取所有策略"""
        return self._strategies.copy()

    def get_strategy(self, strategy_id: str) -> Optional[BaseStrategy]:
        """获取单个策略"""
        return self._strategies.get(strategy_id)

    def get_running_strategies(self) -> List[BaseStrategy]:
        """获取所有运行中的策略"""
        return [
            s for s in self._strategies.values()
            if s._status == StrategyStatus.RUNNING
        ]

    def register_signal_callback(self, callback: Callable):
        """注册信号回调"""
        self._signal_callbacks.append(callback)

    def emit_signals(self, signal: StrategySignal):
        """发出信号给所有监听者"""
        for callback in self._signal_callbacks:
            try:
                callback(signal)
            except Exception as e:
                logger.error(f"Signal callback error: {e}")

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "total_strategies": len(self._strategies),
            "running_strategies": len(self.get_running_strategies()),
            "paused_strategies": sum(1 for s in self._strategies.values() if s._status == StrategyStatus.PAUSED),
            "stopped_strategies": sum(1 for s in self._strategies.values() if s._status == StrategyStatus.STOPPED),
        }

    async def _run_loop(self, strategy_id: str):
        """策略运行循环"""
        while True:
            try:
                # 等待新的 K 线数据
                bar_data = await asyncio.wait_for(
                    self._bar_queue.get(),
                    timeout=30.0  # 30 秒超时
                )
                await self.run(strategy_id, bar_data)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in run loop for {strategy_id}: {e}")
