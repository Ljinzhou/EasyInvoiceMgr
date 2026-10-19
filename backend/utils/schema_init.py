"""数据库结构初始化：启动与恢复备份后共用。"""
import logging

from sqlalchemy import inspect

logger = logging.getLogger(__name__)


def ensure_schema():
    """幂等地保证数据库结构与当前模型一致。

    - 已有 alembic_version：执行待定迁移
    - 有业务表但无版本表：标记为当前 head
    - 空库（含刚被换文件/刚建出的 SQLite 文件）：按模型建表并标记 head
    """
    from flask_migrate import stamp, upgrade
    from models import db

    existing_tables = set(inspect(db.engine).get_table_names())

    if 'alembic_version' in existing_tables:
        logger.info('检测到 Alembic 版本控制，执行待定迁移...')
        upgrade()
        logger.info('数据库迁移完成')
        return

    if 'users' in existing_tables:
        logger.info('检测到已有数据库结构，标记为当前版本...')
        stamp(revision='head')
        logger.info('已标记数据库版本为当前 head')
        return

    logger.info('未检测到数据库结构，按模型创建全部表...')
    db.create_all()
    stamp(revision='head')
    logger.info('数据库结构创建完成')
