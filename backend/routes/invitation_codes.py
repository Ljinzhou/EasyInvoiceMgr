from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, InvitationCode, User
from datetime import datetime, timedelta
import logging
import secrets
import string

logger = logging.getLogger(__name__)
invitation_codes_bp = Blueprint('invitation_codes', __name__)

def generate_invitation_code(target_user_type: str) -> str:
    prefix = {
        'teacher': 'TCH',
        'student_admin': 'ADM',
        'student': 'STU'
    }.get(target_user_type, 'USR')
    
    random_part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16))
    timestamp = datetime.now().strftime('%Y%m%d%H%M')
    
    return f'{prefix}-{timestamp}-{random_part}'

@invitation_codes_bp.route('/invitation-codes', methods=['GET'])
@jwt_required()
def get_invitation_codes():
    logger.info('=== 获取邀请码列表 ===')
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or user.user_type not in ['admin', 'teacher']:
            return jsonify({'code': 403, 'message': '权限不足', 'data': None}), 403
        
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        
        query = InvitationCode.query
        
        if user.user_type == 'teacher':
            query = query.filter_by(created_by=current_user_id)
        
        codes = query.order_by(InvitationCode.created_at.desc()).paginate(
            page=page,
            per_page=page_size,
            error_out=False
        )
        
        code_list = []
        for code in codes.items:
            is_expired = code.expires_at < datetime.utcnow() if code.expires_at else False
            is_used_out = (code.max_uses > 0 and code.used_count >= code.max_uses) if code.max_uses > 0 else False
            
            code_list.append({
                'id': code.id,
                'code': code.code,
                'target_user_type': code.target_user_type,
                'target_user_type_text': {
                    'admin': '管理员',
                    'teacher': '老师',
                    'student_admin': '学生管理员',
                    'student': '学生'
                }.get(code.target_user_type, code.target_user_type),
                'expires_at': code.expires_at.isoformat() if code.expires_at else None,
                'max_uses': code.max_uses,
                'used_count': code.used_count,
                'created_by': code.created_by,
                'creator_name': code.creator.real_name if code.creator else None,
                'is_active': code.is_active and not is_expired and not is_used_out,
                'status': 'expired' if is_expired else ('used_out' if is_used_out else ('active' if code.is_active else 'disabled')),
                'created_at': code.created_at.isoformat() if code.created_at else None
            })
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'data': code_list,
                'total': codes.total,
                'page': page,
                'page_size': page_size,
                'total_pages': codes.pages
            }
        }), 200
        
    except Exception as e:
        logger.error(f'获取邀请码列表异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@invitation_codes_bp.route('/invitation-codes', methods=['POST'])
@jwt_required()
def create_invitation_code():
    logger.info('=== 创建邀请码 ===')
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or user.user_type not in ['admin', 'teacher']:
            return jsonify({'code': 403, 'message': '权限不足，只有管理员和老师可以生成邀请码', 'data': None}), 403
        
        data = request.get_json()
        
        target_user_type = data.get('target_user_type', 'student')
        valid_types = ['admin', 'teacher', 'student_admin', 'student']
        if target_user_type not in valid_types:
            return jsonify({'code': 400, 'message': f'无效的用户类型，可选值: {valid_types}', 'data': None}), 400
        
        expires_days = data.get('expires_days', 30)
        try:
            expires_days = int(expires_days)
            if expires_days < 1 or expires_days > 365:
                return jsonify({'code': 400, 'message': '有效期必须在1-365天之间', 'data': None}), 400
        except (ValueError, TypeError):
            return jsonify({'code': 400, 'message': '有效期必须是数字', 'data': None}), 400
        
        quantity = data.get('quantity', 1)
        try:
            quantity = int(quantity)
            if quantity < 1 or quantity > 20:
                return jsonify({'code': 400, 'message': '生成数量必须在1-20之间', 'data': None}), 400
        except (ValueError, TypeError):
            return jsonify({'code': 400, 'message': '数量必须是数字', 'data': None}), 400
        
        created_codes = []
        expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        for _ in range(quantity):
            code_str = generate_invitation_code(target_user_type)
            
            invitation_code = InvitationCode(
                code=code_str,
                target_user_type=target_user_type,
                expires_at=expires_at,
                max_uses=data.get('max_uses', -1),
                created_by=current_user_id,
                is_active=True
            )
            
            db.session.add(invitation_code)
            created_codes.append({
                'code': code_str,
                'target_user_type': target_user_type,
                'expires_at': expires_at.isoformat()
            })
        
        db.session.commit()
        
        logger.info(f'成功创建 {quantity} 个邀请码')
        
        return jsonify({
            'code': 200,
            'message': f'成功生成 {quantity} 个邀请码',
            'data': {
                'codes': created_codes,
                'count': len(created_codes)
            }
        }), 200
        
    except Exception as e:
        logger.error(f'创建邀请码异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@invitation_codes_bp.route('/invitation-codes/verify', methods=['POST'])
def verify_invitation_code():
    logger.info('=== 验证邀请码 ===')
    try:
        data = request.get_json()
        code = data.get('code', '').strip()
        
        if not code:
            return jsonify({'code': 400, 'message': '请输入邀请码', 'data': None}), 400
        
        invitation_code = InvitationCode.query.filter_by(code=code).first()
        
        if not invitation_code:
            return jsonify({
                'code': 404,
                'message': '邀请码不存在',
                'data': {'valid': False}
            }), 200
        
        if not invitation_code.is_active:
            return jsonify({
                'code': 200,
                'message': '该邀请码已被禁用',
                'data': {'valid': False, 'reason': 'disabled'}
            }), 200
        
        if invitation_code.expires_at < datetime.utcnow():
            return jsonify({
                'code': 200,
                'message': '该邀请码已过期',
                'data': {'valid': False, 'reason': 'expired'}
            }), 200
        
        if invitation_code.max_uses > 0 and invitation_code.used_count >= invitation_code.max_uses:
            return jsonify({
                'code': 200,
                'message': '该邀请码使用次数已达上限',
                'data': {'valid': False, 'reason': 'used_out'}
            }), 200
        
        return jsonify({
            'code': 200,
            'message': '邀请码有效',
            'data': {
                'valid': True,
                'target_user_type': invitation_code.target_user_type
            }
        }), 200
        
    except Exception as e:
        logger.error(f'验证邀请码异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@invitation_codes_bp.route('/invitation-codes/<int:code_id>/toggle', methods=['POST'])
@jwt_required()
def toggle_invitation_code(code_id):
    logger.info(f'=== 切换邀请码状态: {code_id} ===')
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or user.user_type not in ['admin', 'teacher']:
            return jsonify({'code': 403, 'message': '权限不足', 'data': None}), 403
        
        code = InvitationCode.query.get(code_id)
        if not code:
            return jsonify({'code': 404, 'message': '邀请码不存在', 'data': None}), 404
        
        if user.user_type == 'teacher' and code.created_by != current_user_id:
            return jsonify({'code': 403, 'message': '只能操作自己创建的邀请码', 'data': None}), 403
        
        code.is_active = not code.is_active
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': f'邀请码已{"启用" if code.is_active else "禁用"}',
            'data': {'is_active': code.is_active}
        }), 200
        
    except Exception as e:
        logger.error(f'切换邀请码状态异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@invitation_codes_bp.route('/invitation-codes/<int:code_id>', methods=['DELETE'])
@jwt_required()
def delete_invitation_code(code_id):
    logger.info(f'=== 删除邀请码: {code_id} ===')
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or user.user_type != 'admin':
            return jsonify({'code': 403, 'message': '只有管理员可以删除邀请码', 'data': None}), 403
        
        code = InvitationCode.query.get(code_id)
        if not code:
            return jsonify({'code': 404, 'message': '邀请码不存在', 'data': None}), 404
        
        db.session.delete(code)
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '邀请码已删除',
            'data': None
        }), 200
        
    except Exception as e:
        logger.error(f'删除邀请码异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500