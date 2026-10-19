"""SQLite 迁移的三个硬点回归测试。"""
from datetime import datetime, timezone


def test_user_primary_key_autoincrements(app):
    """BigInteger 主键在 SQLite 上必须能自增，否则插入直接失败。"""
    from models import db, User

    with app.app_context():
        user = User(username='pk_probe', password_hash='x', real_name='主键探针')
        db.session.add(user)
        db.session.commit()
        assert user.user_id == 1


def test_operation_log_primary_key_autoincrements(app):
    from models import db, User
    from utils.operation_log import OperationLog

    with app.app_context():
        user = User(username='log_probe', password_hash='x', real_name='日志探针')
        db.session.add(user)
        db.session.commit()

        log = OperationLog(
            user_id=user.user_id,
            username=user.username,
            action_type='test',
            action_description='探针',
        )
        db.session.add(log)
        db.session.commit()
        assert log.log_id == 1


def test_datetime_roundtrip_keeps_utc_timezone(app):
    """写 aware UTC，读出来仍应是 aware UTC；当前 SQLite 会退化成 naive。"""
    from models import db, User

    with app.app_context():
        moment = datetime(2026, 5, 16, 12, 0, 0, tzinfo=timezone.utc)
        user = User(
            username='tz_probe',
            password_hash='x',
            real_name='时区探针',
            created_at=moment,
        )
        db.session.add(user)
        db.session.commit()
        db.session.expire_all()

        loaded = db.session.get(User, user.user_id)
        assert loaded.created_at.tzinfo is not None
        assert loaded.created_at == moment
