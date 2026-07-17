import logging
import os
import threading
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_cors import cross_origin
from config import CORS_ORIGINS
from models import db, SystemConfig, User, BackupRecord
from utils.crypto_utils import encrypt_value, decrypt_value

logger = logging.getLogger(__name__)

system_bp = Blueprint('system', __name__)

# 需要加密存储的配置键
ENCRYPTED_KEYS = {'ai_api_key', 'summary_ai_api_key'}


def _log_operation(user_id, username, action_type, action_description, target_type=None, target_id=None, target_name=None, event_id=None, event_name=None, detail=None):
    """记录操作日志"""
    try:
        from utils.operation_log import LogService
        LogService.log(
            user_id=user_id,
            username=username,
            action_type=action_type,
            action_description=action_description,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            event_id=event_id,
            event_name=event_name,
            detail=detail
        )
    except Exception as e:
        logger.warning(f'记录操作日志失败: {str(e)}')


def _get_version():
    """从 VERSION 文件读取应用版本号。"""
    version_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'VERSION')
    try:
        with open(version_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return '1.0.0'


CURRENT_VERSION = _get_version()

# GitHub 发布检查 URL
GITHUB_REPO = 'Ljinzhou/EasyInvoiceMgr'
GITHUB_API_RELEASES = f'https://api.github.com/repos/{GITHUB_REPO}/releases/latest'


def _is_admin() -> bool:
    """Check if the current JWT identity belongs to an admin user."""
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    return user is not None and user.user_type == 'admin'


def _admin_required():
    """Return 403 if the current user is not an admin, or 401 if not authenticated."""
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    if user is None:
        return jsonify({'code': 401, 'message': '用户不存在'}), 401
    if user.user_type != 'admin':
        return jsonify({'code': 403, 'message': '需要管理员权限'}), 403
    return None


def _get_config_value(config_key: str) -> str | None:
    """Read a config value from DB, decrypting if needed."""
    record = SystemConfig.query.filter_by(config_key=config_key).first()
    if not record or not record.config_value:
        return None
    if record.is_encrypted:
        try:
            return decrypt_value(record.config_value)
        except Exception:
            return None
    return record.config_value


def _set_config_value(config_key: str, value: str, description: str = None, admin_id: int = None):
    """Upsert a config value, encrypting if it's a sensitive key."""
    record = SystemConfig.query.filter_by(config_key=config_key).first()
    is_encrypted = config_key in ENCRYPTED_KEYS
    stored_value = encrypt_value(value) if is_encrypted else value

    if record:
        record.config_value = stored_value
        record.is_encrypted = is_encrypted
        if description:
            record.description = description
        if admin_id:
            record.updated_by = admin_id
    else:
        record = SystemConfig(
            config_key=config_key,
            config_value=stored_value,
            is_encrypted=is_encrypted,
            description=description or '',
            updated_by=admin_id
        )
        db.session.add(record)


def get_ai_model() -> str | None:
    """Get the configured AI model (DB first, env fallback). Call within app context."""
    # Prefer DB config
    model = _get_config_value('ai_model')
    if model:
        return model
    # Fallback to env
    import os
    return os.environ.get('GLM_MODEL', 'GLM-4V-Flash')


def get_ai_api_key() -> str | None:
    """Get the configured AI API key (DB first, env fallback). Call within app context."""
    key = _get_config_value('ai_api_key')
    if key:
        return key
    import os
    return os.environ.get('GLM_API_KEY')


def get_ai_api_url() -> str:
    """Get the configured AI API URL (DB first, env fallback)."""
    url = _get_config_value('ai_api_url')
    if url:
        return url
    import os
    return os.environ.get('GLM_API_URL', 'https://open.bigmodel.cn/api/paas/v4/chat/completions')


# ---------------------------------------------------------------------------
# Summary AI (DeepSeek) configuration helpers
# ---------------------------------------------------------------------------

def get_summary_ai_model() -> str:
    """Get the configured summary AI model. Default: deepseek-v4-pro."""
    model = _get_config_value('summary_ai_model')
    return model or 'deepseek-v4-pro'


def get_summary_ai_api_key() -> str | None:
    """Get the configured summary AI API key (DB only, encrypted storage)."""
    return _get_config_value('summary_ai_api_key')


def get_summary_ai_api_url() -> str:
    """Get the configured summary AI API URL. Default: DeepSeek endpoint."""
    url = _get_config_value('summary_ai_api_url')
    return url or 'https://api.deepseek.com/v1/chat/completions'


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@system_bp.route('/system/config', methods=['GET'])
@jwt_required()
def get_system_config():
    """Get all system config. Admin only. Sensitive values are masked."""
    err = _admin_required()
    if err:
        return err

    configs = SystemConfig.query.all()
    result = {}
    for c in configs:
        if c.config_key in ENCRYPTED_KEYS:
            # Mask sensitive values: show first 4 + last 4 chars
            try:
                plain = decrypt_value(c.config_value) if c.config_value else ''
                if len(plain) > 8:
                    masked = plain[:4] + '*' * (len(plain) - 8) + plain[-4:]
                elif plain:
                    masked = plain[:2] + '**'
                else:
                    masked = ''
            except Exception:
                masked = '***'
            result[c.config_key] = {
                'value': masked,
                'is_encrypted': True,
                'description': c.description or '',
                'updated_at': c.updated_at.isoformat() if c.updated_at else None,
                'has_value': bool(plain)
            }
        else:
            result[c.config_key] = {
                'value': c.config_value,
                'is_encrypted': False,
                'description': c.description or '',
                'updated_at': c.updated_at.isoformat() if c.updated_at else None,
                'has_value': bool(c.config_value)
            }

    # Also return current version info
    result['_version'] = {'value': CURRENT_VERSION}

    return jsonify({'code': 200, 'data': result})


@system_bp.route('/system/config', methods=['PUT'])
@jwt_required()
def update_system_config():
    """Update system config. Admin only. Body: {configs: {key: value, ...}}"""
    err = _admin_required()
    if err:
        return err

    data = request.get_json(silent=True)
    if not data or 'configs' not in data:
        return jsonify({'code': 400, 'message': '缺少configs字段'}), 400

    configs = data['configs']
    if not isinstance(configs, dict):
        return jsonify({'code': 400, 'message': 'configs必须是对象'}), 400

    allowed_keys = {'ai_model', 'ai_api_key', 'ai_api_url', 'summary_ai_model', 'summary_ai_api_key', 'summary_ai_api_url'}
    admin_id = get_jwt_identity()

    updated_keys = []
    try:
        for key, value in configs.items():
            if key not in allowed_keys:
                continue
            _set_config_value(key, str(value) if value else '', admin_id=admin_id)
            updated_keys.append(key)

        db.session.commit()
        logger.info(f'管理员 {admin_id} 更新了系统配置: {updated_keys}')

        admin_user = db.session.get(User, admin_id)
        _log_operation(
            user_id=int(admin_id),
            username=admin_user.username if admin_user else str(admin_id),
            action_type='update_config',
            action_description=f'更新系统配置：{", ".join(updated_keys) if updated_keys else "(无变更)"}',
            target_type='system_config',
            target_id=None,
            target_name=','.join(updated_keys),
            detail={
                'updated_keys': updated_keys,
                'count': len(updated_keys)
            }
        )

        return jsonify({
            'code': 200,
            'message': '配置保存成功',
            'data': {'updated_keys': updated_keys}
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f'保存系统配置失败: {e}', exc_info=True)
        return jsonify({'code': 500, 'message': f'保存失败: {str(e)}'}), 500


@system_bp.route('/system/check-update', methods=['GET'])
@jwt_required()
def check_update():
    """Check GitHub releases for a newer version."""
    err = _admin_required()
    if err:
        return err

    result = {
        'current_version': CURRENT_VERSION,
        'latest_version': CURRENT_VERSION,
        'has_update': False,
        'update_info': None,
        'update_commands': {
            'pull': 'git pull',
            'build': 'docker compose build',
            'restart': 'docker compose up -d',
            'full': 'git pull && docker compose build && docker compose up -d',
        },
        'manual_steps': {
            'title': '手动更新步骤',
            'description': '请在服务器上依次执行以下命令完成更新：',
            'steps': [
                {
                    'step': 1,
                    'title': '拉取最新代码',
                    'command': 'cd /path/to/EasyInvoiceMgr && git pull',
                    'description': '从GitHub拉取最新版本代码'
                },
                {
                    'step': 2,
                    'title': '备份数据库（推荐）',
                    'command': 'docker compose exec backend python -c "from utils.backup_service import get_backup_service; get_backup_service().run_backup()"',
                    'description': '在更新前备份数据库，以防万一'
                },
                {
                    'step': 3,
                    'title': '构建Docker镜像',
                    'command': 'docker compose build',
                    'description': '重新构建后端和前端Docker镜像'
                },
                {
                    'step': 4,
                    'title': '重启服务',
                    'command': 'docker compose up -d',
                    'description': '使用新镜像启动所有服务'
                },
                {
                    'step': 5,
                    'title': '检查服务状态',
                    'command': 'docker compose ps',
                    'description': '确认所有服务正常运行'
                },
                {
                    'step': 6,
                    'title': '清理旧镜像（可选）',
                    'command': 'docker image prune -f',
                    'description': '删除不再使用的Docker镜像以释放磁盘空间'
                },
            ],
            'one_liner': 'cd /path/to/EasyInvoiceMgr && git pull && docker compose build && docker compose up -d && docker image prune -f',
            'note': '更新期间系统将短暂不可用（约2-5分钟）。建议在低流量时段执行更新。如使用非Docker部署，请根据实际部署方式调整命令。'
        }
    }

    try:
        import requests as req
        headers = {'Accept': 'application/vnd.github+json'}
        gh_token = os.environ.get('GITHUB_TOKEN')
        if gh_token:
            headers['Authorization'] = f'Bearer {gh_token}'

        resp = req.get(GITHUB_API_RELEASES, headers=headers, timeout=10)
        if resp.status_code == 200:
            release = resp.json()
            latest_ver = release.get('tag_name', '').lstrip('v')
            if latest_ver:
                result['latest_version'] = latest_ver
                result['has_update'] = _compare_versions(latest_ver, CURRENT_VERSION) > 0
                if result['has_update']:
                    result['update_info'] = {
                        'version': latest_ver,
                        'release_name': release.get('name', ''),
                        'release_notes': release.get('body', ''),
                        'download_url': release.get('html_url', ''),
                        'published_at': release.get('published_at', '')
                    }
        elif resp.status_code == 404:
            result['check_error'] = '暂无发布版本'
        else:
            result['check_error'] = f'GitHub API 返回 {resp.status_code}'
    except Exception as e:
        logger.warning(f'更新检查失败: {e}')
        result['check_error'] = str(e)

    return jsonify({'code': 200, 'data': result})


@system_bp.route('/system/backup', methods=['POST'])
@jwt_required()
def manual_backup():
    """手动触发全量备份。仅管理员可用。"""
    err = _admin_required()
    if err:
        return err

    # 检查是否有正在运行的备份
    running = BackupRecord.query.filter(
        BackupRecord.status.in_(['pending', 'running']),
        BackupRecord.backup_type != 'restore'
    ).first()
    if running:
        return jsonify({'code': 409, 'message': '已有备份任务正在执行，请等待完成'}), 409

    from utils.backup_service import get_backup_service

    admin_id = get_jwt_identity()
    record = BackupRecord(
        backup_type='manual',
        backup_scope='full',
        status='pending',
        created_by=admin_id,
    )
    db.session.add(record)
    db.session.commit()

    service = get_backup_service()
    if not service:
        return jsonify({'code': 503, 'message': '备份服务未初始化', 'data': None}), 503

    thread = threading.Thread(target=service.run_backup, args=(record.id,), daemon=True)
    thread.start()

    backup_admin = db.session.get(User, admin_id)
    _log_operation(
        user_id=int(admin_id),
        username=backup_admin.username if backup_admin else str(admin_id),
        action_type='backup',
        action_description=f'触发手动备份（备份ID: {record.id}）',
        target_type='backup',
        target_id=record.id,
        target_name=f'backup-{record.id}',
        detail={
            'backup_id': record.id,
            'backup_type': 'manual',
            'backup_scope': 'full'
        }
    )

    return jsonify({
        'code': 200,
        'message': '备份任务已创建',
        'data': {'id': record.id, 'status': 'pending'}
    })


@system_bp.route('/system/backups', methods=['GET'])
@jwt_required()
def list_backups():
    """获取备份记录列表。仅管理员可用。"""
    err = _admin_required()
    if err:
        return err

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)

    query = BackupRecord.query.order_by(BackupRecord.created_at.desc())
    total = query.count()
    records = query.offset((page - 1) * per_page).limit(per_page).all()

    items = []
    for r in records:
        creator_name = None
        if r.created_by:
            creator = db.session.get(User, r.created_by)
            creator_name = creator.real_name if creator else None
        items.append({
            'id': r.id,
            'backup_type': r.backup_type,
            'backup_scope': r.backup_scope,
            'status': r.status,
            'progress': r.progress,
            'progress_message': r.progress_message,
            'file_size': r.file_size,
            'file_count': r.file_count,
            'error_message': r.error_message,
            'created_at': r.created_at.isoformat() if r.created_at else None,
            'completed_at': r.completed_at.isoformat() if r.completed_at else None,
            'created_by_name': creator_name,
        })

    return jsonify({
        'code': 200,
        'data': {
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
        }
    })


@system_bp.route('/system/backup/<int:backup_id>/download', methods=['GET'])
@jwt_required()
def download_backup(backup_id):
    """下载备份文件。仅管理员可用。"""
    err = _admin_required()
    if err:
        return err

    record = db.session.get(BackupRecord, backup_id)
    if not record:
        return jsonify({'code': 404, 'message': '备份记录不存在'}), 404

    if record.status != 'completed' or not record.file_path:
        return jsonify({'code': 400, 'message': '备份文件不可用'}), 400

    if not os.path.exists(record.file_path):
        return jsonify({'code': 404, 'message': '备份文件已被删除'}), 404

    return send_file(record.file_path, as_attachment=True)


@system_bp.route('/system/backup/<int:backup_id>', methods=['DELETE'])
@jwt_required()
def delete_backup(backup_id):
    """删除备份记录及文件。仅管理员可用。"""
    err = _admin_required()
    if err:
        return err

    record = db.session.get(BackupRecord, backup_id)
    if not record:
        return jsonify({'code': 404, 'message': '备份记录不存在'}), 404

    # 删除文件
    if record.file_path and os.path.exists(record.file_path):
        try:
            os.remove(record.file_path)
        except Exception as e:
            logger.warning(f'删除备份文件失败: {record.file_path}, error={str(e)}')

    backup_id_for_log = record.id
    backup_type_for_log = record.backup_type
    backup_scope_for_log = record.backup_scope

    db.session.delete(record)
    db.session.commit()

    del_admin_id = get_jwt_identity()
    del_admin = db.session.get(User, del_admin_id)
    _log_operation(
        user_id=int(del_admin_id),
        username=del_admin.username if del_admin else str(del_admin_id),
        action_type='delete_backup',
        action_description=f'删除备份记录（ID: {backup_id_for_log}）',
        target_type='backup',
        target_id=backup_id_for_log,
        target_name=f'backup-{backup_id_for_log}',
        detail={
            'backup_id': backup_id_for_log,
            'backup_type': backup_type_for_log,
            'backup_scope': backup_scope_for_log
        }
    )

    return jsonify({'code': 200, 'message': '备份已删除'})


@system_bp.route('/system/backup/restore/<int:backup_id>', methods=['POST'])
@jwt_required()
def restore_backup(backup_id):
    """从备份恢复数据。仅管理员可用，需确认。"""
    err = _admin_required()
    if err:
        return err

    data = request.get_json(silent=True)
    if not data or not data.get('confirm'):
        return jsonify({'code': 400, 'message': '请确认恢复操作（需传入 confirm: true）'}), 400

    record = db.session.get(BackupRecord, backup_id)
    if not record:
        return jsonify({'code': 404, 'message': '备份记录不存在'}), 404

    if record.status != 'completed' or not record.file_path:
        return jsonify({'code': 400, 'message': '该备份不可用于恢复'}), 400

    if not os.path.exists(record.file_path):
        return jsonify({'code': 404, 'message': '备份文件已被删除'}), 404

    # 检查是否有正在运行的任务
    running = BackupRecord.query.filter(
        BackupRecord.status.in_(['pending', 'running'])
    ).first()
    if running:
        return jsonify({'code': 409, 'message': '已有任务正在执行，请等待完成'}), 409

    from utils.backup_service import get_backup_service

    service = get_backup_service()
    thread = threading.Thread(target=service.restore_backup, args=(backup_id,), daemon=True)
    thread.start()

    admin_id = get_jwt_identity()
    logger.warning(f'管理员 {admin_id} 发起数据恢复: 备份id={backup_id}')

    restore_admin = db.session.get(User, admin_id)
    _log_operation(
        user_id=int(admin_id),
        username=restore_admin.username if restore_admin else str(admin_id),
        action_type='restore_backup',
        action_description=f'从备份恢复数据（备份ID: {backup_id}）',
        target_type='backup',
        target_id=backup_id,
        target_name=f'backup-{backup_id}',
        detail={
            'backup_id': backup_id,
            'restore_type': 'from_record'
        }
    )

    return jsonify({
        'code': 200,
        'message': '恢复任务已启动',
        'data': {'backup_id': backup_id}
    })


@system_bp.route('/system/backup/restore/upload', methods=['POST'])
@jwt_required()
def restore_upload_backup():
    """从本地上传的 .tar.gz 备份文件恢复数据。仅管理员可用，需确认。"""
    err = _admin_required()
    if err:
        return err

    # 检查是否有正在运行的任务
    running = BackupRecord.query.filter(
        BackupRecord.status.in_(['pending', 'running'])
    ).first()
    if running:
        return jsonify({'code': 409, 'message': '已有任务正在执行，请等待完成'}), 409

    # 验证文件上传
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请选择备份文件（.tar.gz）'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'code': 400, 'message': '未选择文件'}), 400

    if not file.filename.lower().endswith('.tar.gz'):
        return jsonify({'code': 400, 'message': '只支持 .tar.gz 格式的备份文件'}), 400

    # 确认参数
    data = request.form.get('confirm', 'false')
    if data != 'true':
        return jsonify({'code': 400, 'message': '请确认恢复操作（需传入 confirm: true）'}), 400

    from utils.backup_service import get_backup_service

    service = get_backup_service()
    if not service:
        return jsonify({'code': 503, 'message': '备份服务未初始化', 'data': None}), 503

    # 保存上传文件到 exports 目录
    import uuid
    safe_filename = f'upload_restore_{uuid.uuid4().hex[:8]}.tar.gz'
    upload_path = os.path.join(service.exports_dir, safe_filename)

    try:
        file.save(upload_path)
        file_size = os.path.getsize(upload_path)
    except Exception as e:
        logger.error(f'保存上传文件失败: {e}')
        return jsonify({'code': 500, 'message': '文件保存失败'}), 500

    # 创建恢复记录
    admin_id = get_jwt_identity()
    record = BackupRecord(
        backup_type='restore',
        backup_scope='full',
        status='pending',
        file_path=upload_path,
        file_size=file_size,
        file_count=1,
        created_by=admin_id,
    )
    db.session.add(record)
    db.session.commit()

    # 启动后台恢复
    thread = threading.Thread(target=service.restore_from_file, args=(record.id, upload_path), daemon=True)
    thread.start()

    logger.warning(f'管理员 {admin_id} 发起本地文件恢复: 文件名={file.filename}, 记录id={record.id}')

    return jsonify({
        'code': 200,
        'message': '恢复任务已启动',
        'data': {'id': record.id, 'filename': file.filename}
    })


@system_bp.route('/system/backup/config', methods=['GET'])
@jwt_required()
def get_backup_config():
    """获取定时备份配置。仅管理员可用。"""
    err = _admin_required()
    if err:
        return err

    def _get(key, default):
        record = SystemConfig.query.filter_by(config_key=key).first()
        return record.config_value if record and record.config_value else default

    return jsonify({
        'code': 200,
        'data': {
            'enabled': _get('backup_schedule_enabled', 'false') == 'true',
            'frequency': _get('backup_schedule_frequency', 'daily'),
            'time': _get('backup_schedule_time', '03:00'),
            'retention_count': int(_get('backup_retention_count', '10')),
        }
    })


@system_bp.route('/system/backup/config', methods=['PUT'])
@jwt_required()
def update_backup_config():
    """更新定时备份配置。仅管理员可用。"""
    err = _admin_required()
    if err:
        return err

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'code': 400, 'message': '请求数据为空'}), 400

    admin_id = get_jwt_identity()
    allowed = {
        'backup_schedule_enabled': str(data.get('enabled', False)).lower(),
        'backup_schedule_frequency': data.get('frequency', 'daily'),
        'backup_schedule_time': data.get('time', '03:00'),
        'backup_retention_count': str(data.get('retention_count', 10)),
    }

    # 校验
    if allowed['backup_schedule_frequency'] not in ('daily', 'weekly', 'monthly'):
        return jsonify({'code': 400, 'message': '频率必须为 daily/weekly/monthly'}), 400

    try:
        parts = allowed['backup_schedule_time'].split(':')
        h, m = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
    except (ValueError, IndexError):
        return jsonify({'code': 400, 'message': '时间格式无效，请使用 HH:MM'}), 400

    try:
        ret = int(allowed['backup_retention_count'])
        if ret < 1 or ret > 100:
            raise ValueError
    except ValueError:
        return jsonify({'code': 400, 'message': '保留数量必须为 1-100 的整数'}), 400

    for key, value in allowed.items():
        existing = SystemConfig.query.filter_by(config_key=key).first()
        if existing:
            existing.config_value = value
            existing.updated_by = admin_id
        else:
            db.session.add(SystemConfig(
                config_key=key,
                config_value=value,
                description='',
                updated_by=admin_id,
            ))

    db.session.commit()

    # 更新调度器
    try:
        from utils.backup_service import reschedule_backup
        reschedule_backup()
    except Exception as e:
        logger.warning(f'更新备份调度失败: {e}')

    return jsonify({'code': 200, 'message': '备份配置已保存'})


