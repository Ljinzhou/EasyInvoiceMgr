from flask import Flask, send_from_directory, send_file
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


def _seed_admin_user(app):
    """Create default admin user if not exists."""
    from werkzeug.security import generate_password_hash
    with app.app_context():
        from models import User, db
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin'),
                real_name='系统管理员',
                email='admin@example.com',
                user_type='admin',
                account_status='active',
            )
            db.session.add(admin)
            db.session.commit()
            logger.info('已创建默认管理员账户 (admin/admin)')


def create_app():
    logger.info('=== 创建Flask应用 ===')
    app = Flask(__name__)
    app.config.from_object(Config)
    logger.info('配置加载完成')
    
    # 配置CORS - 允许API和静态文件访问
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        },
        r"/uploads/*": {
            "origins": ["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001"],
            "methods": ["GET", "OPTIONS"],
            "allow_headers": ["Content-Type", "Range"],
            "supports_credentials": True
        }
    })
    JWTManager(app)
    db.init_app(app)
    logger.info('扩展初始化完成')
    
    from routes.auth import auth_bp
    from routes.events import events_bp
    from routes.invoices import invoices_bp
    from routes.parse import parse_bp
    from routes.invitation_codes import invitation_codes_bp
    from routes.vouchers import vouchers_bp
    from routes.purchase_records import purchase_records_bp
    from routes.export import export_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(events_bp, url_prefix='/api')
    app.register_blueprint(invoices_bp, url_prefix='/api')
    app.register_blueprint(parse_bp, url_prefix='/api')
    app.register_blueprint(invitation_codes_bp, url_prefix='/api')
    app.register_blueprint(vouchers_bp, url_prefix='/api')
    app.register_blueprint(purchase_records_bp, url_prefix='/api')
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
        # Only create tables if they don't already exist (e.g. from base.sql)
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        if 'users' not in existing_tables:
            db.create_all()
            logger.info('数据库表已通过 SQLAlchemy 创建')
        else:
            logger.info(f'数据库表已存在，跳过创建 ({len(existing_tables)} 张表)')
        _seed_admin_user(app)

    logger.info('=== Flask应用启动成功 ===')
    return app

if __name__ == '__main__':
    logger.info('启动Flask开发服务器')
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
