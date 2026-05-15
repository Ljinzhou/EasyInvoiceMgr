from flask import Flask, send_from_directory, send_file, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
load_dotenv()
from config import Config
from models import db
import logging
import os

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def _read_version():
    """从 VERSION 文件读取应用版本号。"""
    version_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'VERSION')
    try:
        with open(version_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return '1.0.0'


APP_VERSION = _read_version()


def _seed_admin_user(app):
    """Ensure a valid admin user exists, updating password hash if needed."""
    from werkzeug.security import generate_password_hash
    with app.app_context():
        from models import User, db
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin')
        password_hash = generate_password_hash(admin_password)
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                password_hash=password_hash,
                real_name='系统管理员',
                email='admin@example.com',
                user_type='admin',
                account_status='active',
            )
            db.session.add(admin)
            logger.info('已创建默认管理员账户')
        else:
            # Always update password hash to ensure correct hash on every deploy
            admin.password_hash = password_hash
            logger.info('已更新管理员密码')
        db.session.commit()


def create_app():
    logger.info('=== 创建Flask应用 ===')
    app = Flask(__name__)
    app.config.from_object(Config)
    logger.info('配置加载完成')

    # 配置CORS - 通过环境变量支持自定义域名
    from config import CORS_ORIGINS as cors_origins
    logger.info(f'CORS 允许来源: {cors_origins}')
    CORS(app, resources={
        r"/api/*": {
            "origins": cors_origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        },
        r"/uploads/*": {
            "origins": cors_origins,
            "methods": ["GET", "OPTIONS"],
            "allow_headers": ["Content-Type", "Range"],
            "supports_credentials": True
        }
    })

    @app.before_request
    def handle_options_preflight():
        """Handle CORS preflight OPTIONS requests for all routes."""
        if request.method == 'OPTIONS':
            response = app.make_default_options_response()
            return response

    JWTManager(app)
    db.init_app(app)
    from flask_migrate import Migrate
    migrate = Migrate(app, db)
    logger.info('扩展初始化完成')
    
    from routes.auth import auth_bp
    from routes.events import events_bp
    from routes.invoices import invoices_bp
    from routes.parse import parse_bp
    from routes.invitation_codes import invitation_codes_bp
    from routes.vouchers import vouchers_bp
    from routes.purchase_records import purchase_records_bp
    from routes.system import system_bp
    from routes.export import export_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(events_bp, url_prefix='/api')
    app.register_blueprint(invoices_bp, url_prefix='/api')
    app.register_blueprint(parse_bp, url_prefix='/api')
    app.register_blueprint(invitation_codes_bp, url_prefix='/api')
    app.register_blueprint(vouchers_bp, url_prefix='/api')
    app.register_blueprint(purchase_records_bp, url_prefix='/api')
    app.register_blueprint(system_bp, url_prefix='/api')
    app.register_blueprint(export_bp, url_prefix='/api')
    logger.info('蓝图注册完成')

    from routes.export import init_export_service
    init_export_service(app)

    # 配置静态文件服务（用于本地文件访问）
    uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
        logger.info(f'创建uploads目录: {uploads_dir}')

    exports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')
    if not os.path.exists(exports_dir):
        os.makedirs(exports_dir)
        logger.info(f'创建exports目录: {exports_dir}')
    
    @app.route('/uploads/<path:filename>')
    def serve_upload_file(filename):
        """提供上传文件的静态访问"""
        try:
            logger.info(f'📷 静态文件请求: /uploads/{filename}')
            
            # 安全检查：防止路径遍历攻击
            if '..' in filename or filename.startswith('/'):
                logger.warning(f'⚠️ 可疑的文件路径: {filename}')
                return jsonify({'error': '非法请求'}), 400
            
            # 检查文件是否存在
            file_path = os.path.join(uploads_dir, filename)
            if not os.path.exists(file_path):
                logger.error(f'❌ 文件不存在: {file_path}')
                
                # 列出uploads目录中的所有文件用于调试
                existing_files = os.listdir(uploads_dir) if os.path.exists(uploads_dir) else []
                logger.debug(f'📁 uploads目录现有文件: {existing_files[:10]}')  # 只显示前10个
                
                return jsonify({'error': '文件不存在', 'available_files': existing_files[:5]}), 404
            
            # 返回文件并设置正确的Content-Type
            response = send_from_directory(uploads_dir, filename, as_attachment=False)
            
            # 根据文件扩展名设置MIME类型
            ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            mime_types = {
                'png': 'image/png',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'gif': 'image/gif',
                'pdf': 'application/pdf'
            }
            if ext in mime_types:
                response.headers['Content-Type'] = mime_types[ext]
            
            # 设置缓存控制
            response.headers['Cache-Control'] = 'public, max-age=3600'
            
            logger.info(f'✅ 文件发送成功: {filename} ({os.path.getsize(file_path)} bytes)')
            return response
            
        except Exception as e:
            logger.error(f'❌ 无法访问文件 {filename}: {str(e)}', exc_info=True)
            return jsonify({'error': f'服务器错误: {str(e)}'}), 500
    
    @app.route('/api/uploads/<path:filename>')
    def serve_api_upload_file(filename):
        """通过API路径访问上传文件（兼容性）- 委托给主路由"""
        return serve_upload_file(filename)
    
    logger.info('静态文件路由配置完成')
    
    with app.app_context():
        from flask_migrate import upgrade, stamp
        from sqlalchemy import inspect
        import time

        inspector = inspect(db.engine)
        existing_tables = set(inspector.get_table_names())

        if 'alembic_version' in existing_tables:
            # Alembic 已管理 schema - 执行待定迁移
            logger.info('检测到 Alembic 版本控制，执行待定迁移...')
            upgrade()
            logger.info('数据库迁移完成')
        elif 'users' in existing_tables:
            # 已有 v1.0.0 数据库但无 Alembic - 标记为当前 head
            logger.info('检测到已有数据库（v1.0.0），标记为当前版本...')
            stamp(revision='head')
            logger.info('已标记数据库版本为当前 head')
        else:
            # 全新安装 - 等待 base.sql 完成初始化
            logger.info('新安装检测：等待数据库初始化...')
            for attempt in range(30):
                time.sleep(1)
                inspector = inspect(db.engine)
                tables = set(inspector.get_table_names())
                if 'users' in tables:
                    logger.info(f'数据库已初始化 ({len(tables)} 张表)，标记版本...')
                    stamp(revision='head')
                    break
            else:
                logger.error('数据库初始化超时（30秒），base.sql 可能未执行')
                db.create_all()
                logger.info('使用 SQLAlchemy 创建表作为后备方案')
                stamp(revision='head')

        _seed_admin_user(app)

    # 初始化备份服务和定时调度器（在数据库迁移完成后）
    from utils.backup_service import init_backup_service
    init_backup_service(app)

    logger.info('=== Flask应用启动成功 ===')
    return app

if __name__ == '__main__':
    logger.info('启动Flask开发服务器')
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
