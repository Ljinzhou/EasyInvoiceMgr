from flask import Blueprint, request, jsonify, make_response
from flask_cors import cross_origin
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, InvitationCode
from config import CORS_ORIGINS
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST', 'OPTIONS'])
@cross_origin(origins=CORS_ORIGINS, supports_credentials=True)
def register():
    if request.method == 'OPTIONS':
        response = make_response()
        origin = request.headers.get('Origin', 'http://localhost:3001')
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response
    
    logger.info('=== 用户注册请求 ===')
    try:
        data = request.get_json()
        logger.info(f'注册用户名: {data.get("username")}')
        
        # 验证邀请码
        invitation_code = data.get('invitation_code')
        if invitation_code:
            logger.info(f'验证邀请码: {invitation_code}')
            code_obj = InvitationCode.query.filter_by(code=invitation_code).first()
            
            if not code_obj:
                return jsonify({'code': 400, 'message': '邀请码不存在', 'data': None}), 400
            
            if not code_obj.is_active:
                return jsonify({'code': 400, 'message': '邀请码已被禁用', 'data': None}), 400
            
            if code_obj.expires_at < datetime.now(timezone.utc):
                return jsonify({'code': 400, 'message': '邀请码已过期', 'data': None}), 400
            
            if code_obj.max_uses > 0 and code_obj.used_count >= code_obj.max_uses:
                return jsonify({'code': 400, 'message': '邀请码使用次数已达上限', 'data': None}), 400
            
            # 验证用户类型
            user_type = data.get('user_type', 'student')
            if user_type != code_obj.target_user_type:
                return jsonify({'code': 400, 'message': f'邀请码只能用于注册{code_obj.target_user_type}类型的账户', 'data': None}), 400
        
        if User.query.filter_by(username=data['username']).first():
            logger.warning(f'用户名已存在: {data["username"]}')
            return jsonify({'code': 1001, 'message': '用户名已存在', 'data': None}), 400
        
        email = data.get('email')
        if email and User.query.filter_by(email=email).first():
            logger.warning(f'邮箱已被注册: {email}')
            return jsonify({'code': 1002, 'message': '邮箱已被注册', 'data': None}), 400
        
        user = User(
            username=data['username'],
            password_hash=generate_password_hash(data['password']),
            real_name=data['real_name'],
            email=data.get('email'),
            phone=data.get('phone'),
            user_type=data.get('user_type', 'student'),
            student_or_staff_id=data.get('student_or_staff_id')
        )
        
        db.session.add(user)
        
        # 更新邀请码使用次数
        if invitation_code and code_obj:
            code_obj.used_count += 1
            logger.info(f'邀请码使用次数更新: {code_obj.code}, 新次数: {code_obj.used_count}')
        
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
                'student_or_staff_id': user.student_or_staff_id,
                'account_status': user.account_status
            }
        }), 201
        
    except Exception as e:
        logger.error(f'用户注册异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@auth_bp.route('/login', methods=['POST', 'OPTIONS'])
@cross_origin(origins=CORS_ORIGINS, supports_credentials=True)
def login():
    if request.method == 'OPTIONS':
        response = make_response()
        origin = request.headers.get('Origin', 'http://localhost:3001')
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response
    
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
        
        access_token = create_access_token(identity=str(user.user_id))
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
                    'student_or_staff_id': user.student_or_staff_id,
                    'avatar_url': user.avatar_url
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
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)

        # Role check: only admin, teacher, student_admin can view user list (BUG-03 fix)
        if not current_user or current_user.user_type not in ['admin', 'teacher', 'student_admin']:
            return jsonify({'code': 403, 'message': '权限不足', 'data': None}), 403

        search = request.args.get('search', '')
        user_type = request.args.get('user_type')
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        logger.info(f'搜索参数: search={search}, user_type={user_type}, page={page}, page_size={page_size}')

        query = User.query.filter_by(is_deleted=False)
        
        if search:
            query = query.filter(
                db.or_(
                    User.username.ilike(f'%{search}%'),
                    User.real_name.ilike(f'%{search}%'),
                    User.email.ilike(f'%{search}%')
                )
            )
        
        if user_type:
            query = query.filter_by(user_type=user_type)
        
        total = query.count()
        users = query.order_by(User.created_at.desc()).paginate(page=page, per_page=page_size, error_out=False).items
        logger.info(f'查询到 {len(users)} 个用户，总共 {total} 个用户')
        
        users_data = []
        for user in users:
            users_data.append({
                'user_id': user.user_id,
                'username': user.username,
                'real_name': user.real_name,
                'email': user.email,
                'phone': user.phone,
                'user_type': user.user_type,
                'student_or_staff_id': user.student_or_staff_id,
                'account_status': user.account_status,
                'register_time': user.register_time.isoformat() if user.register_time else None,
                'avatar_url': user.avatar_url
            })
        
        logger.info('用户列表返回成功')
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'total': total,
                'page': page,
                'page_size': page_size,
                'data': users_data
            }
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

