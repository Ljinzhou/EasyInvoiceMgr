"""备份服务 - 全量备份/恢复/定时调度/自动清理"""
import os
import json
import shutil
import tarfile
import logging
import platform
import subprocess
import tempfile
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# 模块级单例
_backup_service = None
_scheduler = None

# 超过该时长没有任何进度更新的 pending/running 记录，视为孤儿记录（僵尸任务）
STALE_BACKUP_MINUTES = 30


class BackupService:
    def __init__(self, app):
        self.app = app
        self.exports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'exports')
        os.makedirs(self.exports_dir, exist_ok=True)

    def recover_stale_backups(self, max_age_minutes=None):
        """把僵尸备份记录（长期停在 pending/running）标记为失败，返回回收条数。

        背景：备份线程是进程内的 daemon 线程，进程一旦被杀/重启，跑到一半的记录
        就永远停在 running，而手动备份接口会以「已有备份任务正在执行」返回 409，
        导致备份功能被一条历史记录永久卡死（迁移前的 PostgreSQL 时代遗留记录被
        导入后就会这样）。这里以最后更新时间作为心跳，超出阈值即判定为中断。

        Args:
            max_age_minutes: None 表示无条件回收——进程刚启动时调用，
                此时进程内不可能存在存活的后台备份线程，凡是未结束的记录都是孤儿。
                传入分钟数则只回收超过该时长没有进展的记录，用于长时间运行的进程兜底。
        """
        from datetime import timedelta

        from sqlalchemy import func, or_

        from models import BackupRecord, db

        query = BackupRecord.query.filter(BackupRecord.status.in_(['pending', 'running']))
        if max_age_minutes is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
            query = query.filter(
                or_(
                    func.coalesce(BackupRecord.updated_at, BackupRecord.created_at) < cutoff,
                    BackupRecord.created_at.is_(None),
                )
            )
        stale = query.all()
        if not stale:
            return 0

        now = datetime.now(timezone.utc)
        stale_ids = []
        for record in stale:
            stale_ids.append(record.id)
            record.status = 'failed'
            record.error_message = (
                '备份进程已中断（服务重启或线程异常退出），该记录已自动标记为失败，请重新发起备份'
            )
            record.progress_message = '备份中断，已标记为失败'
            record.completed_at = now

        try:
            db.session.commit()
        except Exception as error:
            db.session.rollback()
            logger.error(f'回收僵尸备份记录失败: {error}', exc_info=True)
            raise

        logger.warning(f'回收僵尸备份记录 {len(stale_ids)} 条: id={stale_ids}')
        return len(stale_ids)

    def run_backup(self, record_id):
        """后台线程：执行全量备份"""
        with self.app.app_context():
            from models import db, BackupRecord, SystemConfig
            from utils.crypto_utils import decrypt_value

            record = db.session.get(BackupRecord, record_id)
            if not record:
                return

            record.status = 'running'
            record.progress = 0
            record.progress_message = '正在准备备份...'
            db.session.commit()

            try:
                uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
                invoices_dir = os.path.join(uploads_dir, 'invoices')
                avatars_dir = os.path.join(uploads_dir, 'avatars')

                with tempfile.TemporaryDirectory() as staging_dir:
                    # 步骤1：数据库备份 (0-30%)
                    record.progress = 5
                    record.progress_message = '正在备份数据库...'
                    db.session.commit()

                    db_url = self.app.config.get('SQLALCHEMY_DATABASE_URI')
                    db_dump_path = self._dump_database(db_url, staging_dir)
                    if not db_dump_path:
                        raise RuntimeError('数据库备份失败，请检查数据库文件是否可读')

                    record.progress = 30
                    record.progress_message = '数据库备份完成'
                    db.session.commit()

                    # 步骤2：复制上传文件 (30-70%)
                    file_count = 0
                    record.progress = 35
                    record.progress_message = '正在备份发票文件...'
                    db.session.commit()

                    if os.path.isdir(invoices_dir):
                        dest_invoices = os.path.join(staging_dir, 'invoices')
                        shutil.copytree(invoices_dir, dest_invoices, dirs_exist_ok=True)
                        file_count += self._count_files(dest_invoices)

                    record.progress = 50
                    record.progress_message = '正在备份用户头像...'
                    db.session.commit()

                    if os.path.isdir(avatars_dir):
                        dest_avatars = os.path.join(staging_dir, 'avatars')
                        shutil.copytree(avatars_dir, dest_avatars, dirs_exist_ok=True)
                        file_count += self._count_files(dest_avatars)

                    record.progress = 70
                    record.progress_message = '文件备份完成'
                    db.session.commit()

                    # 步骤3：导出系统配置 (70-80%)
                    record.progress = 75
                    record.progress_message = '正在导出系统配置...'
                    db.session.commit()

                    configs = SystemConfig.query.all()
                    config_list = []
                    for c in configs:
                        value = c.config_value
                        if c.is_encrypted and value:
                            try:
                                value = decrypt_value(value)
                            except Exception:
                                value = ''
                        config_list.append({
                            'config_key': c.config_key,
                            'config_value': value,
                            'is_encrypted': c.is_encrypted,
                            'description': c.description or '',
                        })
                    config_path = os.path.join(staging_dir, 'system_config.json')
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(config_list, f, ensure_ascii=False, indent=2)

                    record.progress = 80
                    record.progress_message = '系统配置导出完成'
                    db.session.commit()

                    # 步骤4：创建 tar.gz 压缩包 (80-95%)
                    record.progress = 85
                    record.progress_message = '正在创建压缩包...'
                    db.session.commit()

                    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
                    archive_name = f'full_backup_{timestamp}.tar.gz'
                    archive_path = os.path.join(self.exports_dir, archive_name)

                    with tarfile.open(archive_path, 'w:gz') as tar:
                        # 添加数据库备份
                        db_arcname = os.path.basename(db_dump_path)
                        tar.add(db_dump_path, arcname=db_arcname)
                        file_count += 1

                        # 添加发票目录
                        if os.path.isdir(os.path.join(staging_dir, 'invoices')):
                            tar.add(os.path.join(staging_dir, 'invoices'), arcname='invoices')

                        # 添加头像目录
                        if os.path.isdir(os.path.join(staging_dir, 'avatars')):
                            tar.add(os.path.join(staging_dir, 'avatars'), arcname='avatars')

                        # 添加配置文件
                        tar.add(config_path, arcname='system_config.json')

                    record.progress = 95
                    record.progress_message = '压缩包创建完成'
                    db.session.commit()

                    # 步骤5：完成 (100%)
                    file_size = os.path.getsize(archive_path)
                    record.file_path = archive_path
                    record.file_size = file_size
                    record.file_count = file_count
                    record.status = 'completed'
                    record.progress = 100
                    record.progress_message = '备份完成'
                    record.completed_at = datetime.now(timezone.utc)
                    db.session.commit()

                    logger.info(f'全量备份完成: id={record_id}, 文件={archive_path}, 大小={file_size / (1024*1024):.2f} MB, 文件数={file_count}')

                    # 自动清理旧备份
                    self._cleanup_old_backups()

            except Exception as e:
                logger.error(f'备份失败: id={record_id}, error={str(e)}', exc_info=True)
                try:
                    record.status = 'failed'
                    record.error_message = str(e)
                    record.completed_at = datetime.now(timezone.utc)
                    db.session.commit()
                except Exception:
                    pass
            finally:
                try:
                    db.session.remove()
                except Exception:
                    pass

    def restore_backup(self, record_id):
        """后台线程：从备份恢复数据"""
        with self.app.app_context():
            from models import db, BackupRecord

            record = db.session.get(BackupRecord, record_id)
            if not record or record.status != 'completed' or not record.file_path:
                logger.error(f'恢复失败：备份记录无效 id={record_id}')
                return

            if not os.path.exists(record.file_path):
                logger.error(f'恢复失败：备份文件不存在 {record.file_path}')
                return

            # 创建临时恢复记录（仅用于 _do_restore 获取 created_by，
            # 该记录会被 DROP SCHEMA 销毁，_do_restore 结束时创建新完成记录）
            restore_record = BackupRecord(
                backup_type='restore',
                backup_scope='full',
                status='running',
                progress=0,
                progress_message='正在准备恢复...',
                created_by=record.created_by,
            )
            db.session.add(restore_record)
            db.session.commit()

            try:
                with tempfile.TemporaryDirectory() as staging_dir:
                    new_id = self._do_restore(restore_record, record.file_path, staging_dir)

                logger.info(f'数据恢复完成: 源备份id={record_id}, 新恢复记录id={new_id}')
            except Exception as e:
                logger.error(f'恢复失败: id={record_id}, error={str(e)}', exc_info=True)
                # 若 _restore_database 已执行则旧记录已销毁，创建失败日志
                try:
                    fail_record = BackupRecord(
                        backup_type='restore',
                        backup_scope='full',
                        status='failed',
                        error_message=str(e),
                        completed_at=datetime.now(timezone.utc),
                        created_by=record.created_by,
                    )
                    db.session.add(fail_record)
                    db.session.commit()
                except Exception:
                    pass
            finally:
                try:
                    db.session.remove()
                except Exception:
                    pass

    def restore_from_file(self, record_id, file_path):
        """后台线程：从上传的备份文件恢复数据"""
        with self.app.app_context():
            from models import db, BackupRecord

            record = db.session.get(BackupRecord, record_id)
            if not record:
                logger.error(f'恢复失败：恢复记录无效 id={record_id}')
                return

            if not os.path.exists(file_path):
                logger.error(f'恢复失败：上传文件不存在 {file_path}')
                record.status = 'failed'
                record.error_message = '上传文件不存在'
                db.session.commit()
                return

            record.status = 'running'
            record.progress = 0
            record.progress_message = '正在验证备份文件...'
            db.session.commit()

            try:
                # 先验证 tar.gz 结构
                try:
                    with tarfile.open(file_path, 'r:gz') as tar:
                        names = tar.getnames()
                        has_db = any(n.startswith('db_dump') for n in names)
                        if not has_db:
                            raise ValueError('备份文件中未找到数据库转储文件，请选择有效的系统备份')
                except tarfile.ReadError:
                    raise ValueError('文件不是有效的 tar.gz 压缩包')

                with tempfile.TemporaryDirectory() as staging_dir:
                    self._do_restore(record, file_path, staging_dir)
                # _do_restore 会在数据库恢复后创建新的完成记录
                # 旧 record 已随 DROP SCHEMA 销毁，无需再更新

            except Exception as e:
                logger.error(f'本地文件恢复失败: id={record_id}, error={str(e)}', exc_info=True)
                # 尝试记录失败状态；若 _restore_database 已执行则旧 record 已销毁，
                # 此时创建一条新的失败记录
                try:
                    existing = db.session.get(BackupRecord, record_id)
                    if existing:
                        existing.status = 'failed'
                        existing.error_message = str(e)
                        existing.completed_at = datetime.now(timezone.utc)
                    else:
                        # 旧记录已随 schema 删除，创建失败日志
                        fail_record = BackupRecord(
                            backup_type='restore',
                            backup_scope='full',
                            status='failed',
                            error_message=str(e),
                            completed_at=datetime.now(timezone.utc),
                        )
                        db.session.add(fail_record)
                    db.session.commit()
                except Exception:
                    pass
            finally:
                try:
                    db.session.remove()
                except Exception:
                    pass

    def _do_restore(self, record, archive_path, staging_dir):
        """从 tar.gz 压缩包恢复数据。

        重要：_restore_database 会整体替换数据库文件（含全部数据表），
        导致所有表（包括 backup_records）被销毁。因此 record 对象在
        数据库恢复后将变为无效，不可再提交。本方法会在恢复完成后
        创建一条新的 BackupRecord 作为恢复日志。
        返回新记录的 id。
        """
        from models import db, BackupRecord, User

        # 在数据库恢复前保存必要信息（之后 record 会失效）
        created_by = record.created_by

        # 解压备份文件
        record.progress = 5
        record.progress_message = '正在解压备份文件...'
        db.session.commit()

        with tarfile.open(archive_path, 'r:gz') as tar:
            tar.extractall(staging_dir)

        # 查找数据库备份文件：新版为 db_dump.sqlite3，旧版为 db_dump.sql(.gz)
        db_dump_path = None
        for file_name in sorted(os.listdir(staging_dir)):
            if not file_name.startswith('db_dump'):
                continue
            if file_name.endswith(('.sqlite3', '.sqlite', '.db', '.sql', '.sql.gz')):
                db_dump_path = os.path.join(staging_dir, file_name)
                break

        if not db_dump_path:
            raise RuntimeError('备份文件中未找到数据库转储文件')

        # 数据库恢复前最后的进度更新
        record.progress = 10
        record.progress_message = '正在恢复数据库...'
        db.session.commit()

        # 恢复数据库（会 DROP SCHEMA public CASCADE，record 将失效）
        db_url = self.app.config.get('SQLALCHEMY_DATABASE_URI')
        self._restore_database(db_url, db_dump_path, staging_dir)

        # === 此后 record 对象已随表一起销毁，不可再访问 ===
        db.session.expire_all()

        # 恢复文件（进度不再写入 DB，文件操作通常较快）
        uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')

        invoices_src = os.path.join(staging_dir, 'invoices')
        if os.path.isdir(invoices_src):
            invoices_dest = os.path.join(uploads_dir, 'invoices')
            shutil.copytree(invoices_src, invoices_dest, dirs_exist_ok=True)

        avatars_src = os.path.join(staging_dir, 'avatars')
        if os.path.isdir(avatars_src):
            avatars_dest = os.path.join(uploads_dir, 'avatars')
            shutil.copytree(avatars_src, avatars_dest, dirs_exist_ok=True)

        # 恢复系统配置
        config_json_path = os.path.join(staging_dir, 'system_config.json')
        if os.path.exists(config_json_path):
            self._import_system_config(config_json_path)

        # 旧 dump 里可能没有这个用户，SQLite 已开启外键强制，必须回退为 NULL
        creator_id = created_by
        if creator_id is not None and db.session.get(User, creator_id) is None:
            logger.warning(f'恢复记录的原创建者 id={creator_id} 不在恢复后的数据库中，改为 NULL')
            creator_id = None

        # 创建恢复完成记录（旧 record 已随数据库替换销毁）
        restore_record = BackupRecord(
            backup_type='restore',
            backup_scope='full',
            status='completed',
            progress=100,
            progress_message='恢复完成',
            completed_at=datetime.now(timezone.utc),
            created_by=creator_id,
        )
        db.session.add(restore_record)
        db.session.commit()

        logger.info(f'数据恢复完成: 恢复记录id={restore_record.id}')
        return restore_record.id

    def run_scheduled_backup(self):
        """定时任务入口：创建 scheduled 类型备份记录并执行"""
        with self.app.app_context():
            from models import db, BackupRecord

            # 先回收僵尸记录，否则一条历史遗留的 running 会让定时备份永久跳过
            self.recover_stale_backups(max_age_minutes=STALE_BACKUP_MINUTES)

            # 检查是否有正在运行的备份
            running = BackupRecord.query.filter(
                BackupRecord.status.in_(['pending', 'running']),
                BackupRecord.backup_type != 'restore'
            ).first()
            if running:
                logger.warning(f'跳过定时备份：已有备份任务正在运行 id={running.id}')
                return

            record = BackupRecord(
                backup_type='scheduled',
                backup_scope='full',
                status='pending',
            )
            db.session.add(record)
            db.session.commit()
            record_id = record.id

        # 在 app context 外启动线程
        import threading
        thread = threading.Thread(target=self.run_backup, args=(record_id,), daemon=True)
        thread.start()
        logger.info(f'定时备份已启动: id={record_id}')

    def _cleanup_old_backups(self):
        """自动清理旧备份，保留最近 N 个"""
        from models import db, BackupRecord, SystemConfig

        try:
            retention_config = SystemConfig.query.filter_by(config_key='backup_retention_count').first()
            retention_count = int(retention_config.config_value) if retention_config and retention_config.config_value else 10
        except (ValueError, TypeError):
            retention_count = 10

        completed = BackupRecord.query.filter_by(
            status='completed'
        ).filter(
            BackupRecord.backup_type.in_(['manual', 'scheduled'])
        ).order_by(BackupRecord.created_at.desc()).all()

        if len(completed) <= retention_count:
            return

        to_delete = completed[retention_count:]
        for record in to_delete:
            if record.file_path and os.path.exists(record.file_path):
                try:
                    os.remove(record.file_path)
                    logger.info(f'已清理旧备份文件: {record.file_path}')
                except Exception as e:
                    logger.warning(f'清理备份文件失败: {record.file_path}, error={str(e)}')
            db.session.delete(record)

        db.session.commit()
        logger.info(f'自动清理完成，删除了 {len(to_delete)} 个旧备份')

    def _dump_database(self, db_url, output_dir):
        """用 SQLite 在线备份 API 产出一致性快照（含 WAL 中未合并的内容）。"""
        import sqlite3

        from utils.db_engine import database_file_path

        source_path = database_file_path(db_url)
        if not os.path.exists(source_path):
            logger.error(f'数据库文件不存在，无法备份: {source_path}')
            return None

        dump_path = os.path.join(output_dir, 'db_dump.sqlite3')
        source = sqlite3.connect(source_path, timeout=30)
        destination = sqlite3.connect(dump_path)
        try:
            source.backup(destination)
        finally:
            destination.close()
            source.close()

        size_mb = os.path.getsize(dump_path) / (1024 * 1024)
        logger.info(f'数据库快照完成: {dump_path} ({size_mb:.2f} MB)')
        return dump_path

    def _restore_database(self, db_url, dump_path, staging_dir):
        """用备份里的数据库文件整体替换当前数据库。"""
        from utils.db_engine import database_file_path

        if dump_path.endswith('.gz'):
            import gzip

            sql_path = dump_path[:-3]
            with gzip.open(dump_path, 'rb') as source, open(sql_path, 'wb') as target:
                shutil.copyfileobj(source, target)
            dump_path = sql_path

        target_path = database_file_path(db_url)

        if dump_path.endswith(('.sqlite3', '.sqlite', '.db')):
            self._replace_database_file(target_path, dump_path)
            return

        if dump_path.endswith('.sql'):
            self._import_legacy_pg_dump(target_path, dump_path)
            return

        raise RuntimeError(f'无法识别的数据库备份文件: {os.path.basename(dump_path)}')

    def _disconnect_database(self):
        """丢弃会话并释放连接池，让 SQLite 文件句柄尽快归还给系统。"""
        from models import db

        db.session.remove()
        db.engine.dispose()

    def _replace_database_file(self, target_path, source_path):
        """用备份里的快照覆盖当前数据库。

        走 SQLite 在线备份 API 而不是替换文件：Windows 上只要有任一连接
        没关闭（恢复线程与请求线程并存时就会出现），删除或覆盖库文件都会
        抛 WinError 32；备份 API 只是连接级操作，不会碰到文件占用问题。
        """
        import sqlite3

        probe = sqlite3.connect(source_path)
        try:
            probe.execute('SELECT count(*) FROM sqlite_master').fetchone()
        finally:
            probe.close()

        self._disconnect_database()

        source = sqlite3.connect(source_path, timeout=30)
        destination = sqlite3.connect(target_path, timeout=30)
        try:
            source.backup(destination)
        finally:
            destination.close()
            source.close()

        self._disconnect_database()
        logger.info(f'数据库已由快照覆盖: {target_path}')

    def _reset_sqlite_schema(self):
        """原地清空数据库结构。

        不删除库文件：文件被其它会话占用时删除会失败，而原地 DROP 所有表
        同样能拿到一个干净的空库，且不受 Windows 文件锁影响。
        """
        from models import db
        from sqlalchemy import text

        self._disconnect_database()

        # 数据库文件可能还不存在，先建出合法库再 DROP
        db.create_all()
        with db.engine.begin() as connection:
            for table in reversed(db.metadata.sorted_tables):
                connection.execute(text(f'DROP TABLE IF EXISTS "{table.name}"'))
            connection.execute(text('DROP TABLE IF EXISTS alembic_version'))

        # 建回空表；旧 dump 里的 DDL 一律不执行
        db.create_all()
        db.session.commit()

    def _import_legacy_pg_dump(self, target_path, sql_path):
        """把旧版 PostgreSQL dump 恢复成全新的 SQLite 数据库。"""
        from utils.legacy_pg_dump import import_pg_dump_file
        from utils.schema_init import ensure_schema

        self._reset_sqlite_schema()

        report = import_pg_dump_file(target_path, sql_path)

        # 建表后没有 alembic_version，ensure_schema 会标记为 head
        ensure_schema()

        logger.info(f'旧版备份恢复完成: {report.summary()}')
        return report

    def _import_system_config(self, json_path):
        """从 JSON 文件恢复系统配置"""
        from models import db, SystemConfig
        from utils.crypto_utils import encrypt_value

        with open(json_path, 'r', encoding='utf-8') as f:
            config_list = json.load(f)

        for item in config_list:
            key = item.get('config_key')
            value = item.get('config_value', '')
            is_encrypted = item.get('is_encrypted', False)
            description = item.get('description', '')

            if not key:
                continue

            stored_value = encrypt_value(value) if is_encrypted and value else value

            existing = SystemConfig.query.filter_by(config_key=key).first()
            if existing:
                existing.config_value = stored_value
                existing.is_encrypted = is_encrypted
                if description:
                    existing.description = description
            else:
                db.session.add(SystemConfig(
                    config_key=key,
                    config_value=stored_value,
                    is_encrypted=is_encrypted,
                    description=description,
                ))

        db.session.commit()
        logger.info(f'系统配置恢复完成，共 {len(config_list)} 项')

    def _count_files(self, directory):
        """递归统计目录中的文件数"""
        count = 0
        for _, _, files in os.walk(directory):
            count += len(files)
        return count


