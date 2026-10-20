"""回归测试：只允许 SQLite 方言，且 SQLite 专用连接参数不能外泄给其他方言。

背景：迁移完成后 `backend/.env` 里残留的 `DATABASE_URL=postgresql://...`
曾把 `check_same_thread` 传给 psycopg2，启动时报
`invalid dsn: invalid connection option "check_same_thread"`。
"""
import importlib
import os
import subprocess
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _reload_config(monkeypatch, database_url):
    if database_url is None:
        monkeypatch.delenv('DATABASE_URL', raising=False)
    else:
        monkeypatch.setenv('DATABASE_URL', database_url)
    import config
    return importlib.reload(config)


def test_sqlite_url_gets_thread_and_lock_options(monkeypatch, tmp_path):
    sqlite_uri = 'sqlite:///' + (tmp_path / 'x.sqlite').as_posix()
    config = _reload_config(monkeypatch, sqlite_uri)
    options = config.Config.SQLALCHEMY_ENGINE_OPTIONS
    assert options['connect_args']['check_same_thread'] is False
    assert options['connect_args']['timeout'] == 30


def test_default_url_without_env_is_sqlite(monkeypatch):
    config = _reload_config(monkeypatch, None)
    assert config.Config.SQLALCHEMY_DATABASE_URI.startswith('sqlite:///')


def test_non_sqlite_url_gets_no_sqlite_only_options(monkeypatch):
    config = _reload_config(
        monkeypatch, 'postgresql://postgres:root@localhost:5432/easy_invoice_mgr')
    # 关键：不能把 check_same_thread 传给别的方言，否则驱动直接抛 invalid dsn
    assert config.Config.SQLALCHEMY_ENGINE_OPTIONS == {}
    assert config.Config.SQLALCHEMY_DATABASE_URI.startswith('postgresql://')


def test_create_app_rejects_non_sqlite_database(tmp_path):
    env = dict(os.environ)
    env.update({
        'DATABASE_URL': 'postgresql://postgres:root@localhost:5432/easy_invoice_mgr',
        'SECRET_KEY': 'test-secret',
        'JWT_SECRET_KEY': 'test-jwt-secret',
        'PYTHONIOENCODING': 'utf-8',
    })
    result = subprocess.run(
        [sys.executable, '-c', 'from app import create_app; create_app()'],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=120,
    )
    assert result.returncode != 0
    output = (result.stdout or '') + (result.stderr or '')
    assert '只支持 SQLite' in output
    # 报错要指向配置来源，而不是把驱动层的 dsn 报错抛给使用者
    assert 'DATABASE_URL' in output
