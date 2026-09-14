"""Alembic 环境配置"""
import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# 将 services 目录加入 sys.path 以便导入 common 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services'))

# 导入配置和模型
from common.database import Base
from common import models  # noqa: F401  确保所有模型被注册到 Base.metadata
from common.config import get_database_url

config = context.config

# 从项目配置中获取数据库 URL（本地无 MySQL 时使用 SQLite 生成迁移）
import os
if os.environ.get('ALEMBIC_USE_SQLITE'):
    config.set_main_option('sqlalchemy.url', 'sqlite:///./alembic_tmp.db')
else:
    config.set_main_option('sqlalchemy.url', get_database_url())

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """以离线模式运行迁移"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """以在线模式运行迁移"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
