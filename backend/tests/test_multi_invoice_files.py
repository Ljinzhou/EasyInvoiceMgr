"""多张发票逐张落库测试。

覆盖：
- 前端提交的附件数组能携带每张发票各自的解析结果；
- 附件表按发票逐张存储号码/日期/税号/类型/金额/解析状态；
- 记录级字段（旧单文件列 + 号码/税号/日期/合计）按多张发票汇总；
- 单张重解析只改目标附件行。
"""
from datetime import date

import models  # noqa: F401  确保全部模型注册进 db.metadata
from models import PurchaseRecord, PurchaseRecordFile, db
from routes.purchase_records import (
    _apply_parsed_info_to_row,
    _first_invoice_file,
    _normalize_file_entries,
    _replace_record_files,
    _sync_legacy_file_columns,
)


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


INVOICE_ENTRIES = [
    {
        'file_key': 'invoices/a.pdf',
        'preview_key': 'invoices/a_preview.png',
        'original_filename': 'a.pdf',
        'invoice_number': '11111111',
        'invoice_date': '2026-03-01',
        'invoice_tax_number': 'TAX-A',
        'invoice_type': '餐饮',
        'item_name': '*餐饮*午餐',
        'amount': 100.5,
        'parse_status': 'parsed',
    },
    {
        'file_key': 'invoices/b.pdf',
        'preview_key': 'invoices/b_preview.png',
        'original_filename': 'b.pdf',
        'invoice_number': '22222222',
        'invoice_date': '2026-02-15',
        'invoice_tax_number': 'TAX-B',
        'invoice_type': '交通',
        'item_name': '*运输*高铁',
        'amount': 200.25,
        'parse_status': 'parsed',
    },
]


def test_normalize_file_entries_keeps_per_invoice_fields():
    entries = _normalize_file_entries(
        [
            {
                'file_key': 'invoices/a.pdf',
                'invoice_number': ' 111 ',
                'invoice_date': '2026-03-01',
                'tax_number': 'TAX-A',
                'item_name': '午餐',
                'total_amount': '88.80',
                'parse_status': 'parsed',
            },
            # 重复 file_key 只保留第一条
            {'file_key': 'invoices/a.pdf', 'invoice_number': '999'},
            # 缺 file_key 直接丢弃
            {'invoice_number': '333'},
        ],
        PurchaseRecord.FILE_TYPE_INVOICE,
    )

    assert len(entries) == 1
    entry = entries[0]
    assert entry['invoice_number'] == '111'
    assert entry['invoice_date'] == date(2026, 3, 1)
    assert entry['invoice_tax_number'] == 'TAX-A'
    assert entry['invoice_item_name'] == '午餐'
    assert entry['invoice_amount'] == 88.8


def test_normalize_file_entries_ignores_invoice_fields_for_receipts():
    entries = _normalize_file_entries(
        [{'file_key': 'receipts/a.jpg', 'invoice_number': '111', 'amount': 10}],
        PurchaseRecord.FILE_TYPE_RECEIPT,
    )
    assert entries == [{
        'file_key': 'receipts/a.jpg',
        'preview_key': None,
        'original_filename': None,
        'file_md5': None,
    }]


def test_replace_files_and_sync_aggregates_multi_invoices(app):
    record = _make_record()
    db.session.add(record)
    db.session.flush()

    _replace_record_files(
        record, PurchaseRecord.FILE_TYPE_RECEIPT,
        _normalize_file_entries(
            [{'file_key': 'receipts/1.jpg', 'original_filename': '1.jpg'}],
            PurchaseRecord.FILE_TYPE_RECEIPT,
        ),
    )
    _replace_record_files(
        record, PurchaseRecord.FILE_TYPE_INVOICE,
        _normalize_file_entries(INVOICE_ENTRIES, PurchaseRecord.FILE_TYPE_INVOICE),
    )
    _sync_legacy_file_columns(record)
    db.session.commit()
    db.session.expire_all()

    loaded = db.session.get(PurchaseRecord, record.record_id)
    invoices = [f for f in loaded.files if f.file_type == PurchaseRecord.FILE_TYPE_INVOICE]
    assert [f.sort_order for f in invoices] == [0, 1]
    assert [f.invoice_number for f in invoices] == ['11111111', '22222222']
    assert [float(f.invoice_amount) for f in invoices] == [100.5, 200.25]
    assert invoices[1].invoice_type == '交通'
    assert invoices[0].parse_status == 'parsed'
    assert invoices[0].parsed_at is not None

    # 记录级字段为汇总镜像：合计金额、首张号码/税号、最早开票日期
    assert float(loaded.total_amount) == 300.75
    assert loaded.invoice_number == '11111111'
    assert loaded.invoice_tax_number == 'TAX-A'
    assert loaded.invoice_date == date(2026, 2, 15)
    assert loaded.invoice_type == '餐饮'
    # 旧单文件列仍指向第一张，导出/兼容逻辑不受影响
    assert loaded.invoice_file_key == 'invoices/a.pdf'
    assert loaded.invoice_preview_key == 'invoices/a_preview.png'
    assert loaded.has_invoice is True


