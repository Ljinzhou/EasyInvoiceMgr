from flask import Flask, send_from_directory, send_file, request, jsonify
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
    """确保存在有效的管理员用户，必要时更新密码哈希。"""
    from werkzeug.security import generate_password_hash
    from utils.crypto_utils import encrypt_password
    with app.app_context():
        from models import User, db
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin')
        password_hash = generate_password_hash(admin_password)
        password_encrypted = encrypt_password(admin_password)
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                password_hash=password_hash,
                password_encrypted=password_encrypted,
                real_name='系统管理员',
                email='admin@example.com',
                user_type='admin',
                account_status='active',
            )
            db.session.add(admin)
            logger.info('已创建默认管理员账户')
        else:
            # 每次部署都更新密码哈希，确保哈希值正确
            admin.password_hash = password_hash
            admin.password_encrypted = password_encrypted
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
        """处理所有路由的 CORS 预检 OPTIONS 请求。"""
        if request.method == 'OPTIONS':
            response = app.make_default_options_response()
            return response

    JWTManager(app)
    # 支持从查询参数获取JWT令牌（用于浏览器直接下载文件等场景）
    app.config['JWT_TOKEN_LOCATION'] = ['headers', 'query_string']
    app.config['JWT_QUERY_STRING_NAME'] = 'token'
    # 本项目已从 PostgreSQL 迁移到 SQLite，只支持 sqlite 方言。
    # 这里用 make_url 纯字符串解析，不创建引擎、不导入任何 DBAPI，
    # 避免旧 DATABASE_URL 残留时先崩在驱动层（连接参数不被驱动识别）。
    from sqlalchemy.engine import make_url
    backend_name = make_url(app.config['SQLALCHEMY_DATABASE_URI']).get_backend_name()
    if backend_name != 'sqlite':
        raise RuntimeError(
            f'数据库方言为 {backend_name!r}，本项目只支持 SQLite。'
            f'请检查环境变量 DATABASE_URL 或 backend/.env 中的 DATABASE_URL，'
            f'当前配置为：{make_url(app.config["SQLALCHEMY_DATABASE_URI"]).render_as_string(hide_password=True)}'
        )

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
    from routes.operation_logs import operation_logs_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(events_bp, url_prefix='/api')
    app.register_blueprint(invoices_bp, url_prefix='/api')
    app.register_blueprint(parse_bp, url_prefix='/api')
    app.register_blueprint(invitation_codes_bp, url_prefix='/api')
    app.register_blueprint(vouchers_bp, url_prefix='/api')
    app.register_blueprint(purchase_records_bp, url_prefix='/api')
    app.register_blueprint(system_bp, url_prefix='/api')
    app.register_blueprint(export_bp, url_prefix='/api')
    app.register_blueprint(operation_logs_bp, url_prefix='/api/operation-logs')
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
        from utils.db_engine import register_sqlite_pragmas
        from utils.schema_init import ensure_schema

        register_sqlite_pragmas(db.engine)
        ensure_schema()

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
