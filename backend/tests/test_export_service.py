"""导出服务测试：多文件附件、导出选项归一化、打包与缓存版本。

重点覆盖「购买记录改为多附件」后的回归风险：
- 一条记录的全部购物凭证/发票都要导出，而不是只导第一份；
- Excel 除主表外必须有「附件清单」工作表；
- check_cache 必须拒绝旧格式版本产生的导出结果。
"""
import os
import sys
from datetime import date, datetime, timedelta, timezone

import pytest
from PyPDF2 import PdfReader, PdfWriter

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from utils.export_service import (  # noqa: E402
    EXPORT_FORMAT_VERSION,
    ExportService,
    normalize_export_options,
)

FAKE_JPG_BYTES = b'\xff\xd8\xff\xe0fake-jpeg'
FAKE_PNG_BYTES = b'\x89PNG\r\n\x1a\nfake-png'


def _make_pdf(path, pages=1):
    """生成一个空白 PDF，供合并测试使用。"""
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    with open(path, 'wb') as fh:
        writer.write(fh)
    return str(path)


class InMemoryExportService(ExportService):
    """不访问 COS/本地文件，_download_file 直接返回内存数据。"""

    def __init__(self, payloads):
        self.payloads = payloads

    def _download_file(self, file_key):
        return self.payloads.get(file_key)


def _multi_file_record():
    return {
        'type': 'purchase',
        'id': 'P1',
        'item_name': '电阻',
        'purchase_platform': '淘宝',
        'amount': 10.0,
        'purchase_date': '2026-10-01',
        'invoice_date': '',
        'uploader_name': '测试',
        'invoice_tax_number': '',
        'invoice_number': '',
        'has_invoice': True,
        'receipt_files': [
            {'file_key': 'uploads/receipt-1.jpg', 'original_filename': '凭证1.jpg'},
            {'file_key': 'uploads/receipt-2.jpg', 'original_filename': '凭证2.jpg'},
        ],
        'invoice_files': [
            {'file_key': 'invoices/inv-1.pdf', 'original_filename': '发票1.pdf'},
            {'file_key': 'invoices/inv-2.png', 'original_filename': '发票2.png'},
        ],
        'receipt_count': 2,
        'invoice_count': 2,
    }


# ---------------------------------------------------------------------------
# 导出选项归一化
# ---------------------------------------------------------------------------

def test_normalize_options_maps_camel_case_and_bool():
    normalized = normalize_export_options({
        'mergedPdf': True,
        'individualInvoices': 'false',
        'receiptImages': 1,
        'onlyMine': 'true',
        'unknownKey': True,
    })

    assert normalized == {
        'merged_pdf': True,
        'individual_invoices': False,
        'receipt_images': True,
        'only_mine': True,
    }


def test_normalize_options_handles_empty_and_non_dict():
    empty = {key: False for key in (
        'merged_pdf', 'individual_invoices', 'receipt_images', 'only_mine')}
    assert normalize_export_options(None) == empty
    assert normalize_export_options({}) == empty


# ---------------------------------------------------------------------------
# 取数：附件明细表的多文件要完整带出
# ---------------------------------------------------------------------------

def test_fetch_data_reads_all_attachments(app):
    from models import db, PurchaseRecord, PurchaseRecordFile

    record = PurchaseRecord(
        event_id=1,
        uploader_id=1,
        item_name='电阻',
        purchase_platform='淘宝',
        purchase_date=date(2026, 10, 1),
        amount=10,
        receipt_image_url='uploads/legacy-receipt.jpg',
    )
    db.session.add(record)
    db.session.flush()
    db.session.add_all([
        PurchaseRecordFile(record_id=record.record_id, file_type='receipt',
                           file_key='uploads/receipt-1.jpg', sort_order=0),
        PurchaseRecordFile(record_id=record.record_id, file_type='receipt',
                           file_key='uploads/receipt-2.jpg', sort_order=1),
        PurchaseRecordFile(record_id=record.record_id, file_type='invoice',
                           file_key='invoices/inv-1.pdf', sort_order=0),
        PurchaseRecordFile(record_id=record.record_id, file_type='invoice',
                           file_key='invoices/inv-2.pdf', sort_order=1),
    ])
    db.session.commit()

    records, _ = ExportService(app)._fetch_data(1)

    purchase = next(item for item in records if item['type'] == 'purchase')
    assert purchase['receipt_count'] == 2
    assert purchase['invoice_count'] == 2
    assert purchase['receipt_files'][1]['file_key'] == 'uploads/receipt-2.jpg'
    assert purchase['has_invoice'] is True
    # 兼容字段仍指向第一个文件
    assert purchase['invoice_file_key'] == 'invoices/inv-1.pdf'


def test_fetch_data_falls_back_to_legacy_single_file(app):
    from models import db, PurchaseRecord

    db.session.add(PurchaseRecord(
        event_id=1,
        uploader_id=1,
        item_name='旧记录',
        purchase_platform='京东',
        purchase_date=date(2026, 10, 1),
        amount=20,
        receipt_image_url='uploads/legacy-receipt.jpg',
        has_invoice=True,
        invoice_file_key='invoices/legacy.pdf',
    ))
    db.session.commit()

    records, _ = ExportService(app)._fetch_data(1)

    purchase = next(item for item in records if item['type'] == 'purchase')
    assert purchase['receipt_count'] == 1
    assert purchase['invoice_count'] == 1
    assert purchase['invoice_files'][0]['file_key'] == 'invoices/legacy.pdf'


