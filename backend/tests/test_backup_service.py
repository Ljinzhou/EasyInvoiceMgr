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


def test_restore_legacy_pg_dump_rebuilds_database(app, service, db_path):
    """旧版 pg_dump 备份：重建库 → 灌数据 → 标记 Alembic 版本。"""
    import shutil
    from pathlib import Path

    from sqlalchemy import text

    from models import db, User

    _insert_user(app, 'wiped_by_restore')

    fixture = Path(__file__).parent / 'fixtures' / 'legacy_dump_sample.sql'
    legacy_sql = str(Path(db_path).parent / 'db_dump.sql')
    shutil.copyfile(fixture, legacy_sql)

    service._restore_database('sqlite:///' + db_path.replace('\\', '/'), legacy_sql, str(Path(db_path).parent))

    with app.app_context():
        usernames = [row[0] for row in db.session.execute(
            text('SELECT username FROM users ORDER BY user_id')
        )]
        assert usernames == ['admin', '张三', 'tab\tname']
        assert User.query.count() == 3
        versions = db.session.execute(text('SELECT version_num FROM alembic_version')).fetchall()
        assert versions, '恢复后必须写入 alembic_version，否则下次启动会重复建表'


def test_restore_from_file_survives_open_engine_handles(app, service, db_path):
    """恢复线程替换数据库文件时，调用方会话可能仍持有 SQLite 句柄。

    Windows 上删除被占用的库文件会抛 WinError 32，恢复必须照常成功。
    """
    import shutil
    import tarfile
    from pathlib import Path

    from sqlalchemy import text

    from models import BackupRecord, db

    work_dir = Path(db_path).parent
    staging = work_dir / 'legacy_staging'
    staging.mkdir(exist_ok=True)
    shutil.copyfile(
        Path(__file__).parent / 'fixtures' / 'legacy_dump_sample.sql',
        staging / 'db_dump.sql',
    )

    archive_path = str(work_dir / 'legacy_restore.tar.gz')
    with tarfile.open(archive_path, 'w:gz') as tar:
        tar.add(str(staging / 'db_dump.sql'), arcname='db_dump.sql')

    with app.app_context():
        record = BackupRecord(backup_type='restore', backup_scope='full', status='pending')
        db.session.add(record)
        db.session.commit()
        record_id = record.id

        # 故意保留一个已检出连接的会话，模拟发起恢复的请求线程持有句柄
        db.session.execute(text('SELECT count(*) FROM users')).fetchone()

        service.restore_from_file(record_id, archive_path)

        db.session.remove()
        usernames = [
            row[0] for row in db.session.execute(text('SELECT username FROM users ORDER BY user_id'))
        ]
        assert usernames == ['admin', '张三', 'tab\tname']
        completed = db.session.execute(
            text("SELECT count(*) FROM backup_records WHERE backup_type='restore' AND status='completed'")
        ).scalar()
        assert completed == 1, '恢复完成后必须留下一条 completed 的恢复记录'
