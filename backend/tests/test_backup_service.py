"""备份与恢复的文件级行为测试。"""
import os
import sqlite3

import pytest


@pytest.fixture()
def service(app):
    from utils.backup_service import BackupService

    return BackupService(app)


def _insert_user(app, username):
    from models import db, User

    with app.app_context():
        user = User(username=username, password_hash='x', real_name=username)
        db.session.add(user)
        db.session.commit()
        return user.user_id


def _usernames(db_file):
    connection = sqlite3.connect(db_file)
    try:
        return [row[0] for row in connection.execute('SELECT username FROM users ORDER BY user_id')]
    finally:
        connection.close()


def test_dump_database_produces_sqlite_snapshot(app, service, db_path, tmp_path):
    _insert_user(app, 'alice')
    dump_dir = tmp_path / 'dump'
    dump_dir.mkdir()
    dump_path = service._dump_database('sqlite:///' + db_path.replace('\\', '/'), str(dump_dir))

    assert dump_path is not None
    assert os.path.basename(dump_path) == 'db_dump.sqlite3'
    assert _usernames(dump_path) == ['alice']


def test_restore_database_replaces_file(app, service, db_path, tmp_path):
    _insert_user(app, 'alice')
    dump_dir = tmp_path / 'dump'
    dump_dir.mkdir()
    dump_path = service._dump_database('sqlite:///' + db_path.replace('\\', '/'), str(dump_dir))

    _insert_user(app, 'bob')
    assert _usernames(db_path) == ['alice', 'bob']

    staging_dir = tmp_path / 'staging'
    staging_dir.mkdir()
    service._restore_database('sqlite:///' + db_path.replace('\\', '/'), dump_path, str(staging_dir))

    assert _usernames(db_path) == ['alice']
    # 替换后连接池仍然可用
    with app.app_context():
        from models import User
        assert User.query.count() == 1