@system_bp.route('/system/test-model', methods=['POST'])
@jwt_required()
def test_model():
    """Test the configured AI model by sending a simple vision request."""
    err = _admin_required()
    if err:
        return err

    import time

    from utils.glm_vision_service import resolve_ai_api_key, resolve_ai_model, resolve_ai_api_url, REQUESTS_AVAILABLE
    if not REQUESTS_AVAILABLE:
        return jsonify({'code': 500, 'message': 'requests 库未安装'}), 500

    api_key = resolve_ai_api_key()
    if not api_key:
        return jsonify({'code': 400, 'message': '请先配置 API 密钥'}), 400

    model = resolve_ai_model()
    api_url = resolve_ai_api_url()

    try:
        import requests as req
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "这是一条测试消息，用于验证模型连通性。请简短回复'连接测试成功'。"
                        }
                    ]
                }
            ],
            "max_tokens": 32
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        start = time.time()
        resp = req.post(api_url, headers=headers, json=payload, timeout=15)
        elapsed_ms = int((time.time() - start) * 1000)

        if resp.status_code == 200:
            body = resp.json()
            if 'choices' in body and len(body['choices']) > 0:
                reply = body['choices'][0].get('message', {}).get('content', '')
                tm_admin_id = get_jwt_identity()
                tm_admin = db.session.get(User, tm_admin_id)
                _log_operation(
                    user_id=int(tm_admin_id),
                    username=tm_admin.username if tm_admin else str(tm_admin_id),
                    action_type='test_model',
                    action_description=f'测试视觉模型「{model}」成功（{elapsed_ms}ms）',
                    target_type='ai_model',
                    target_id=None,
                    target_name=model,
                    detail={
                        'model': model,
                        'latency_ms': elapsed_ms,
                        'success': True
                    }
                )
                return jsonify({
                    'code': 200,
                    'message': '模型连接测试成功',
                    'data': {
                        'model': model,
                        'latency_ms': elapsed_ms,
                        'reply': reply[:200]
                    }
                })
            else:
                tm_admin_id = get_jwt_identity()
                tm_admin = db.session.get(User, tm_admin_id)
                _log_operation(
                    user_id=int(tm_admin_id),
                    username=tm_admin.username if tm_admin else str(tm_admin_id),
                    action_type='test_model',
                    action_description=f'测试视觉模型「{model}」失败：返回数据异常',
                    target_type='ai_model',
                    target_id=None,
                    target_name=model,
                    detail={
                        'model': model,
                        'latency_ms': elapsed_ms,
                        'success': False,
                        'error': 'no_valid_response'
                    }
                )
                return jsonify({
                    'code': 500,
                    'message': '模型返回数据异常：无有效响应',
                    'data': {'model': model, 'latency_ms': elapsed_ms}
                }), 500
        else:
            error_detail = resp.text[:300]
            logger.error(f'Model test failed: HTTP {resp.status_code}: {error_detail}')
            tm_admin_id = get_jwt_identity()
            tm_admin = db.session.get(User, tm_admin_id)
            _log_operation(
                user_id=int(tm_admin_id),
                username=tm_admin.username if tm_admin else str(tm_admin_id),
                action_type='test_model',
                action_description=f'测试视觉模型「{model}」失败：HTTP {resp.status_code}',
                target_type='ai_model',
                target_id=None,
                target_name=model,
                detail={
                    'model': model,
                    'latency_ms': elapsed_ms,
                    'success': False,
                    'http_status': resp.status_code
                }
            )
            return jsonify({
                'code': 500,
                'message': f'模型请求失败 (HTTP {resp.status_code})',
                'data': {'model': model, 'latency_ms': elapsed_ms, 'error': error_detail}
            }), 500

    except req.exceptions.Timeout:
        return jsonify({'code': 500, 'message': '测试超时，请检查网络和 API 地址'}), 500
    except Exception as e:
        logger.error(f'Model test error: {e}', exc_info=True)
        return jsonify({'code': 500, 'message': f'测试失败: {str(e)}'}), 500


