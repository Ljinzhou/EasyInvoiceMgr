"""用真实旧备份验证恢复链路（临时脚本，验证后删除）。"""
import os
import sys
import tempfile

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

TEMP_DIR = tempfile.mkdtemp(prefix='easyinvoice_verify_')
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(TEMP_DIR, 'verify.sqlite').replace('\\', '/')
os.environ.setdefault('SECRET_KEY', 'verify-secret')
os.environ.setdefault('JWT_SECRET_KEY', 'verify-jwt-secret')
os.environ['ADMIN_PASSWORD'] = 'admin'

from sqlalchemy import text  # noqa: E402

from app import create_app  # noqa: E402
from models import db  # noqa: E402
from utils.backup_service import get_backup_service  # noqa: E402


def main(archive_path):
    application = create_app()
    print(f'临时数据库文件: {os.environ["DATABASE_URL"]}')
    with application.app_context():
        from models import BackupRecord

        record = BackupRecord(backup_type='restore', backup_scope='full', status='pending')
        db.session.add(record)
        db.session.commit()

        service = get_backup_service()
        # 走与「上传备份恢复」路由完全相同的入口
        new_id = service.restore_from_file(record.id, archive_path)
        print(f'恢复调用返回 id={new_id}')

        for table in db.metadata.sorted_tables:
            count = db.session.execute(text(f'SELECT count(*) FROM "{table.name}"')).scalar()
            print(f'{table.name}\t{count}')

        missing = db.session.execute(text('PRAGMA foreign_key_check')).fetchall()
        print(f'外键异常条数: {len(missing)}')
        if missing:
            print(missing[:5])

        for done in db.session.execute(
            text(
                'SELECT id, backup_type, backup_scope, status, progress_message, '
                'error_message FROM backup_records ORDER BY id'
            )
        ).fetchall():
            print('恢复记录:', done)

        for name in ('users', 'events', 'purchase_records', 'invoices', 'vouchers'):
            count = db.session.execute(text(f'SELECT count(*) FROM "{name}"')).scalar()
            print(f'抽查 {name} = {count}')

        admin = db.session.execute(
            text("SELECT username, user_type FROM users WHERE username='admin'")
        ).fetchone()
        print('抽查 admin 账号:', admin)


if __name__ == '__main__':
    main(sys.argv[1])
