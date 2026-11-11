"""购买记录多文件附件（purchase_record_files）模型测试。

覆盖：
- 一个购买记录挂多份购物凭证/发票，按 sort_order、file_id 排序；
- 删除购买记录时附件级联删除；
- 旧单文件列继续保留（导出/旧备份兼容）；
- SQLite 实表与复合索引按模型创建。
"""
from datetime import date

import models  # noqa: F401  确保全部模型注册进 db.metadata
from models import PurchaseRecord, PurchaseRecordFile, db


def _make_record(**overrides):
    data = dict(
        event_id=1,
        uploader_id=1,
        item_name='测试物品',
        purchase_platform='淘宝',
        purchase_date=date(2026, 1, 1),
        amount=100,
        receipt_image_url='receipts/legacy-receipt.jpg',
    )
    data.update(overrides)
    return PurchaseRecord(**data)


def test_record_files_sorted_and_cascade_deleted(app):
    record = _make_record()
    db.session.add(record)
    db.session.flush()

    db.session.add_all([
        PurchaseRecordFile(record_id=record.record_id, file_type='invoice',
                           file_key='invoices/second.jpg', sort_order=2),
        PurchaseRecordFile(record_id=record.record_id, file_type='receipt',
                           file_key='receipts/first.jpg', sort_order=1),
        PurchaseRecordFile(record_id=record.record_id, file_type='invoice',
                           file_key='invoices/third.jpg', sort_order=2),
    ])
    db.session.commit()

    db.session.expire_all()
    loaded = db.session.get(PurchaseRecord, record.record_id)
    assert [f.file_key for f in loaded.files] == [
        'receipts/first.jpg', 'invoices/second.jpg', 'invoices/third.jpg',
    ]

    db.session.delete(loaded)
    db.session.commit()
    assert db.session.query(PurchaseRecordFile).count() == 0


def test_legacy_single_file_columns_kept(app):
    record = _make_record(
        has_invoice=True,
        invoice_file_key='invoices/legacy.pdf',
        invoice_preview_key='invoices/legacy.jpg',
        invoice_original_filename='legacy.pdf',
    )
    db.session.add(record)
    db.session.commit()

    loaded = db.session.get(PurchaseRecord, record.record_id)
    assert loaded.receipt_image_url == 'receipts/legacy-receipt.jpg'
    assert loaded.invoice_file_key == 'invoices/legacy.pdf'
    assert loaded.invoice_preview_key == 'invoices/legacy.jpg'
    assert loaded.invoice_original_filename == 'legacy.pdf'
    assert loaded.cannot_invoice is False


def test_sqlite_table_and_index_created(app, sqlite_connection):
    columns = {
        row[1] for row in sqlite_connection.execute('PRAGMA table_info(purchase_record_files)')
    }
    assert {
        'file_id', 'record_id', 'file_type', 'file_key', 'preview_key',
        'original_filename', 'file_md5', 'file_size', 'sort_order', 'created_at',
    } <= columns

    indexes = {
        row[1] for row in sqlite_connection.execute('PRAGMA index_list(purchase_record_files)')
    }
    assert 'ix_purchase_record_files_record_type' in indexes
