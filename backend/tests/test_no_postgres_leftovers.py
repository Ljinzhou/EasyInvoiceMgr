"""守卫测试：迁移完成后后端不应再残留 PostgreSQL 专用代码。"""
import os

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.dirname(BACKEND_DIR)
FORBIDDEN = ('psycopg2', 'pg_dump', 'pg_restore', 'base.sql')
SKIP_DIRS = {'venv', 'tests', '__pycache__', 'migrations', '.pytest_cache'}
# 旧版备份导入器必须处理 pg_dump 的文本格式，允许出现该字样
ALLOWED_FILES = {os.path.join('utils', 'legacy_pg_dump.py'),
                 os.path.join('utils', 'backup_service.py')}

# 部署侧同样不允许再出现 PostgreSQL：驱动、服务、端口、数据卷
DEPLOY_FILES = [
    os.path.join(BACKEND_DIR, 'requirements.txt'),
    os.path.join(BACKEND_DIR, 'requirements-dev.txt'),
    os.path.join(BACKEND_DIR, 'Dockerfile'),
    os.path.join(PROJECT_DIR, 'docker-compose.yml'),
    os.path.join(PROJECT_DIR, 'dev.ps1'),
    os.path.join(PROJECT_DIR, 'dev.bat'),
]
DEPLOY_FORBIDDEN = ('psycopg', 'postgres', 'pgdata', '5432', 'postgresql-client')


def _iter_sources():
    for root, dirs, files in os.walk(BACKEND_DIR):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
        for name in files:
            if name.endswith('.py'):
                yield os.path.join(root, name)


def test_no_postgres_specific_code_remains():
    offenders = []
    for path in _iter_sources():
        rel = os.path.relpath(path, BACKEND_DIR)
        if rel in ALLOWED_FILES:
            continue
        with open(path, 'r', encoding='utf-8', errors='ignore') as handle:
            for lineno, line in enumerate(handle, start=1):
                for token in FORBIDDEN:
                    if token in line:
                        offenders.append(f'{rel}:{lineno}: {line.strip()}')
    assert offenders == [], '仍有 PostgreSQL 专用残留:\n' + '\n'.join(offenders)


def test_postgres_artifacts_are_deleted():
    assert not os.path.exists(os.path.join(BACKEND_DIR, 'sql', 'base.sql'))
    assert not os.path.exists(os.path.join(BACKEND_DIR, 'migrate.py'))
    assert not os.path.exists(os.path.join(BACKEND_DIR, 'utils', 'db_backup.py'))


def test_deployment_files_have_no_postgres():
    """依赖清单、Dockerfile、compose、本地启动脚本里不能再有 PG。"""
    offenders = []
    for path in DEPLOY_FILES:
        if not os.path.exists(path):
            continue
        with open(path, 'r', encoding='utf-8', errors='ignore') as handle:
            for lineno, line in enumerate(handle, start=1):
                lowered = line.lower()
                for token in DEPLOY_FORBIDDEN:
                    if token in lowered:
                        offenders.append(
                            f'{os.path.basename(path)}:{lineno}: {line.strip()}')
    assert offenders == [], '部署配置仍有 PostgreSQL 残留:\n' + '\n'.join(offenders)


def test_default_database_url_is_sqlite():
    """不设 DATABASE_URL 时必须落到 SQLite 文件库。"""
    from config import _default_database_url

    assert _default_database_url().startswith('sqlite:///')

