"""启动流程测试：真实跑一次 create_app()，确认不再等待 PostgreSQL。"""
import os
import sqlite3
import subprocess
import sys
import time

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_create_app_bootstraps_schema_without_waiting(tmp_path):
    db_file = tmp_path / 'boot.sqlite'
    database_url = 'sqlite:///' + str(db_file).replace('\\', '/')

    env = os.environ.copy()
    env.update({
        'DATABASE_URL': database_url,
        'SECRET_KEY': 'boot-secret',
        'JWT_SECRET_KEY': 'boot-jwt-secret',
        'ADMIN_PASSWORD': 'admin',
        'PYTHONPATH': BACKEND_DIR,
    })

    started = time.time()
    completed = subprocess.run(
        [sys.executable, '-c', 'from app import create_app; create_app(); print("BOOT_OK")'],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=120,
    )
    elapsed = time.time() - started

    assert completed.returncode == 0, completed.stderr[-3000:]
    assert 'BOOT_OK' in completed.stdout
    assert db_file.exists()
    # 旧实现在等 PG initdb，固定空转 30 秒；新实现必须远低于这个值
    assert elapsed < 20, f'启动耗时 {elapsed:.1f}s，疑似仍在等待数据库初始化'

    connection = sqlite3.connect(str(db_file))
    try:
        tables = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        version = connection.execute('SELECT version_num FROM alembic_version').fetchone()
    finally:
        connection.close()

    assert {'users', 'events', 'operation_logs', 'alembic_version'}.issubset(tables)
    assert version is not None
