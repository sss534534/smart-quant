"""
配置管理模块
提供环境变量验证和配置管理功能
"""
import os
from typing import Optional, List, Any
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings
from enum import Enum


class Environment(str, Enum):
    """环境类型"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseConfig(BaseSettings):
    """数据库配置"""
    MYSQL_HOST: str = Field("mysql", description="MySQL主机")
    MYSQL_PORT: int = Field(3306, ge=1, le=65535, description="MySQL端口")
    MYSQL_USER: str = Field("root", description="MySQL用户名")
    MYSQL_PASSWORD: str = Field("quant123", description="MySQL密码")
    MYSQL_DATABASE: str = Field("quant_system", description="MySQL数据库名")
    MYSQL_POOL_SIZE: int = Field(10, ge=1, le=100, description="连接池大小")
    MYSQL_MAX_OVERFLOW: int = Field(20, ge=0, le=100, description="连接池溢出大小")
    MYSQL_POOL_RECYCLE: int = Field(3600, ge=60, description="连接回收时间（秒）")
    
    @field_validator('MYSQL_PASSWORD')
    @classmethod
    def validate_mysql_password(cls, v: str) -> str:
        """验证MySQL密码"""
        if len(v) < 6:
            raise ValueError('MySQL密码长度不能少于6位')
        return v
    
    def get_mysql_url(self) -> str:
        """获取MySQL连接URL"""
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
    
    class Config:
        env_prefix = "MYSQL_"
        case_sensitive = True


class RedisConfig(BaseSettings):
    """Redis配置"""
    REDIS_HOST: str = Field("redis", description="Redis主机")
    REDIS_PORT: int = Field(6379, ge=1, le=65535, description="Redis端口")
    REDIS_PASSWORD: Optional[str] = Field(None, description="Redis密码")
    REDIS_DB: int = Field(0, ge=0, le=15, description="Redis数据库")
    REDIS_MAX_CONNECTIONS: int = Field(20, ge=1, le=100, description="最大连接数")
    REDIS_SOCKET_TIMEOUT: float = Field(5.0, gt=0, description="Socket超时时间")
    REDIS_SOCKET_CONNECT_TIMEOUT: float = Field(5.0, gt=0, description="Socket连接超时时间")
    
    class Config:
        env_prefix = "REDIS_"
        case_sensitive = True


class TushareConfig(BaseSettings):
    """Tushare配置"""
    TUSHARE_TOKEN: Optional[str] = Field(None, description="Tushare Token")
    TUSHARE_API_URL: str = Field("http://api.tushare.pro", description="Tushare API URL")
    TUSHARE_TIMEOUT: int = Field(30, ge=1, le=300, description="Tushare请求超时时间")
    
    @field_validator('TUSHARE_TOKEN')
    @classmethod
    def validate_tushare_token(cls, v: Optional[str]) -> Optional[str]:
        """验证Tushare Token"""
        if v and len(v) < 10:
            raise ValueError('Tushare Token格式不正确')
        return v
    
    class Config:
        env_prefix = "TUSHARE_"
        case_sensitive = True


class TradingConfig(BaseSettings):
    """交易配置"""
    TRADING_ENABLED: bool = Field(False, description="是否启用交易")
    TRADING_MODE: str = Field("simulation", description="交易模式：simulation/live")
    TRADING_ACCOUNT: Optional[str] = Field(None, description="交易账户")
    TRADING_API_KEY: Optional[str] = Field(None, description="交易API Key")
    TRADING_API_SECRET: Optional[str] = Field(None, description="交易API Secret")
    TRADING_MAX_POSITION: float = Field(0.3, ge=0, le=1, description="最大持仓比例")
    TRADING_MAX_SINGLE_TRADE: float = Field(0.1, ge=0, le=1, description="最大单笔交易比例")
    TRADING_DAILY_LOSS_LIMIT: float = Field(0.05, ge=0, le=1, description="每日亏损限额")
    
    @field_validator('TRADING_API_SECRET')
    @classmethod
    def validate_trading_api_secret(cls, v: Optional[str]) -> Optional[str]:
        """验证交易API Secret"""
        if v and len(v) < 16:
            raise ValueError('交易API Secret长度不能少于16位')
        return v
    
    class Config:
        env_prefix = "TRADING_"
        case_sensitive = True


class LoggingConfig(BaseSettings):
    """日志配置"""
    LOG_LEVEL: LogLevel = Field(LogLevel.INFO, description="日志级别")
    LOG_FORMAT: str = Field("json", description="日志格式：json/text")
    LOG_FILE: Optional[str] = Field(None, description="日志文件路径")
    LOG_MAX_SIZE: int = Field(10, ge=1, le=100, description="日志文件最大大小（MB）")
    LOG_BACKUP_COUNT: int = Field(5, ge=1, le=20, description="日志文件备份数量")
    
    class Config:
        env_prefix = "LOG_"
        case_sensitive = True


class MonitoringConfig(BaseSettings):
    """监控配置"""
    MONITORING_ENABLED: bool = Field(True, description="是否启用监控")
    MONITORING_PORT: int = Field(9090, ge=1024, le=65535, description="监控端口")
    MONITORING_PATH: str = Field("/metrics", description="监控路径")
    HEALTH_CHECK_INTERVAL: int = Field(30, ge=5, le=300, description="健康检查间隔（秒）")
    
    class Config:
        env_prefix = "MONITORING_"
        case_sensitive = True


class SecurityConfig(BaseSettings):
    """安全配置"""
    SECRET_KEY: str = Field("dev-secret-key-quant-system-2026", description="密钥")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, ge=1, le=1440, description="访问令牌过期时间（分钟）")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, ge=1, le=30, description="刷新令牌过期时间（天）")
    ALLOWED_HOSTS: List[str] = Field(["*"], description="允许的主机")
    CORS_ORIGINS: List[str] = Field(["*"], description="CORS来源")
    
    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """验证密钥"""
        if len(v) < 32:
            raise ValueError('密钥长度不能少于32位')
        return v
    
    class Config:
        env_prefix = "SECURITY_"
        case_sensitive = True


class Settings(BaseSettings):
    """主配置类"""
    # 环境
    ENVIRONMENT: Environment = Field(Environment.DEVELOPMENT, description="运行环境")
    SERVICE_NAME: str = Field("quant-system", description="服务名称")
    SERVICE_VERSION: str = Field("1.0.0", description="服务版本")
    DEBUG: bool = Field(False, description="调试模式")
    
    # 子配置
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    tushare: TushareConfig = Field(default_factory=TushareConfig)
    trading: TradingConfig = Field(default_factory=TradingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    
    @model_validator(mode='after')
    def validate_environment_specific(self) -> 'Settings':
        """验证环境特定配置"""
        if self.ENVIRONMENT == Environment.PRODUCTION:
            if self.DEBUG:
                raise ValueError('生产环境不能启用调试模式')
            if self.security.SECRET_KEY == "your-secret-key-here":
                raise ValueError('生产环境必须设置安全的密钥')
        return self
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例"""
    return settings


def get_database_url() -> str:
    """获取数据库URL"""
    return settings.database.get_mysql_url()


def is_production() -> bool:
    """检查是否为生产环境"""
    return settings.ENVIRONMENT == Environment.PRODUCTION


def is_development() -> bool:
    """检查是否为开发环境"""
    return settings.ENVIRONMENT == Environment.DEVELOPMENT


def is_testing() -> bool:
    """检查是否为测试环境"""
    return settings.ENVIRONMENT == Environment.TESTING