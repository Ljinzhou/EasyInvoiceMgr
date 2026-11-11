"""发票预览图链路回归测试。

覆盖：
- PDF 转 JPG 工具可真正产出 JPEG（防止 `import io` 缺失一类问题复发）；
- 解析失败也要保存预览图：`_persist_invoice_preview` 同时更新附件行与旧单文件列；
- 接口级：`/api/upload-file` 返回 PDF 预览图；`/api/parse-invoice` 在 AI 解析失败时
  仍保存发票文件与预览图，并返回 `ai_parse_success=false` + `ai_parse_error`。
"""
import importlib
from datetime import date

import pytest

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz

import models  # noqa: F401  确保全部模型注册进 db.metadata
from models import PurchaseRecord, PurchaseRecordFile, db
from routes.purchase_records import _persist_invoice_preview
from utils.pdf_converter import PDFConverter


def _make_pdf_bytes():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), 'EasyInvoiceMgr preview test')
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_convert_pdf_to_jpg_returns_jpeg():
    assert PDFConverter.is_pdf_available()

    jpg_bytes, width, height, page_count = PDFConverter.convert_pdf_to_jpg(_make_pdf_bytes())

    assert jpg_bytes, 'PDF 转 JPG 应返回图片数据'
    assert jpg_bytes[:3] == b'\xff\xd8\xff', '返回值应是 JPEG'
    assert page_count == 1
    assert width > 0 and height > 0


def _make_record(**overrides):
    data = dict(
        event_id=1,
        uploader_id=1,
        item_name='测试物品',
        purchase_platform='淘宝',
        purchase_date=date(2026, 1, 1),
        amount=100,
        receipt_image_url='receipts/legacy-receipt.jpg',
        cannot_invoice=False,
    )
    data.update(overrides)
    return PurchaseRecord(**data)


def test_persist_invoice_preview_updates_attachment_and_legacy_columns(app):
    record = _make_record(
        has_invoice=True,
        invoice_file_key='invoices/legacy.pdf',
        invoice_original_filename='legacy.pdf',
    )
    db.session.add(record)
    db.session.flush()
    db.session.add(PurchaseRecordFile(
        record_id=record.record_id,
        file_type=PurchaseRecord.FILE_TYPE_INVOICE,
        file_key='invoices/legacy.pdf',
        preview_key=None,
        original_filename='legacy.pdf',
        sort_order=0,
    ))
    db.session.commit()

    _persist_invoice_preview(record, 'invoices/legacy.pdf', 'invoices/legacy_preview.jpg')

    db.session.expire_all()
    loaded = db.session.get(PurchaseRecord, record.record_id)
    invoice_rows = [row for row in loaded.files if row.file_type == PurchaseRecord.FILE_TYPE_INVOICE]
    assert len(invoice_rows) == 1
    assert invoice_rows[0].preview_key == 'invoices/legacy_preview.jpg'
    assert loaded.invoice_preview_key == 'invoices/legacy_preview.jpg'


class _FakeStorage:
    """内存版 storage_manager：避免测试污染真实 uploads/COS。"""

    def __init__(self):
        self.files = {}

    def is_available(self):
        return True

    def upload_bytes(self, data, key):
        self.files[key] = data

    def get_presigned_url(self, key, expires=None):
        return f'https://cos.example/{key}'

    def download_file(self, key):
        return self.files.get(key)


@pytest.fixture()
def api_env(tmp_path, monkeypatch):
    """真实 create_app + 临时 SQLite，返回 (application, client, admin_id)。"""
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///' + (tmp_path / 'api.sqlite').as_posix())
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')
    monkeypatch.setenv('ADMIN_PASSWORD', 'admin')

    import config
    importlib.reload(config)
    import app as app_module
    importlib.reload(app_module)

    application = app_module.create_app()

    with application.app_context():
        from models import User
        admin = User.query.filter_by(username='admin').first()
        admin_id = admin.user_id

    client = application.test_client()
    yield application, client, admin_id
    application = None


def _auth(application, user_id):
    from flask_jwt_extended import create_access_token
    with application.app_context():
        token = create_access_token(identity=str(user_id))
    return {'Authorization': f'Bearer {token}'}


