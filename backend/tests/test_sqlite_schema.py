"""SQLite 建表冒烟测试：确认全部模型都能在 SQLite 上建出来。"""
from sqlalchemy import inspect

EXPECTED_TABLES = {
    'users', 'events', 'event_members', 'invoices', 'vouchers',
    'purchase_records', 'invitation_codes', 'system_configs',
    'export_tasks', 'backup_records', 'operation_logs',
}


def test_create_all_builds_every_table(app):
    from models import db

    existing = set(inspect(db.engine).get_table_names())
    assert EXPECTED_TABLES.issubset(existing)


def test_primary_keys_are_integer_type(app, sqlite_connection):
    """SQLite 只有 INTEGER 主键才能自增，BIGINT 主键会插入失败。"""
    rows = sqlite_connection.execute("PRAGMA table_info('users')").fetchall()
    primary_keys = [row for row in rows if row[5]]
    assert [row[1] for row in primary_keys] == ['user_id']
    assert primary_keys[0][2].upper() == 'INTEGER'