def init_backup_service(app):
    """初始化备份服务和定时调度器"""
    global _backup_service, _scheduler

    _backup_service = BackupService(app)

    # 进程刚启动时不存在任何存活的后台备份线程，
    # 因此此刻仍是 pending/running 的记录一定是上次进程被杀掉时留下的孤儿记录。
    try:
        with app.app_context():
            _backup_service.recover_stale_backups()
    except Exception as e:
        logger.error(f'启动时回收僵尸备份记录失败: {e}', exc_info=True)

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger

        _scheduler = BackgroundScheduler(timezone='Asia/Shanghai')

        # 从配置中读取调度设置并注册任务
        _setup_schedule(app, _scheduler)

        _scheduler.start()
        logger.info('备份调度器已启动')

        import atexit
        atexit.register(lambda: _scheduler.shutdown(wait=False))

    except ImportError:
        logger.warning('APScheduler 未安装，定时备份功能不可用')
    except Exception as e:
        logger.error(f'备份调度器启动失败: {e}', exc_info=True)


def _setup_schedule(app, scheduler):
    """根据 SystemConfig 配置设置定时任务"""
    try:
        from apscheduler.triggers.cron import CronTrigger

        with app.app_context():
            from models import SystemConfig

            def _get_config(key, default=None):
                record = SystemConfig.query.filter_by(config_key=key).first()
                return record.config_value if record and record.config_value else default

            enabled = _get_config('backup_schedule_enabled', 'false') == 'true'
            if not enabled:
                logger.info('定时备份未启用')
                return

            frequency = _get_config('backup_schedule_frequency', 'daily')
            time_str = _get_config('backup_schedule_time', '03:00')

            hour, minute = 3, 0
            try:
                parts = time_str.split(':')
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0
            except (ValueError, IndexError):
                pass

            if frequency == 'daily':
                trigger = CronTrigger(hour=hour, minute=minute)
            elif frequency == 'weekly':
                trigger = CronTrigger(day_of_week='mon', hour=hour, minute=minute)
            elif frequency == 'monthly':
                trigger = CronTrigger(day=1, hour=hour, minute=minute)
            else:
                trigger = CronTrigger(hour=hour, minute=minute)

            # 移除已有任务并重新添加
            if scheduler.get_job('scheduled_backup'):
                scheduler.remove_job('scheduled_backup')

            scheduler.add_job(
                _backup_service.run_scheduled_backup,
                trigger=trigger,
                id='scheduled_backup',
                name='定时全量备份',
                replace_existing=True,
            )
            logger.info(f'定时备份已配置: {frequency} {time_str}')

    except Exception as e:
        logger.error(f'配置定时备份失败: {e}', exc_info=True)


def reschedule_backup():
    """更新定时备份调度（配置变更时调用）"""
    global _backup_service, _scheduler
    if not _scheduler or not _backup_service:
        return

    with _backup_service.app.app_context():
        _setup_schedule(_backup_service.app, _scheduler)


def get_backup_service():
    """获取备份服务单例"""
    return _backup_service
