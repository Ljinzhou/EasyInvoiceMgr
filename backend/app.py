from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
from models import db
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def create_app():
    logger.info('=== 创建Flask应用 ===')
    app = Flask(__name__)
    app.config.from_object(Config)
    logger.info('配置加载完成')
    
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
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
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(events_bp, url_prefix='/api')
    app.register_blueprint(invoices_bp, url_prefix='/api')
    app.register_blueprint(parse_bp, url_prefix='/api')
    app.register_blueprint(invitation_codes_bp, url_prefix='/api')
    app.register_blueprint(vouchers_bp, url_prefix='/api')
    app.register_blueprint(purchase_records_bp, url_prefix='/api')
    logger.info('蓝图注册完成')
    
    with app.app_context():
        db.create_all()
    
    logger.info('=== Flask应用启动成功 ===')
    return app

if __name__ == '__main__':
    logger.info('启动Flask开发服务器')
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
