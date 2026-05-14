"""数据库备份工具 - 使用 pg_dump 创建压缩备份。"""
import os
import platform
import subprocess
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _default_exports_dir() -> str:
    """根据平台返回默认的导出目录。"""
    if platform.system() == 'Windows':
        # Windows 本地开发：使用 backend/exports 目录
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'exports')
    # Docker 环境：使用 /app/exports
    return '/app/exports'


def backup_database(database_url: str, exports_dir: str | None = None) -> str | None:
    """
    创建数据库的压缩备份。

    Args:
        database_url: PostgreSQL 连接 URL (postgresql://user:pass@host:port/dbname)
        exports_dir: 备份文件输出目录，None 则使用默认目录。

    Returns:
        备份文件路径，失败返回 None。
    """
    if exports_dir is None:
        exports_dir = _default_exports_dir()

    try:
        os.makedirs(exports_dir, exist_ok=True)

        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f'db_backup_{timestamp}.sql.gz'
        filepath = os.path.join(exports_dir, filename)

        logger.info(f'开始数据库备份: {filepath}')

        is_windows = platform.system() == 'Windows'

        if is_windows:
            # Windows 不支持 gzip 管道，直接保存为 .sql 文件
            filepath = filepath.replace('.sql.gz', '.sql')
            cmd = ['pg_dump', '--no-owner', '--no-acl', '-f', filepath, database_url]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f'pg_dump 失败 (退出码 {result.returncode}): {result.stderr}')
                if os.path.exists(filepath):
                    os.remove(filepath)
                return None
        else:
            # Linux/Docker：使用 pg_dump | gzip 管道
            cmd = f"pg_dump --no-owner --no-acl '{database_url}' | gzip > '{filepath}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f'备份命令失败: {result.stderr}')
                if os.path.exists(filepath):
                    os.remove(filepath)
                return None

        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        logger.info(f'数据库备份完成: {filepath} ({size_mb:.2f} MB)')
        return filepath

    except FileNotFoundError:
        logger.error('pg_dump 未找到。请在 Docker 镜像中安装 postgresql-client。')
        return None
    except Exception as e:
        logger.error(f'数据库备份失败: {e}', exc_info=True)
        return None