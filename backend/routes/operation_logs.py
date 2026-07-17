from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import User
from utils.operation_log import LogService
import logging

logger = logging.getLogger(__name__)
operation_logs_bp = Blueprint('operation_logs', __name__)


def admin_required(f):
    """装饰器：仅允许管理员访问"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or user.user_type != 'admin':
            return jsonify({'code': 403, 'message': '需要管理员权限', 'data': None}), 403
        return f(*args, **kwargs)
    return decorated_function


@operation_logs_bp.route('', methods=['GET'])
@jwt_required()
@admin_required
def get_logs():
    """获取操作日志列表（仅管理员）"""
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 50, type=int)
        user_id = request.args.get('user_id', type=int)
        action_type = request.args.get('action_type')
        target_type = request.args.get('target_type')
        event_id = request.args.get('event_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        result = LogService.get_logs(
            page=page,
            page_size=page_size,
            user_id=user_id,
            action_type=action_type,
            target_type=target_type,
            event_id=event_id,
            start_date=start_date,
            end_date=end_date
        )

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': result
        }), 200

    except Exception as e:
        logger.error(f'获取操作日志异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


@operation_logs_bp.route('/action-types', methods=['GET'])
@jwt_required()
@admin_required
def get_action_types():
    """获取所有操作类型"""
    try:
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': LogService.get_action_types()
        }), 200
    except Exception as e:
        logger.error(f'获取操作类型异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


@operation_logs_bp.route('/<int:log_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_log(log_id):
    """删除单条日志"""
    try:
        success = LogService.delete_log(log_id)
        if success:
            return jsonify({'code': 200, 'message': '日志已删除', 'data': None}), 200
        return jsonify({'code': 404, 'message': '日志不存在', 'data': None}), 404
    except Exception as e:
        logger.error(f'删除日志异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


@operation_logs_bp.route('', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_logs():
    """批量删除日志"""
    try:
        data = request.get_json()
        log_ids = data.get('log_ids', [])
        if not log_ids:
            return jsonify({'code': 400, 'message': '请提供要删除的日志ID', 'data': None}), 400

        count = LogService.delete_logs(log_ids)
        return jsonify({
            'code': 200,
            'message': f'已删除 {count} 条日志',
            'data': {'deleted': count}
        }), 200

    except Exception as e:
        logger.error(f'批量删除日志异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500
