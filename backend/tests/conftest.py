"""
Pytest fixtures for EasyInvoiceMgr backend testing.

Usage:
    pytest tests/ -v
    pytest tests/ -v -k "test_login"

Requires PostgreSQL running locally. Set PGPASSWORD env var if needed.
"""

import os
import sys

import pytest

# Ensure the backend directory is in the path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# PostgreSQL test database configuration
TEST_DB_URL = os.environ.get(
    'TEST_DATABASE_URL',
    'postgresql://postgres:root@localhost:5432/easy_invoice_test'
)

os.environ['DATABASE_URL'] = TEST_DB_URL
os.environ['SECRET_KEY'] = 'test-secret-key-for-testing'
os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret-for-testing'
os.environ['STORAGE_BACKEND'] = 'local'
os.environ['ADMIN_PASSWORD'] = 'admin'
os.environ['CORS_ORIGINS'] = 'http://localhost:3000'

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from werkzeug.security import generate_password_hash
from models import db as _db, User


@pytest.fixture(scope='session')
def app():
    """Session-wide Flask application fixture with PostgreSQL."""
    from config import Config, CORS_ORIGINS as cors_origins

    app = Flask(__name__)
    app.config.from_object(Config)
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': TEST_DB_URL,
        'SECRET_KEY': 'test-secret',
        'JWT_SECRET_KEY': 'test-jwt-secret',
        'STORAGE_BACKEND': 'local',
    })

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
        if request.method == 'OPTIONS':
            return app.make_default_options_response()

    JWTManager(app)
    _db.init_app(app)

    from routes.auth import auth_bp
    from routes.events import events_bp
    from routes.invoices import invoices_bp
    from routes.parse import parse_bp
    from routes.invitation_codes import invitation_codes_bp
    from routes.vouchers import vouchers_bp
    from routes.purchase_records import purchase_records_bp
    from routes.system import system_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(events_bp, url_prefix='/api')
    app.register_blueprint(invoices_bp, url_prefix='/api')
    app.register_blueprint(parse_bp, url_prefix='/api')
    app.register_blueprint(invitation_codes_bp, url_prefix='/api')
    app.register_blueprint(vouchers_bp, url_prefix='/api')
    app.register_blueprint(purchase_records_bp, url_prefix='/api')
    app.register_blueprint(system_bp, url_prefix='/api')

    # Create uploads dir
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)

    @app.route('/uploads/<path:filename>')
    def serve_upload_file(filename):
        if '..' in filename or filename.startswith('/'):
            return jsonify({'error': 'invalid'}), 400
        file_path = os.path.join(uploads_dir, filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'not found'}), 404
        return send_from_directory(uploads_dir, filename)

    @app.route('/api/uploads/<path:filename>')
    def serve_api_upload_file(filename):
        return serve_upload_file(filename)

    # Initialize database schema once for the session
    with app.app_context():
        _db.create_all()
        # Seed admin user (PostgreSQL BIGSERIAL handles autoincrement)
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin')
        admin_hash = generate_password_hash(admin_password)
        admin = User(
            username='admin',
            password_hash=admin_hash,
            real_name='Admin',
            email='admin@example.com',
            user_type='admin',
            account_status='active',
        )
        _db.session.add(admin)
        _db.session.commit()

    yield app

    # Teardown: drop all tables after session
    with app.app_context():
        _db.drop_all()


@pytest.fixture(scope='function')
def db(app):
    """Function-scoped DB: create tables, yield, then clean up."""
    with app.app_context():
        _db.create_all()
        from werkzeug.security import generate_password_hash
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin'),
                real_name='Admin',
                email='admin@example.com',
                user_type='admin',
                account_status='active',
            )
            _db.session.add(admin)
            _db.session.commit()
        yield _db
        _db.session.rollback()
        # Truncate all tables for clean next test (preserves schema)
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()


@pytest.fixture(scope='function')
def client(app, db):
    """Flask test client."""
    return app.test_client()


# ── Helper functions ────────────────────────────────────────────────────

def _json(response):
    """Parse JSON from a Flask test response."""
    return response.get_json()


def login_as(client, username='admin', password='admin'):
    """Login and return the JWT token string."""
    resp = client.post('/api/auth/login',
                       json={'username': username, 'password': password})
    data = _json(resp)
    if data and data.get('code') == 200:
        return data['data']['token']
    return None


def register_user(client, username, password, real_name,
                  user_type='student', email=None, code=None):
    """Register a new user and return the response JSON."""
    payload = {
        'username': username,
        'password': password,
        'real_name': real_name,
        'user_type': user_type,
        'email': email if email else f'{username}@auto.test',
    }
    if code:
        payload['invitation_code'] = code
    return client.post('/api/auth/register', json=payload)


def auth_headers(token):
    """Return Authorization header dict for a JWT token."""
    return {'Authorization': f'Bearer {token}'}


# ── Token fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def admin_token(client, db):
    return login_as(client, 'admin', 'admin')


@pytest.fixture
def student_token(client, db):
    register_user(client, 'student1', 'pass123', 'Student One',
                  user_type='student', email='s1@test.com')
    return login_as(client, 'student1', 'pass123')


@pytest.fixture
def teacher_token(client, db):
    register_user(client, 'teacher1', 'pass123', 'Teacher One',
                  user_type='teacher', email='t1@test.com')
    return login_as(client, 'teacher1', 'pass123')


@pytest.fixture
def student_admin_token(client, db):
    register_user(client, 'sa1', 'pass123', 'Student Admin',
                  user_type='student_admin', email='sa1@test.com')
    return login_as(client, 'sa1', 'pass123')


@pytest.fixture
def event_ongoing(client, admin_token, db):
    resp = client.post('/api/events', json={
        'event_name': 'Test Event',
        'description': 'For testing',
        'event_start_time': '2026-06-01T09:00:00+08:00',
        'event_end_time': '2026-06-01T18:00:00+08:00',
        'upload_start_time': '2026-05-01T00:00:00+08:00',
        'upload_end_time': '2026-06-30T23:59:59+08:00',
        'total_budget': 10000,
        'need_invoice_review': True,
    }, headers=auth_headers(admin_token))
    return _json(resp)
