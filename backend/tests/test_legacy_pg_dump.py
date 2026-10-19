"""旧版 PostgreSQL dump 导入器测试。"""
import os
from datetime import datetime, timezone

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'legacy_dump_sample.sql')


def _fixture_text():
    with open(FIXTURE, 'r', encoding='utf-8') as handle:
        return handle.read()


def test_parse_copy_blocks_handles_escapes_and_nulls():
    from utils.legacy_pg_dump import parse_copy_blocks

    blocks = {block.table: block for block in parse_copy_blocks(_fixture_text())}

    assert set(blocks) == {'users', 'system_configs', 'ignored_table'}
    assert blocks['users'].columns[:3] == ['user_id', 'username', 'password_hash']
    assert blocks['users'].rows[0][0] == '1'
    assert blocks['users'].rows[2][1] == 'tab\tname'
    assert blocks['users'].rows[2][3] == '反斜杠\\名字'
    assert blocks['users'].rows[2][6] is None


def test_timestamp_is_converted_to_naive_utc():
    from models import User
    from utils.legacy_pg_dump import _coerce_value

    column = User.__table__.columns['created_at']

    # +00 偏移：原样保留墙钟时间
    assert _coerce_value(column, '2025-08-01 12:34:56.789+00') == '2025-08-01 12:34:56.789000'
    # +08 偏移：换算成 UTC
    assert _coerce_value(column, '2025-08-02 08:00:00+08') == '2025-08-02 00:00:00.000000'


def test_import_writes_rows_and_skips_unknown(app, db_path):
    from models import db, SystemConfig, User
    from utils.legacy_pg_dump import import_pg_dump_text

    report = import_pg_dump_text(db_path, _fixture_text())

    assert report.row_counts == {'users': 3, 'system_configs': 2}
    assert 'ignored_table' in report.skipped_tables
    assert report.skipped_columns['users'] == ['legacy_flag']
    assert report.foreign_key_violations == []

    with app.app_context():
        assert User.query.count() == 3
        admin = db.session.get(User, 1)
        assert admin.username == 'admin'
        assert admin.is_deleted is False
        assert admin.created_at == datetime(2025, 8, 1, 12, 34, 56, 789000, tzinfo=timezone.utc)
        assert SystemConfig.query.count() == 2