def _patch_storage(monkeypatch):
    import routes.parse as parse_module
    fake = _FakeStorage()
    monkeypatch.setattr(parse_module, 'storage_manager', fake)
    return fake


def test_upload_file_returns_pdf_preview(api_env, monkeypatch):
    """普通上传也应把 PDF 转成 JPG 预览图并返回 preview_key。"""
    application, client, admin_id = api_env
    fake = _patch_storage(monkeypatch)

    response = client.post(
        '/api/upload-file',
        data={'file': (_bytes_io(_make_pdf_bytes()), 'invoice.pdf')},
        headers=_auth(application, admin_id),
        content_type='multipart/form-data',
    )

    assert response.status_code == 200, response.get_json()
    data = response.get_json()['data']
    assert data['file_key'].endswith('.pdf')
    assert data['preview_key'] and data['preview_key'].endswith('_preview.jpg')
    assert fake.files[data['preview_key']][:3] == b'\xff\xd8\xff'


def test_parse_invoice_saves_preview_when_ai_fails(api_env, monkeypatch):
    """AI 解析失败时，发票文件与预览图也必须保存。"""
    application, client, admin_id = api_env
    fake = _patch_storage(monkeypatch)

    import routes.parse as parse_module

    class _FailingParser:
        @staticmethod
        def is_available():
            return True

        @staticmethod
        def parse_file(file_bytes, filename):
            return {'success': False, 'message': '模拟AI解析失败', 'data': None}

    monkeypatch.setattr(parse_module, 'invoice_parser', _FailingParser())

    response = client.post(
        '/api/parse-invoice',
        data={'file': (_bytes_io(_make_pdf_bytes()), 'invoice.pdf')},
        headers=_auth(application, admin_id),
        content_type='multipart/form-data',
    )

    assert response.status_code == 200, response.get_json()
    payload = response.get_json()
    data = payload['data']
    assert data['file_key'].endswith('.pdf')
    assert data['preview_key'] and data['preview_key'].endswith('_preview.jpg')
    assert data['ai_parse_success'] is False
    assert '模拟AI解析失败' in (data['ai_parse_error'] or '')
    assert 'AI解析失败' in payload['message']
    # 原始 PDF 与预览 JPG 都落盘
    assert fake.files[data['file_key']][:4] == b'%PDF'
    assert fake.files[data['preview_key']][:3] == b'\xff\xd8\xff'


def test_preview_invoice_backfills_missing_preview_for_legacy_pdf(api_env, monkeypatch):
    """历史 PDF 发票没有预览图时，预览接口按需补生成并落库。"""
    application, client, admin_id = api_env

    import routes.purchase_records as pr_module
    fake = _FakeStorage()
    monkeypatch.setattr(pr_module, 'storage_manager', fake)
    fake.files['invoices/legacy.pdf'] = _make_pdf_bytes()

    with application.app_context():
        from models import Event
        event = Event(event_name='预览回填测试活动', creator_id=admin_id)
        db.session.add(event)
        db.session.flush()

        record = _make_record(
            event_id=event.event_id,
            uploader_id=admin_id,
            has_invoice=True,
            invoice_file_key='invoices/legacy.pdf',
            invoice_original_filename='legacy.pdf',
        )
        db.session.add(record)
        db.session.commit()
        record_id = record.record_id

    response = client.get(
        f'/api/records/{record_id}/preview-invoice',
        headers=_auth(application, admin_id),
    )

    assert response.status_code == 200, response.get_json()
    data = response.get_json()['data']
    assert data['is_pdf'] is True
    assert data['preview_url'] and '_preview.jpg' in data['preview_url']

    # 预览图写入了 fake storage，并持久化到 record.invoice_preview_key
    generated = [key for key in fake.files if key.endswith('_preview.jpg')]
    assert generated, '应生成并保存预览 JPG'
    assert fake.files[generated[0]][:3] == b'\xff\xd8\xff'

    with application.app_context():
        loaded = db.session.get(PurchaseRecord, record_id)
        assert loaded.invoice_preview_key == generated[0]


def _bytes_io(data):
    import io
    return io.BytesIO(data)
