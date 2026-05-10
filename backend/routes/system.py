import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, SystemConfig, AdminAuditLog, User
from utils.crypto_utils import encrypt_value, decrypt_value

logger = logging.getLogger(__name__)

system_bp = Blueprint('system', __name__)

# Config keys that should be encrypted at rest
ENCRYPTED_KEYS = {'ai_api_key'}

# Current application version
CURRENT_VERSION = '1.2.0'

# GitHub release check URL
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


def _write_audit_log(admin_id: int, action: str, target: str, detail: str = None):
    """Record an admin action in the audit log."""
    try:
        log_entry = AdminAuditLog(
            admin_id=admin_id,
            action=action,
            target=target,
            detail=detail,
            ip_address=request.remote_addr
        )
        db.session.add(log_entry)
    except Exception as e:
        logger.error(f'Failed to write audit log: {e}')


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

            # Write audit log
            is_sensitive = key in ENCRYPTED_KEYS
            detail = f'更新配置项: {key}'
            if is_sensitive and value:
                detail += ' (敏感信息已加密存储)'
            _write_audit_log(admin_id, 'update_config', key, detail)

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
        'update_info': None
    }

    try:
        import requests as req
        headers = {'Accept': 'application/vnd.github+json'}
        # Use a GitHub token if configured for higher rate limits
        import os
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
        logger.warning(f'Update check failed: {e}')
        result['check_error'] = str(e)

    return jsonify({'code': 200, 'data': result})


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


@system_bp.route('/system/audit-logs', methods=['GET'])
@jwt_required()
def get_audit_logs():
    """Get admin audit logs. Admin only. Supports ?page=1&per_page=20"""
    err = _admin_required()
    if err:
        return err

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)

    pagination = AdminAuditLog.query \
        .order_by(AdminAuditLog.created_at.desc()) \
        .paginate(page=page, per_page=per_page, error_out=False)

    logs = []
    for log_entry in pagination.items:
        admin = db.session.get(User, log_entry.admin_id)
        logs.append({
            'id': log_entry.id,
            'admin_name': admin.real_name if admin else '未知',
            'action': log_entry.action,
            'target': log_entry.target,
            'detail': log_entry.detail,
            'ip_address': log_entry.ip_address,
            'created_at': log_entry.created_at.isoformat() if log_entry.created_at else None
        })

    return jsonify({
        'code': 200,
        'data': {
            'logs': logs,
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        }
    })


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