@system_bp.route('/system/test-summary-model', methods=['POST'])
@jwt_required()
def test_summary_model():
    """Test the configured summary AI model (DeepSeek chat)."""
    err = _admin_required()
    if err:
        return err

    import time

    from utils.glm_vision_service import REQUESTS_AVAILABLE
    if not REQUESTS_AVAILABLE:
        return jsonify({'code': 500, 'message': 'requests 库未安装'}), 500

    api_key = get_summary_ai_api_key()
    if not api_key:
        return jsonify({'code': 400, 'message': '请先配置 AI 总结 API 密钥'}), 400

    model = get_summary_ai_model()
    api_url = get_summary_ai_api_url()

    try:
        import requests as req
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": "这是一条测试消息，用于验证 AI 总结模型连通性。请简短回复'连接测试成功'。"
                }
            ],
            "max_tokens": 32
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        start = time.time()
        resp = req.post(api_url, headers=headers, json=payload, timeout=15)
        elapsed_ms = int((time.time() - start) * 1000)

        if resp.status_code == 200:
            body = resp.json()
            if 'choices' in body and len(body['choices']) > 0:
                reply = body['choices'][0].get('message', {}).get('content', '')
                tsm_admin_id = get_jwt_identity()
                tsm_admin = db.session.get(User, tsm_admin_id)
                _log_operation(
                    user_id=int(tsm_admin_id),
                    username=tsm_admin.username if tsm_admin else str(tsm_admin_id),
                    action_type='test_model',
                    action_description=f'测试总结模型「{model}」成功（{elapsed_ms}ms）',
                    target_type='ai_model',
                    target_id=None,
                    target_name=model,
                    detail={
                        'model': model,
                        'latency_ms': elapsed_ms,
                        'success': True,
                        'model_type': 'summary'
                    }
                )
                return jsonify({
                    'code': 200,
                    'message': 'AI 总结模型连接测试成功',
                    'data': {
                        'model': model,
                        'latency_ms': elapsed_ms,
                        'reply': reply[:200]
                    }
                })
            else:
                tsm_admin_id = get_jwt_identity()
                tsm_admin = db.session.get(User, tsm_admin_id)
                _log_operation(
                    user_id=int(tsm_admin_id),
                    username=tsm_admin.username if tsm_admin else str(tsm_admin_id),
                    action_type='test_model',
                    action_description=f'测试总结模型「{model}」失败：返回数据异常',
                    target_type='ai_model',
                    target_id=None,
                    target_name=model,
                    detail={
                        'model': model,
                        'latency_ms': elapsed_ms,
                        'success': False,
                        'error': 'no_valid_response',
                        'model_type': 'summary'
                    }
                )
                return jsonify({
                    'code': 500,
                    'message': '模型返回数据异常：无有效响应',
                    'data': {'model': model, 'latency_ms': elapsed_ms}
                }), 500
        else:
            error_detail = resp.text[:300]
            logger.error(f'Summary model test failed: HTTP {resp.status_code}: {error_detail}')
            tsm_admin_id = get_jwt_identity()
            tsm_admin = db.session.get(User, tsm_admin_id)
            _log_operation(
                user_id=int(tsm_admin_id),
                username=tsm_admin.username if tsm_admin else str(tsm_admin_id),
                action_type='test_model',
                action_description=f'测试总结模型「{model}」失败：HTTP {resp.status_code}',
                target_type='ai_model',
                target_id=None,
                target_name=model,
                detail={
                    'model': model,
                    'latency_ms': elapsed_ms,
                    'success': False,
                    'http_status': resp.status_code,
                    'model_type': 'summary'
                }
            )
            return jsonify({
                'code': 500,
                'message': f'模型请求失败 (HTTP {resp.status_code})',
                'data': {'model': model, 'latency_ms': elapsed_ms, 'error': error_detail}
            }), 500

    except req.exceptions.Timeout:
        return jsonify({'code': 500, 'message': '测试超时，请检查网络和 API 地址'}), 500
    except Exception as e:
        logger.error(f'Summary model test error: {e}', exc_info=True)
        return jsonify({'code': 500, 'message': f'测试失败: {str(e)}'}), 500


