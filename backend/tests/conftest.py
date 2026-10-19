"""pytest 公共夹具：构造只带数据库的最小 Flask 应用。"""
import os
import sqlite3
import sys

import pytest
from flask import Flask

# 让 tests 目录能 import backend 根目录下的 models / utils
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# 导入一次，确保 operation_logs 表注册进 db.metadata
import models  # noqa: E402,F401
import utils.operation_log  # noqa: E402,F401


@pytest.fixture()
def db_path(tmp_path):
    """临时 SQLite 数据库文件路径。"""
    return str(tmp_path / 'test.sqlite')


@pytest.fixture()
def app(db_path):
    """最小 Flask 应用：只初始化数据库并按模型建表。"""
    from flask_migrate import Migrate

    from models import db

    flask_app = Flask(__name__)
    flask_app.config.update(
        SQLALCHEMY_DATABASE_URI='sqlite:///' + db_path.replace('\\', '/'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY='test-secret',
        JWT_SECRET_KEY='test-jwt-secret',
    )
    db.init_app(flask_app)
    # 与 app.py 一致：ensure_schema() 靠 flask_migrate 读取/写入 alembic_version
    Migrate(flask_app, db, directory=os.path.join(BACKEND_DIR, 'migrations'))
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()


@pytest.fixture()
def sqlite_connection(db_path, app):
    """绕过 ORM 直连数据库文件，用于断言真实存储格式。"""
    connection = sqlite3.connect(db_path)
    try:
        yield connection
    finally:
        connection.close()