@auth_bp.route('/users/<int:user_id>', methods=['PUT', 'OPTIONS'])
@cross_origin(origins=CORS_ORIGINS, supports_credentials=True)
@jwt_required()
def update_user(user_id):
    if request.method == 'OPTIONS':
        response = make_response()
        origin = request.headers.get('Origin', 'http://localhost:3001')
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'PUT,OPTIONS')
        return response
    
    logger.info(f'=== 更新用户信息请求: user_id={user_id} ===')
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user:
            return jsonify({'code': 401, 'message': '用户未登录', 'data': None}), 401
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'code': 1003, 'message': '用户不存在', 'data': None}), 404
        
        data = request.get_json()
        
        if current_user.user_type == 'admin':
            if 'real_name' in data:
                user.real_name = data['real_name']
            if 'email' in data:
                user.email = data['email']
            if 'phone' in data:
                user.phone = data['phone']
            if 'student_or_staff_id' in data:
                user.student_or_staff_id = data['student_or_staff_id']
            if 'user_type' in data:
                user.user_type = data['user_type']
            if 'account_status' in data:
                user.account_status = data['account_status']
        elif current_user_id == user_id:
            if 'real_name' in data:
                user.real_name = data['real_name']
            if 'email' in data:
                user.email = data['email']
            if 'phone' in data:
                user.phone = data['phone']
            if 'student_or_staff_id' in data:
                user.student_or_staff_id = data['student_or_staff_id']
        else:
            return jsonify({'code': 403, 'message': '权限不足', 'data': None}), 403
        
        db.session.commit()
        logger.info(f'用户信息更新成功: {user.username}')
        
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
                'student_or_staff_id': user.student_or_staff_id,
                'account_status': user.account_status
            }
        }), 200
        
    except Exception as e:
        logger.error(f'更新用户信息异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

ALLOWED_AVATAR_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
MAX_AVATAR_SIZE = 5 * 1024 * 1024


@auth_bp.route('/avatar', methods=['GET'])
@jwt_required()
def get_avatar():
    logger.info('=== 获取用户头像请求 ===')
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if not user:
            return jsonify({'code': 404, 'message': '用户不存在', 'data': None}), 404

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'avatar_url': user.avatar_url
            }
        }), 200

    except Exception as e:
        logger.error(f'获取头像异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


@auth_bp.route('/avatar/upload', methods=['POST', 'OPTIONS'])
@cross_origin(origins=CORS_ORIGINS, supports_credentials=True)
@jwt_required()
def upload_avatar():
    if request.method == 'OPTIONS':
        response = make_response()
        origin = request.headers.get('Origin', 'http://localhost:3001')
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response

    logger.info('=== 上传头像请求 ===')
    try:
        current_user_id = get_jwt_identity()
        current_user_id_int = int(current_user_id)
        user = User.query.get(current_user_id_int)

        if not user:
            return jsonify({'code': 404, 'message': '用户不存在', 'data': None}), 404

        if 'file' not in request.files:
            return jsonify({'code': 400, 'message': '请选择图片文件', 'data': None}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'code': 400, 'message': '请选择图片文件', 'data': None}), 400

        if '.' not in file.filename:
            return jsonify({'code': 400, 'message': '文件需要包含扩展名', 'data': None}), 400

        file_ext = file.filename.rsplit('.', 1)[1].lower()
        if file_ext not in ALLOWED_AVATAR_EXTENSIONS:
            return jsonify({'code': 400, 'message': '仅支持 JPG、PNG、WEBP 格式的图片', 'data': None}), 400

        file_bytes = file.read()
        if len(file_bytes) > MAX_AVATAR_SIZE:
            return jsonify({'code': 400, 'message': '图片大小不能超过 5MB', 'data': None}), 400

        content_type_map = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'webp': 'image/webp'
        }
        content_type = content_type_map.get(file_ext, 'image/jpeg')

        import hashlib
        file_md5 = hashlib.md5(file_bytes).hexdigest()

        from utils.storage import storage_manager

        if storage_manager.is_available():
            if user.avatar_url:
                old_key = user.avatar_url.split('/')[-1] if '/' in user.avatar_url else user.avatar_url
                try:
                    storage_manager.delete_file(old_key)
                    logger.info(f'已删除旧头像: {old_key}')
                except Exception as del_err:
                    logger.warning(f'删除旧头像失败（可能不存在）: {str(del_err)}')

            result = storage_manager.upload_avatar(current_user_id_int, file_bytes, content_type)
            user.avatar_url = result['avatar_url']
            db.session.commit()

            logger.info(f'头像上传成功: user_id={current_user_id_int}')

            return jsonify({
                'code': 200,
                'message': '头像上传成功',
                'data': {
                    'avatar_url': result['avatar_url'],
                    'file_md5': file_md5
                }
            }), 200

        else:
            import os
            uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads', 'avatars')
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir)

            import uuid as uuid_lib
            local_filename = f"{current_user_id_int}_{uuid_lib.uuid4().hex[:8]}.{file_ext}"
            local_path = os.path.join(uploads_dir, local_filename)

            with open(local_path, 'wb') as f:
                f.write(file_bytes)

            avatar_url = f'/uploads/avatars/{local_filename}'
            user.avatar_url = avatar_url
            db.session.commit()

            logger.info(f'头像保存到本地成功: {avatar_url}')

            return jsonify({
                'code': 200,
                'message': '头像上传成功',
                'data': {
                    'avatar_url': avatar_url,
                    'file_md5': file_md5
                }
            }), 200

    except Exception as e:
        logger.error(f'头像上传异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


@auth_bp.route('/avatar', methods=['DELETE', 'OPTIONS'])
@cross_origin(origins=CORS_ORIGINS, supports_credentials=True)
@jwt_required()
def delete_avatar():
    if request.method == 'OPTIONS':
        response = make_response()
        origin = request.headers.get('Origin', 'http://localhost:3001')
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'DELETE,OPTIONS')
        return response

    logger.info('=== 删除头像请求 ===')
    try:
        current_user_id = get_jwt_identity()
        current_user_id_int = int(current_user_id)
        user = User.query.get(current_user_id_int)

        if not user:
            return jsonify({'code': 404, 'message': '用户不存在', 'data': None}), 404

        if user.avatar_url:
            from utils.storage import storage_manager
            old_key = user.avatar_url.split('/')[-1] if '/' in user.avatar_url else user.avatar_url
            try:
                storage_manager.delete_file(old_key)
                logger.info(f'头像文件已删除: {old_key}')
            except Exception as del_err:
                logger.warning(f'删除头像文件失败: {str(del_err)}')

            user.avatar_url = None
            db.session.commit()
            logger.info(f'头像已删除: user_id={current_user_id_int}')

        return jsonify({
            'code': 200,
            'message': '头像已删除',
            'data': None
        }), 200

    except Exception as e:
        logger.error(f'删除头像异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


@auth_bp.route('/users/<int:user_id>', methods=['DELETE', 'OPTIONS'])
@cross_origin(origins=CORS_ORIGINS, supports_credentials=True)
@jwt_required()
def delete_user(user_id):
    if request.method == 'OPTIONS':
        response = make_response()
        origin = request.headers.get('Origin', 'http://localhost:3001')
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'DELETE,OPTIONS')
        return response
    
    logger.info(f'=== 删除用户请求: user_id={user_id} ===')
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user or current_user.user_type != 'admin':
            return jsonify({'code': 403, 'message': '权限不足', 'data': None}), 403
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'code': 1003, 'message': '用户不存在', 'data': None}), 404
        
        if user.user_type == 'admin':
            return jsonify({'code': 403, 'message': '不能删除管理员账户', 'data': None}), 403
        
        user.is_deleted = True
        db.session.commit()
        logger.info(f'用户删除成功: {user.username}')
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': None
        }), 200
        
    except Exception as e:
        logger.error(f'删除用户异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500
