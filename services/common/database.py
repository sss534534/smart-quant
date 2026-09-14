"""
数据库配置和连接管理
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from typing import Generator
import logging

from .config import settings

logger = logging.getLogger(__name__)


def create_database_engine():
    """创建数据库引擎"""
    engine = create_engine(
        settings.database.get_mysql_url(),
        pool_size=settings.database.MYSQL_POOL_SIZE,
        max_overflow=settings.database.MYSQL_MAX_OVERFLOW,
        pool_recycle=settings.database.MYSQL_POOL_RECYCLE,
        pool_pre_ping=True,
        poolclass=QueuePool,
        echo=settings.DEBUG,
    )
    
    logger.info(
        "Database engine created",
        host=settings.database.MYSQL_HOST,
        port=settings.database.MYSQL_PORT,
        database=settings.database.MYSQL_DATABASE,
        pool_size=settings.database.MYSQL_POOL_SIZE,
    )
    
    return engine


# 创建引擎和会话
engine = create_database_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator:
    """
    获取数据库会话
    
    Yields:
        Session: 数据库会话
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error("Database session error", error=str(e))
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """初始化数据库"""
    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        raise


def check_db_connection() -> bool:
    """检查数据库连接"""
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return True
    except Exception as e:
        logger.error("Database connection check failed", error=str(e))
        return False


def get_db_info() -> dict:
    """获取数据库信息"""
    return {
        "host": settings.database.MYSQL_HOST,
        "port": settings.database.MYSQL_PORT,
        "database": settings.database.MYSQL_DATABASE,
        "pool_size": settings.database.MYSQL_POOL_SIZE,
        "max_overflow": settings.database.MYSQL_MAX_OVERFLOW,
        "pool_recycle": settings.database.MYSQL_POOL_RECYCLE,
    }