# ---------------------------------------------------------------------------
# Excel：多文件附件只嵌入第一张，并生成附件清单工作表
# ---------------------------------------------------------------------------

def test_generate_excel_adds_attachment_sheet(tmp_path):
    service = ExportService(app=None)
    records = [_multi_file_record()]

    excel_path = service._generate_excel(
        records,
        ['item_name', 'receipt_count', 'invoice_count'],
        str(tmp_path),
        str(tmp_path),
    )

    from openpyxl import load_workbook

    workbook = load_workbook(excel_path)
    assert workbook.sheetnames == ['购物记录', '附件清单']

    sheet = workbook['附件清单']
    rows = list(sheet.iter_rows(min_row=2, values_only=True))
    # 2 张凭证 + 2 张发票 = 4 行附件清单
    assert len(rows) == 4
    assert [row[2] for row in rows] == ['购物凭证', '购物凭证', '发票', '发票']
    assert [row[3] for row in rows] == [1, 2, 1, 2]


def test_generate_excel_marks_multi_file_image_cell(tmp_path):
    """多文件时图片列只嵌第一张，并在单元格标注 [图片 1/N]。"""
    from PIL import Image

    image_path = tmp_path / 'receipt.jpg'
    Image.new('RGB', (40, 30), (200, 200, 200)).save(image_path)
    image_bytes = image_path.read_bytes()

    service = InMemoryExportService({'uploads/receipt-1.jpg': image_bytes})
    records = [_multi_file_record()]

    excel_path = service._generate_excel(
        records,
        ['item_name', 'receipt_image'],
        str(tmp_path),
        str(tmp_path),
    )

    from openpyxl import load_workbook

    cell_value = load_workbook(excel_path)['购物记录']['B2'].value
    assert cell_value == '[图片 1/2]'


# ---------------------------------------------------------------------------
# 多文件导出：单独的发票/凭证文件全部落盘
# ---------------------------------------------------------------------------

def test_process_invoices_exports_every_invoice_file(tmp_path):
    pdf_bytes = open(_make_pdf(tmp_path / 'source.pdf'), 'rb').read()
    service = InMemoryExportService({
        'invoices/inv-1.pdf': pdf_bytes,
        'invoices/inv-2.png': FAKE_PNG_BYTES,
    })
    records = [_multi_file_record()]

    invoice_files, merged_pdf = service._process_invoices(
        records, str(tmp_path), {'merged_pdf': False, 'individual_invoices': True}
    )

    assert len(invoice_files) == 2
    assert merged_pdf is None
    names = sorted(os.path.basename(path) for path in invoice_files)
    assert names[0].endswith('.pdf')
    assert names[1].endswith('.png')
    # 文件名保留记录编号与序号，避免多条记录同名覆盖
    assert all(name.startswith('00') for name in names)


def test_process_receipts_exports_every_receipt_file(tmp_path):
    service = InMemoryExportService({
        'uploads/receipt-1.jpg': FAKE_JPG_BYTES,
        'uploads/receipt-2.jpg': FAKE_JPG_BYTES,
    })
    records = [_multi_file_record()]

    receipt_dir = service._process_receipt_images(records, str(tmp_path))

    files = os.listdir(receipt_dir)
    assert len(files) == 2
    assert all(name.endswith('.jpg') for name in files)


def test_merge_invoice_files_merges_real_pdfs(tmp_path):
    first = _make_pdf(tmp_path / 'a.pdf', pages=2)
    second = _make_pdf(tmp_path / 'b.pdf', pages=1)
    service = ExportService(app=None)

    merged_path = service._merge_invoice_files([first, second], str(tmp_path))

    assert merged_path and os.path.exists(merged_path)
    assert len(PdfReader(merged_path).pages) == 3


def test_merge_invoice_files_returns_none_when_nothing_mergeable(tmp_path):
    service = ExportService(app=None)
    broken = tmp_path / 'broken.pdf'
    broken.write_bytes(b'not-a-pdf')

    assert service._merge_invoice_files([str(broken)], str(tmp_path)) is None


# ---------------------------------------------------------------------------
# 导出缓存：格式版本升级后旧结果必须失效
# ---------------------------------------------------------------------------

def _create_completed_task(app, tmp_path, format_version):
    from models import db, ExportTask

    zip_path = tmp_path / f'export-v{format_version}.zip'
    zip_path.write_bytes(b'PK\x03\x04-fake-zip')

    now = datetime.now(timezone.utc)
    task = ExportTask(
        event_id=1,
        requester_id=1,
        status='completed',
        columns_config={
            'columns': ['item_name'],
            'options': normalize_export_options({}),
            'format_version': format_version,
        },
        file_path=str(zip_path),
        data_snapshot_time=now,
        record_count=1,
        expires_at=now + timedelta(minutes=30),
    )
    db.session.add(task)
    db.session.commit()
    return task


def test_check_cache_rejects_old_format_version(app, tmp_path):
    _create_completed_task(app, tmp_path, format_version=EXPORT_FORMAT_VERSION - 1)
    service = ExportService(app)

    assert service.check_cache(1, {'columns': ['item_name'], 'options': {}}) is None


def test_check_cache_hits_current_format_version(app, tmp_path):
    task = _create_completed_task(app, tmp_path, format_version=EXPORT_FORMAT_VERSION)
    service = ExportService(app)

    cached = service.check_cache(1, {'columns': ['item_name'], 'options': {}})

    assert cached is not None
    assert cached.task_id == task.task_id