def test_first_invoice_file_can_target_by_file_id(app):
    record = _make_record()
    db.session.add(record)
    db.session.flush()
    _replace_record_files(
        record, PurchaseRecord.FILE_TYPE_INVOICE,
        _normalize_file_entries(INVOICE_ENTRIES, PurchaseRecord.FILE_TYPE_INVOICE),
    )
    _sync_legacy_file_columns(record)
    db.session.commit()

    second = [f for f in record.files if f.file_type == PurchaseRecord.FILE_TYPE_INVOICE][1]
    targeted = _first_invoice_file(record, second.file_id)
    assert targeted['file_id'] == second.file_id
    assert targeted['file_key'] == 'invoices/b.pdf'
    assert targeted['invoice_number'] == '22222222'
    assert targeted['amount'] == 200.25

    # 不传 file_id 时回落到第一张
    assert _first_invoice_file(record)['file_key'] == 'invoices/a.pdf'
    # 显式指定了不存在的 file_id：返回 None，由调用方报 404（避免误改其他发票）
    assert _first_invoice_file(record, 999999) is None


def test_apply_parsed_info_updates_only_target_row(app):
    record = _make_record()
    db.session.add(record)
    db.session.flush()
    _replace_record_files(
        record, PurchaseRecord.FILE_TYPE_INVOICE,
        _normalize_file_entries(INVOICE_ENTRIES, PurchaseRecord.FILE_TYPE_INVOICE),
    )
    _sync_legacy_file_columns(record)
    db.session.commit()

    second = [f for f in record.files if f.file_type == PurchaseRecord.FILE_TYPE_INVOICE][1]
    _apply_parsed_info_to_row(second, {
        'invoice_number': ' 22222222 ',
        'date': '2026-04-02',
        'invoice_tax_number': 'TAX-B2',
        'invoice_type': '住宿',
        'item_name': '*住宿*酒店',
        'amount': '520.005',
    })
    db.session.commit()
    db.session.expire_all()

    invoices = [
        f for f in db.session.get(PurchaseRecord, record.record_id).files
        if f.file_type == PurchaseRecord.FILE_TYPE_INVOICE
    ]
    # 第一张不受影响
    assert invoices[0].invoice_number == '11111111'
    assert float(invoices[0].invoice_amount) == 100.5
    # 第二张按解析结果更新（金额四舍五入到分）
    assert invoices[1].invoice_number == '22222222'
    assert invoices[1].invoice_date == date(2026, 4, 2)
    assert invoices[1].invoice_type == '住宿'
    assert float(invoices[1].invoice_amount) == 520.01
    assert invoices[1].parse_status == 'parsed'
    assert invoices[1].parse_error is None


def test_apply_parsed_info_ignores_invalid_amount_and_date(app):
    row = PurchaseRecordFile(file_type='invoice', file_key='invoices/x.pdf', sort_order=0)
    _apply_parsed_info_to_row(row, {
        'invoice_number': 'X1',
        'date': '不是日期',
        'amount': 'abc',
    })
    assert row.invoice_number == 'X1'
    assert row.invoice_date is None
    assert row.invoice_amount is None
    assert row.parse_status == 'parsed'


def test_find_invoice_by_md5_detects_duplicate_and_honours_exclude(app):
    """PDF 选文件即上传，保存不再走 /parse-invoice，查重改由 find_invoice_by_md5 承担。"""
    from routes.parse import InvoiceUploadService

    record = _make_record()
    db.session.add(record)
    db.session.flush()
    _replace_record_files(
        record, PurchaseRecord.FILE_TYPE_INVOICE,
        _normalize_file_entries(
            [{'file_key': 'invoices/dup.pdf', 'file_md5': 'md5-dup-1', 'invoice_number': 'D1'}],
            PurchaseRecord.FILE_TYPE_INVOICE,
        ),
    )
    _sync_legacy_file_columns(record)
    db.session.commit()

    hit = InvoiceUploadService.find_invoice_by_md5('md5-dup-1')
    assert hit['duplicate'] is True
    assert hit['record_id'] == record.record_id

    # 编辑同一条记录时允许重传自己的发票
    same_record = InvoiceUploadService.find_invoice_by_md5('md5-dup-1', record.record_id)
    assert same_record['duplicate'] is False

    # 未出现过的 md5 不算重复
    assert InvoiceUploadService.find_invoice_by_md5('md5-not-exists')['duplicate'] is False


def test_find_invoice_by_md5_detects_duplicate_and_honours_exclude(app):
    """PDF 选文件即上传，保存不再走 /parse-invoice，查重改由 find_invoice_by_md5 承担。"""
    from routes.parse import InvoiceUploadService

    record = _make_record()
    db.session.add(record)
    db.session.flush()
    _replace_record_files(
        record, PurchaseRecord.FILE_TYPE_INVOICE,
        _normalize_file_entries(
            [{'file_key': 'invoices/dup.pdf', 'file_md5': 'md5-dup-1', 'invoice_number': 'D1'}],
            PurchaseRecord.FILE_TYPE_INVOICE,
        ),
    )
    _sync_legacy_file_columns(record)
    db.session.commit()

    hit = InvoiceUploadService.find_invoice_by_md5('md5-dup-1')
    assert hit['duplicate'] is True
    assert hit['record_id'] == record.record_id

    # 编辑同一条记录时允许重传自己的发票
    same_record = InvoiceUploadService.find_invoice_by_md5('md5-dup-1', record.record_id)
    assert same_record['duplicate'] is False

    # 未出现过的 md5 不算重复
    assert InvoiceUploadService.find_invoice_by_md5('md5-not-exists')['duplicate'] is False
