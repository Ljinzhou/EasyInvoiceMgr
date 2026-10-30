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


# 早于「加入申请」功能的 dump：events 没有 join_review_mode、
# event_members 没有 joined_by / join_source
DUMP_WITHOUT_NEW_COLUMNS = r"""
COPY public.users (user_id, username, password_hash, real_name, user_type, account_status, created_at, is_deleted) FROM stdin;
1	admin	hash1	管理员	admin	active	2025-08-01 12:34:56.789+00	f
\.

COPY public.events (event_id, event_name, status, creator_id, total_budget, created_at, is_deleted) FROM stdin;
11	社团经费	ongoing	1	1000.00	2025-08-01 12:34:56.789+00	f
\.

COPY public.event_members (id, event_id, user_id, role_in_event, join_time, created_at, is_deleted) FROM stdin;
21	11	1	teacher	2025-08-01 12:34:56.789+00	2025-08-01 12:34:56.789+00	f
\.
"""


def test_import_fills_defaults_for_columns_added_after_dump(app, db_path):
    """旧 dump 缺少模型后来新增的列时，按默认值补齐而不是撞 NOT NULL。"""
    from models import Event, EventMember, db
    from utils.legacy_pg_dump import import_pg_dump_text

    report = import_pg_dump_text(db_path, DUMP_WITHOUT_NEW_COLUMNS)

    assert report.row_counts == {'users': 1, 'events': 1, 'event_members': 1}
    assert report.foreign_key_violations == []

    with app.app_context():
        event = db.session.get(Event, 11)
        assert event.join_review_mode == 'manual'

        member = db.session.get(EventMember, 21)
        assert member.join_source == 'legacy'   # 导入后回填的历史语义
        assert member.joined_by is None          # 旧数据没有审核人

