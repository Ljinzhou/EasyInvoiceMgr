import logging
import os
import threading
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, SystemConfig, User, BackupRecord
from utils.crypto_utils import encrypt_value, decrypt_value

logger = logging.getLogger(__name__)

system_bp = Blueprint('system', __name__)

# 需要加密存储的配置键
ENCRYPTED_KEYS = {'ai_api_key'}


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

    allowed_keys = {'ai_model', 'ai_api_key', 'ai_api_url'}
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
                    result['update_commands']['full_with_prune'] = (
                        'git pull && docker compose build --no-cache && '
                        'docker compose up -d && docker image prune -f'
                    )
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

    db.session.delete(record)
    db.session.commit()

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

    return jsonify({
        'code': 200,
        'message': '恢复任务已启动',
        'data': {'backup_id': backup_id}
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
                return jsonify({
                    'code': 500,
                    'message': '模型返回数据异常：无有效响应',
                    'data': {'model': model, 'latency_ms': elapsed_ms}
                }), 500
        else:
            error_detail = resp.text[:300]
            logger.error(f'Model test failed: HTTP {resp.status_code}: {error_detail}')
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
# One-click Update
# ---------------------------------------------------------------------------

import json as _json
import subprocess as _subprocess

_UPDATE_SCRIPT = 'update.sh'


@system_bp.route('/system/update', methods=['POST'])
@jwt_required()
def trigger_update():
    """Trigger one-click system update. Admin only. Runs update.sh as a detached background process."""
    err = _admin_required()
    if err:
        return err

    # Check if update is already running
    status_path = _update_status_path()
    lock_path = _update_lock_path()
    update_alive = False
    if os.path.exists(status_path):
        try:
            with open(status_path, 'r', encoding='utf-8') as f:
                st = _json.load(f)
            if st.get('status') == 'running':
                # Verify the update process is actually still alive via lock file
                if os.path.exists(lock_path):
                    try:
                        with open(lock_path, 'r') as lf:
                            pid = int(lf.read().strip())
                        os.kill(pid, 0)  # Check if process exists
                        update_alive = True
                    except (ValueError, OSError, ProcessLookupError):
                        logger.warning('更新锁文件存在但进程已不存在，清除残留状态')
                        os.remove(lock_path)
                if update_alive:
                    return jsonify({
                        'code': 409,
                        'message': '系统更新正在进行中，请勿重复操作',
                        'data': st
                    }), 409
                # Stale running status - clean it up
                logger.warning('检测到残留的更新状态文件，已清除')
                try:
                    os.remove(status_path)
                except OSError:
                    pass
            else:
                # Previous update finished or was interrupted — clean up stale status
                logger.info(f'清除旧的更新状态文件 (status={st.get("status")})')
                try:
                    os.remove(status_path)
                except OSError:
                    pass
                if os.path.exists(lock_path):
                    try:
                        os.remove(lock_path)
                    except OSError:
                        pass
        except Exception:
            pass

    project_dir = os.environ.get('HOST_PROJECT_DIR', '')
    script_path = os.path.join(project_dir, _UPDATE_SCRIPT) if project_dir else ''

    if not script_path or not os.path.exists(script_path):
        logger.error(f'Update script not found: {script_path}')
        return jsonify({
            'code': 503,
            'message': '更新脚本未找到，请检查 HOST_PROJECT_DIR 配置。'
            '更新功能需要将项目目录挂载到容器内相同路径，并挂载 Docker socket。'
        }), 503

    if not os.access(script_path, os.X_OK):
        try:
            os.chmod(script_path, 0o755)
        except Exception:
            pass

    try:
        proc = _subprocess.Popen(
            ['bash', script_path, '--force'],
            cwd=project_dir,
            stdout=_subprocess.DEVNULL,
            stderr=_subprocess.DEVNULL,
            stdin=_subprocess.DEVNULL,
            start_new_session=True,
        )
        logger.info(f'管理员 {get_jwt_identity()} 触发了系统更新, PID={proc.pid}')
    except Exception as e:
        logger.error(f'启动更新脚本失败: {e}', exc_info=True)
        return jsonify({'code': 500, 'message': f'启动更新失败: {str(e)}'}), 500

    return jsonify({
        'code': 200,
        'message': '系统更新已启动。服务将在更新完成后自动重启，期间系统将短暂不可用。',
        'data': {'status': 'running', 'message': '更新已启动'}
    })


@system_bp.route('/system/update/status', methods=['GET'])
@jwt_required()
def update_status():
    """Get current update progress. Reads from update_status.json on the host project directory."""
    err = _admin_required()
    if err:
        return err

    status_path = _update_status_path()
    if not os.path.exists(status_path):
        return jsonify({
            'code': 200,
            'data': {'status': 'idle', 'message': '没有正在进行的更新'}
        })

    try:
        with open(status_path, 'r', encoding='utf-8') as f:
            st = _json.load(f)
        return jsonify({'code': 200, 'data': st})
    except Exception as e:
        return jsonify({
            'code': 200,
            'data': {'status': 'idle', 'message': f'读取状态失败: {str(e)}'}
        })


def _update_status_path():
    """Return the path to update_status.json on the host project directory."""
    project_dir = os.environ.get('HOST_PROJECT_DIR', '')
    if project_dir:
        return os.path.join(project_dir, 'update_status.json')
    return '/tmp/update_status.json'


def _update_lock_path():
    """Return the path to .update.lock on the host project directory."""
    project_dir = os.environ.get('HOST_PROJECT_DIR', '')
    if project_dir:
        return os.path.join(project_dir, '.update.lock')
    return '/tmp/.update.lock'
