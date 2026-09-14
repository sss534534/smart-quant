"""
定时任务调度器
基于 APScheduler 的异步任务调度封装
"""
import logging
from typing import Callable, Optional, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class Scheduler:
    """全局调度器封装"""

    def __init__(self):
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._initialized = False
        self._jobs = {}  # job_id -> job

    def start(self):
        """启动调度器"""
        if self._initialized:
            return
        self._scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
        self._scheduler.start()
        self._initialized = True
        logger.info("Scheduler started")

    def shutdown(self):
        """关闭调度器"""
        if self._scheduler and self._initialized:
            self._scheduler.shutdown(wait=False)
            self._initialized = False
            self._jobs.clear()
            logger.info("Scheduler shutdown")

    def add_interval_job(
        self,
        job_id: str,
        func: Callable,
        seconds: int = 60,
        replace_existing: bool = True,
        **kwargs,
    ):
        """
        添加间隔执行任务

        Args:
            job_id: 任务唯一ID
            func: 执行函数
            seconds: 间隔秒数
            replace_existing: 是否替换同名任务
        """
        if not self._initialized:
            self.start()
        job = self._scheduler.add_job(
            func,
            trigger=IntervalTrigger(seconds=seconds),
            id=job_id,
            replace_existing=replace_existing,
            **kwargs,
        )
        self._jobs[job_id] = job
        logger.info(f"Interval job added: {job_id} every {seconds}s")

    def add_cron_job(
        self,
        job_id: str,
        func: Callable,
        hour: int = 0,
        minute: int = 0,
        day_of_week: str = "*",
        replace_existing: bool = True,
        **kwargs,
    ):
        """
        添加 Cron 任务

        Args:
            job_id: 任务唯一ID
            func: 执行函数
            hour: 小时
            minute: 分钟
            day_of_week: 星期（0-6，0=周一）
        """
        if not self._initialized:
            self.start()
        job = self._scheduler.add_job(
            func,
            trigger=CronTrigger(hour=hour, minute=minute, day_of_week=day_of_week),
            id=job_id,
            replace_existing=replace_existing,
            **kwargs,
        )
        self._jobs[job_id] = job
        logger.info(f"Cron job added: {job_id} at {hour:02d}:{minute:02d}")

    def remove_job(self, job_id: str):
        """移除任务"""
        if self._scheduler:
            try:
                self._scheduler.remove_job(job_id)
                self._jobs.pop(job_id, None)
                logger.info(f"Job removed: {job_id}")
            except Exception as e:
                logger.warning(f"Failed to remove job {job_id}: {e}")

    def pause_job(self, job_id: str):
        """暂停任务"""
        if self._scheduler:
            try:
                self._scheduler.pause_job(job_id)
                logger.info(f"Job paused: {job_id}")
            except Exception as e:
                logger.warning(f"Failed to pause job {job_id}: {e}")

    def resume_job(self, job_id: str):
        """恢复任务"""
        if self._scheduler:
            try:
                self._scheduler.resume_job(job_id)
                logger.info(f"Job resumed: {job_id}")
            except Exception as e:
                logger.warning(f"Failed to resume job {job_id}: {e}")

    def get_jobs(self) -> list:
        """获取所有任务"""
        if not self._scheduler:
            return []
        return [
            {"id": j.id, "next_run_time": str(j.next_run_time), "name": j.name}
            for j in self._scheduler.get_jobs()
        ]

    @property
    def is_running(self) -> bool:
        return self._initialized


# 全局调度器实例
scheduler = Scheduler()