@system_bp.route('/system/ai-summary', methods=['POST', 'OPTIONS'])
@cross_origin(origins=CORS_ORIGINS, supports_credentials=True)
@jwt_required(optional=True)
def ai_summary():
    """生成 AI 财务总结。总结范围：全部项目汇总，或指定项目。"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    err = _admin_required()
    if err:
        return err

    import time
    from models import Event, PurchaseRecord, Invoice, User
    from sqlalchemy import func

    from utils.glm_vision_service import REQUESTS_AVAILABLE
    if not REQUESTS_AVAILABLE:
        return jsonify({'code': 500, 'message': 'requests 库未安装'}), 500

    api_key = get_summary_ai_api_key()
    if not api_key:
        return jsonify({'code': 400, 'message': '请先在系统设置中配置 AI 总结 API 密钥'}), 400

    model = get_summary_ai_model()
    api_url = get_summary_ai_api_url()

    # 确定总结范围
    data = request.get_json(silent=True) or {}
    event_id = data.get('event_id')

    if event_id:
        event = Event.query.filter_by(event_id=event_id, is_deleted=False).first()
        if not event:
            return jsonify({'code': 404, 'message': '项目不存在'}), 404
        events = [event]
    else:
        events = Event.query.filter_by(is_deleted=False).all()

    if not events:
        return jsonify({'code': 400, 'message': '暂无项目数据可供总结'}), 400

    # 汇总数据
    event_ids = [e.event_id for e in events]

    total_budget = sum(float(e.total_budget or 0) for e in events)

    # spent_amount 不是 Event 模型列，需要从 purchase + invoice 计算
    purchase_spent = db.session.query(func.sum(PurchaseRecord.amount)).filter(
        PurchaseRecord.event_id.in_(event_ids), PurchaseRecord.is_deleted == False
    ).scalar() or 0
    invoice_table_spent = db.session.query(func.sum(Invoice.total_amount)).filter(
        Invoice.event_id.in_(event_ids), Invoice.is_deleted == False
    ).scalar() or 0
    total_spent = float(purchase_spent) + float(invoice_table_spent)

    total_remaining = max(0, total_budget - total_spent)
    usage_rate = (total_spent / total_budget * 100) if total_budget > 0 else 0

    total_invoice_amount = sum(float(e.invoice_total_amount or 0) for e in events)
    total_reimbursed = sum(float(e.reimbursed_amount or 0) for e in events)
    pending_reimburse = max(0, total_invoice_amount - total_reimbursed)

    total_records = int(db.session.query(func.count(PurchaseRecord.record_id))
        .filter(PurchaseRecord.event_id.in_(event_ids), PurchaseRecord.is_deleted == False).scalar() or 0)
    total_invoice_count = int(db.session.query(func.count(Invoice.invoice_id))
        .filter(Invoice.event_id.in_(event_ids), Invoice.is_deleted == False).scalar() or 0)

    # 用户消费排名（Top 10）
    pr_sq = db.session.query(
        PurchaseRecord.uploader_id,
        func.sum(PurchaseRecord.amount).label('total'),
        func.count(PurchaseRecord.record_id).label('cnt')
    ).filter(
        PurchaseRecord.event_id.in_(event_ids),
        PurchaseRecord.is_deleted == False
    ).group_by(PurchaseRecord.uploader_id).subquery()

    rankings = db.session.query(
        User.real_name, pr_sq.c.total, pr_sq.c.cnt
    ).join(pr_sq, User.user_id == pr_sq.c.uploader_id
    ).order_by(pr_sq.c.total.desc()).limit(10).all()

    # 构建 AI 提示词
    scope_text = f'项目「{events[0].event_name}」' if event_id and len(events) == 1 else f'全部 {len(events)} 个项目'

    parts = [
        f'你是一个专业的财务分析助手。请根据以下财务数据生成一段简洁的中文总结报告（150-300字），重点突出关键数据和需要注意的问题。',
        '',
        f'## 总结范围：{scope_text}',
        '',
        '## 总体概况',
        f'- 项目数：{len(events)} 个',
        f'- 总记录数：{total_records} 条（购买）+ {total_invoice_count} 条（发票）',
        f'- 总预算：¥{total_budget:,.2f}',
        f'- 已支出：¥{total_spent:,.2f}（预算使用率 {usage_rate:.1f}%）',
        f'- 剩余预算：¥{total_remaining:,.2f}',
        f'- 发票总额：¥{total_invoice_amount:,.2f}',
        f'- 已报销：¥{total_reimbursed:,.2f}（待报销 ¥{pending_reimburse:,.2f}）',
        '',
    ]

    if len(events) <= 10:
        # 预计算每个项目的支出金额
        ev_spent_map = {}
        if events:
            pr_rows = db.session.query(
                PurchaseRecord.event_id,
                func.sum(PurchaseRecord.amount).label('total')
            ).filter(
                PurchaseRecord.event_id.in_(event_ids),
                PurchaseRecord.is_deleted == False
            ).group_by(PurchaseRecord.event_id).all()
            inv_rows = db.session.query(
                Invoice.event_id,
                func.sum(Invoice.total_amount).label('total')
            ).filter(
                Invoice.event_id.in_(event_ids),
                Invoice.is_deleted == False
            ).group_by(Invoice.event_id).all()
            for eid, total in pr_rows:
                ev_spent_map[eid] = ev_spent_map.get(eid, 0) + float(total or 0)
            for eid, total in inv_rows:
                ev_spent_map[eid] = ev_spent_map.get(eid, 0) + float(total or 0)

        parts.append('## 各项目明细')
        for e in events:
            ev_spent = ev_spent_map.get(e.event_id, 0)
            ev_budget = float(e.total_budget or 0)
            ev_usage = (ev_spent / ev_budget * 100) if ev_budget > 0 else 0
            parts.append(
                f'- {e.event_name}（{e.status}）：预算 ¥{ev_budget:,.2f}，已用 ¥{ev_spent:,.2f}'
                f'（{ev_usage:.1f}%），发票 {e.invoice_count or 0} 张，记录 {e.purchase_record_count or 0} 条'
            )

    if rankings:
        parts.append('')
        parts.append('## 用户消费排名（Top 10）')
        for i, (name, total, cnt) in enumerate(rankings):
            parts.append(f'{i+1}. {name}：¥{float(total):,.2f}（{cnt} 条记录）')

    parts.append('')
    parts.append('请生成总结报告。要求：1) 先一句话概述整体情况；2) 指出预算使用率最高/最低的项目；3) 如有预算超支风险请特别提醒；4) 指出消费最高的用户；5) 待报销金额较大时提醒。')

    prompt_text = '\n'.join(parts)

    try:
        import requests as req
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt_text}],
            "max_tokens": 800,
            "temperature": 0.3,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        start = time.time()
        resp = req.post(api_url, headers=headers, json=payload, timeout=30)
        elapsed_ms = int((time.time() - start) * 1000)

        if resp.status_code == 200:
            body = resp.json()
            if 'choices' in body and len(body['choices']) > 0:
                reply = body['choices'][0].get('message', {}).get('content', '')
                ai_admin_id = get_jwt_identity()
                ai_admin = db.session.get(User, ai_admin_id)
                _log_operation(
                    user_id=int(ai_admin_id),
                    username=ai_admin.username if ai_admin else str(ai_admin_id),
                    action_type='ai_summary',
                    action_description=f'生成AI财务总结（{scope_text}，模型: {model}，耗时 {elapsed_ms}ms）',
                    target_type='ai_summary',
                    target_id=event_id,
                    target_name=scope_text,
                    event_id=event_id if event_id else None,
                    event_name=events[0].event_name if events and event_id else None,
                    detail={
                        'scope': scope_text,
                        'event_id': event_id,
                        'event_count': len(events),
                        'model': model,
                        'latency_ms': elapsed_ms,
                        'success': True
                    }
                )
                return jsonify({
                    'code': 200,
                    'message': 'AI 总结生成成功',
                    'data': {
                        'summary': reply,
                        'model': model,
                        'latency_ms': elapsed_ms,
                        'scope': scope_text,
                    }
                })
            else:
                ai_admin_id = get_jwt_identity()
                ai_admin = db.session.get(User, ai_admin_id)
                _log_operation(
                    user_id=int(ai_admin_id),
                    username=ai_admin.username if ai_admin else str(ai_admin_id),
                    action_type='ai_summary',
                    action_description=f'生成AI财务总结失败：返回数据异常（{scope_text}）',
                    target_type='ai_summary',
                    target_id=event_id,
                    target_name=scope_text,
                    event_id=event_id if event_id else None,
                    event_name=events[0].event_name if events and event_id else None,
                    detail={
                        'scope': scope_text,
                        'event_id': event_id,
                        'model': model,
                        'success': False,
                        'error': 'no_valid_response'
                    }
                )
                return jsonify({'code': 500, 'message': '模型返回数据异常：无有效响应'}), 500
        else:
            error_detail = resp.text[:300] if resp.text else '无详细信息'
            logger.error(f'AI summary API error: HTTP {resp.status_code} - {error_detail}')
            ai_admin_id = get_jwt_identity()
            ai_admin = db.session.get(User, ai_admin_id)
            _log_operation(
                user_id=int(ai_admin_id),
                username=ai_admin.username if ai_admin else str(ai_admin_id),
                action_type='ai_summary',
                action_description=f'生成AI财务总结失败：HTTP {resp.status_code}（{scope_text}）',
                target_type='ai_summary',
                target_id=event_id,
                target_name=scope_text,
                event_id=event_id if event_id else None,
                event_name=events[0].event_name if events and event_id else None,
                detail={
                    'scope': scope_text,
                    'event_id': event_id,
                    'model': model,
                    'success': False,
                    'http_status': resp.status_code
                }
            )
            return jsonify({
                'code': 500,
                'message': f'AI 总结请求失败 (HTTP {resp.status_code})',
                'data': {'error': error_detail}
            }), 500

    except req.exceptions.Timeout:
        return jsonify({'code': 500, 'message': 'AI 总结超时，请稍后重试'}), 500
    except Exception as e:
        logger.error(f'AI summary error: {e}', exc_info=True)
        return jsonify({'code': 500, 'message': f'AI 总结失败: {str(e)}'}), 500


def _compare_versions(a: str, b: str) -> int:
    """Compare two semver strings. Returns positive if a > b, 0 if equal, negative if a < b."""
    try:
        parts_a = [int(x) for x in a.split('.')]
        parts_b = [int(x) for x in b.split('.')]
        # Pad with zeros
        while len(parts_a) < 3:
            parts_a.append(0)
        while len(parts_b) < 3:
            parts_b.append(0)
        for x, y in zip(parts_a, parts_b):
            if x != y:
                return x - y
        return 0
    except Exception:
        return -1


# ---------------------------------------------------------------------------
