"""SQLite 引擎辅助：连接串解析 + 连接级 PRAGMA。"""
import logging
import os

from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

_SQLITE_PREFIX = 'sqlite:///'


def database_file_path(database_uri: str) -> str:
    """从 SQLAlchemy URI 解析出 SQLite 数据库文件的绝对路径。"""
    if not database_uri.startswith(_SQLITE_PREFIX):
        raise ValueError(f'仅支持 SQLite 数据库，当前连接串为: {database_uri}')
    path = database_uri[len(_SQLITE_PREFIX):]
    if not path or path.startswith(':'):
        raise ValueError(f'无法从连接串解析数据库文件路径: {database_uri}')
    return os.path.abspath(path)


def register_sqlite_pragmas(engine: Engine) -> None:
    """为每个新连接设置 SQLite PRAGMA。

    - journal_mode=WAL：读写不互相阻塞，导出/备份线程不会卡住请求
    - foreign_keys=ON：SQLite 默认不强制外键，不开启等于静默丢掉引用完整性
    - busy_timeout=30000：写锁竞争时最多等待 30 秒而不是立刻抛 database is locked
    - synchronous=NORMAL：WAL 下的安全/性能平衡点
    """
    if engine.dialect.name != 'sqlite':
        logger.warning(f'当前数据库方言为 {engine.dialect.name}，跳过 SQLite PRAGMA 设置')
        return
    if getattr(engine, '_easy_invoice_pragma_ready', False):
        return

    @event.listens_for(engine, 'connect')
    def _apply_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute('PRAGMA journal_mode=WAL')
            cursor.execute('PRAGMA foreign_keys=ON')
            cursor.execute('PRAGMA busy_timeout=30000')
            cursor.execute('PRAGMA synchronous=NORMAL')
        finally:
            cursor.close()

    engine._easy_invoice_pragma_ready = True
    logger.info('SQLite PRAGMA 已注册: WAL / foreign_keys / busy_timeout')
