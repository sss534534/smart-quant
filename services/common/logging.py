"""
统一日志配置模块
提供标准化的日志记录功能，支持结构化日志和上下文信息
"""
import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar
from dataclasses import dataclass, asdict


# 上下文变量，用于存储请求ID等上下文信息
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)


@dataclass
class LogContext:
    """日志上下文信息"""
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    service_name: str = "unknown"
    extra: Optional[Dict[str, Any]] = None


class JSONFormatter(logging.Formatter):
    """JSON格式化器，输出结构化日志"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # 添加上下文信息
        request_id = request_id_var.get()
        user_id = user_id_var.get()
        
        if request_id:
            log_entry["request_id"] = request_id
        if user_id:
            log_entry["user_id"] = user_id
            
        # 添加额外字段
        if hasattr(record, 'extra_data'):
            log_entry["extra"] = record.extra_data
            
        # 添加异常信息
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
            
        return json.dumps(log_entry, ensure_ascii=False)


class ContextLogger:
    """带上下文的日志记录器"""
    
    def __init__(self, logger: logging.Logger, service_name: str = "unknown"):
        self.logger = logger
        self.service_name = service_name
    
    def _log(self, level: int, message: str, extra: Optional[Dict[str, Any]] = None):
        """统一的日志记录方法"""
        record = self.logger.makeRecord(
            name=self.logger.name,
            level=level,
            fn="",
            lno=0,
            msg=message,
            args=(),
            exc_info=None
        )
        
        # 添加额外数据
        if extra:
            record.extra_data = extra
            
        self.logger.handle(record)
    
    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, kwargs)
    
    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, kwargs)
    
    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log(logging.CRITICAL, message, kwargs)
    
    def exception(self, message: str, exc_info=None, **kwargs):
        """记录异常信息"""
        record = self.logger.makeRecord(
            name=self.logger.name,
            level=logging.ERROR,
            fn="",
            lno=0,
            msg=message,
            args=(),
            exc_info=exc_info or True
        )
        
        if kwargs:
            record.extra_data = kwargs
            
        self.logger.handle(record)


def setup_logging(
    service_name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None
) -> ContextLogger:
    """
    设置日志配置
    
    Args:
        service_name: 服务名称
        level: 日志级别
        log_file: 日志文件路径（可选）
    
    Returns:
        ContextLogger实例
    """
    # 创建logger
    logger = logging.getLogger(service_name)
    logger.setLevel(level)
    
    # 清除现有处理器
    logger.handlers.clear()
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)
    
    # 添加文件处理器（如果指定）
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)
    
    # 防止日志传播到根logger
    logger.propagate = False
    
    return ContextLogger(logger, service_name)


def get_logger(service_name: str) -> ContextLogger:
    """获取日志记录器"""
    return setup_logging(service_name)