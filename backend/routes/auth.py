from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    logger.info('=== 用户注册请求 ===')
    try:
        data = request.get_json()
        logger.info(f'注册用户名: {data.get("username")}')
        
        if User.query.filter_by(username=data['username']).first():
            logger.warning(f'用户名已存在: {data["username"]}')
            return jsonify({'code': 1001, 'message': '用户名已存在', 'data': None}), 400
        
        if User.query.filter_by(email=data['email']).first():
            logger.warning(f'邮箱已被注册: {data["email"]}')
            return jsonify({'code': 1002, 'message': '邮箱已被注册', 'data': None}), 400
        
        user = User(
            username=data['username'],
            password_hash=generate_password_hash(data['password']),
            real_name=data['real_name'],
            email=data.get('email'),
            phone=data.get('phone'),
            user_type=data.get('user_type', 'student'),
            organization=data.get('organization'),
            student_or_staff_id=data.get('student_or_staff_id')
        )
        
        db.session.add(user)
        db.session.commit()
        logger.info(f'用户注册成功: {user.username} (ID: {user.user_id})')
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'user_id': user.user_id,
                'username': user.username,
                'real_name': user.real_name,
                'email': user.email,
                'phone': user.phone,
                'user_type': user.user_type,
                'organization': user.organization,
                'student_or_staff_id': user.student_or_staff_id,
                'account_status': user.account_status
            }
        }), 201
        
    except Exception as e:
        logger.error(f'用户注册异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    logger.info('=== 用户登录请求 ===')
    try:
        data = request.get_json()
        logger.info(f'登录用户名: {data.get("username")}')
        
        user = User.query.filter_by(username=data['username']).first()
        
        if not user or not check_password_hash(user.password_hash, data['password']):
            logger.warning(f'登录失败: 用户名或密码错误')
            return jsonify({'code': 1002, 'message': '用户名或密码错误', 'data': None}), 401
        
        if user.account_status != 'active':
            logger.warning(f'登录失败: 账户已被禁用 - {user.username}')
            return jsonify({'code': 1003, 'message': '账户已被禁用', 'data': None}), 403
        
        user.last_login_time = datetime.utcnow()
        db.session.commit()
        
        access_token = create_access_token(identity=user.user_id)
        logger.info(f'用户登录成功: {user.username} (ID: {user.user_id})')
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'token': access_token,
                'user': {
                    'user_id': user.user_id,
                    'username': user.username,
                    'real_name': user.real_name,
                    'email': user.email,
                    'phone': user.phone,
                    'user_type': user.user_type,
                    'organization': user.organization,
                    'student_or_staff_id': user.student_or_staff_id
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f'用户登录异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@auth_bp.route('/users', methods=['GET'])
@jwt_required()
def get_users():
    logger.info('=== 获取用户列表请求 ===')
    try:
        search = request.args.get('search', '')
        user_type = request.args.get('user_type')
        logger.info(f'搜索参数: search={search}, user_type={user_type}')
        
        query = User.query.filter_by(is_deleted=False, account_status='active')
        
        if search:
            query = query.filter(
                db.or_(
                    User.username.ilike(f'%{search}%'),
                    User.real_name.ilike(f'%{search}%')
                )
            )
        
        if user_type:
            query = query.filter_by(user_type=user_type)
        
        users = query.limit(20).all()
        logger.info(f'查询到 {len(users)} 个用户')
        
        users_data = []
        for user in users:
            users_data.append({
                'user_id': user.user_id,
                'username': user.username,
                'real_name': user.real_name,
                'email': user.email,
                'phone': user.phone,
                'user_type': user.user_type,
                'organization': user.organization
            })
        
        logger.info('用户列表返回成功')
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': users_data
        }), 200
        
    except Exception as e:
        logger.error(f'获取用户列表异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@auth_bp.route('/users/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    logger.info(f'=== 获取用户信息请求: user_id={user_id} ===')
    try:
        current_user_id = get_jwt_identity()
        logger.info(f'当前登录用户ID: {current_user_id}')
        
        if current_user_id != user_id:
            logger.warning(f'权限不足: 用户{current_user_id}尝试访问用户{user_id}的信息')
            return jsonify({'code': 403, 'message': '权限不足', 'data': None}), 403
        
        user = User.query.get(user_id)
        if not user:
            logger.warning(f'用户不存在: user_id={user_id}')
            return jsonify({'code': 1003, 'message': '用户不存在', 'data': None}), 404
        
        logger.info(f'用户信息返回成功: {user.username}')
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'user_id': user.user_id,
                'username': user.username,
                'real_name': user.real_name,
                'email': user.email,
                'phone': user.phone,
                'user_type': user.user_type,
                'organization': user.organization,
                'student_or_staff_id': user.student_or_staff_id,
                'avatar_url': user.avatar_url,
                'account_status': user.account_status,
                'register_time': user.register_time.isoformat() if user.register_time else None,
                'last_login_time': user.last_login_time.isoformat() if user.last_login_time else None
            }
        }), 200
        
    except Exception as e:
        logger.error(f'获取用户信息异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500
