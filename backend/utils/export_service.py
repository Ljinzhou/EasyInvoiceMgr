import os
import zipfile
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, unquote

from PyPDF2 import PdfMerger
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.drawing.image import Image as XlImage
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)

COLUMN_DEFINITIONS = {
    'item_name': {'label': '名称', 'width': 25},
    'purchase_platform': {'label': '购买平台', 'width': 18},
    'amount': {'label': '金额', 'width': 14},
    'purchase_date': {'label': '购物日期', 'width': 14},
    'invoice_date': {'label': '开票日期', 'width': 14},
    'uploader': {'label': '上传人', 'width': 12},
    'invoice_tax_number': {'label': '销售方税号', 'width': 22},
    'invoice_number': {'label': '发票号码', 'width': 22},
    'receipt_count': {'label': '凭证张数', 'width': 10},
    'invoice_count': {'label': '发票张数', 'width': 10},
    'receipt_image': {'label': '购物图片', 'width': 20},
    'invoice_image': {'label': '发票图片', 'width': 20},
}

# 需要下载文件并嵌入的图片列键
IMAGE_COLUMNS = {'receipt_image', 'invoice_image'}

# 在 Excel 中嵌入图片的目标像素尺寸
IMG_TARGET_WIDTH_PX = 160
IMG_TARGET_HEIGHT_PX = 100

# 导出产物格式版本：附件多文件、图片发票转 PDF 合并等行为变化时递增，
# check_cache 会拒绝旧版本产生的导出文件，避免命中过期结果。
EXPORT_FORMAT_VERSION = 2

# 可以直接作为图片嵌入 Excel 的扩展名
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')

# Windows / Linux 文件名非法字符
_ILLEGAL_FILENAME_CHARS = '<>:"/\\|?*'


def _sanitize_filename(name, fallback='附件', max_length=80):
    """清理成文件系统安全的文件名片段（不含扩展名）。"""
    text = (name or '').split('?')[0].strip()
    text = ''.join('_' if c in _ILLEGAL_FILENAME_CHARS or ord(c) < 32 else c for c in text)
    text = text.strip(' .')
    if len(text) > max_length:
        text = text[:max_length].rstrip(' .')
    return text or fallback


def _file_extension(file_key, original_filename='', fallback='.pdf'):
    """从文件 key 或原始文件名推断扩展名（带点、小写）。"""
    for candidate in (original_filename, file_key or ''):
        if not candidate:
            continue
        candidate = candidate.split('?')[0]
        ext = os.path.splitext(os.path.basename(candidate))[1].lower()
        if ext and len(ext) <= 6:
            return ext
    return fallback


def _unique_file_path(directory, filename):
    """同名文件自动追加序号，避免多附件导出时相互覆盖。"""
    stem, ext = os.path.splitext(filename)
    candidate = os.path.join(directory, filename)
    counter = 2
    while os.path.exists(candidate):
        candidate = os.path.join(directory, f'{stem}_{counter}{ext}')
        counter += 1
    return candidate


# 导出开关的规范键名（内部统一 snake_case + 布尔值）
_EXPORT_OPTION_KEYS = ('merged_pdf', 'individual_invoices', 'receipt_images', 'only_mine')


def normalize_export_options(options):
    """统一导出开关：前端 camelCase → 后端 snake_case，并规范成布尔值。

    导出缓存按 options 精确比较，必须保证「同一种选择」只有一种表示形式，
    否则缓存会一直未命中。
    """
    mapping = {
        'mergedPdf': 'merged_pdf',
        'individualInvoices': 'individual_invoices',
        'receiptImages': 'receipt_images',
        'onlyMine': 'only_mine',
    }
    raw = options if isinstance(options, dict) else {}
    result = {key: False for key in _EXPORT_OPTION_KEYS}
    for key, value in raw.items():
        normalized_key = mapping.get(key, key)
        if normalized_key not in result:
            continue
        if isinstance(value, str):
            value = value.strip().lower() in ('1', 'true', 'yes', 'on', '是')
        else:
            value = bool(value)
        result[normalized_key] = value
    return result


class ExportService:
    def __init__(self, app):
        self.app = app
        self.exports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'exports')
        os.makedirs(self.exports_dir, exist_ok=True)

    def run_export(self, task_id):
        with self.app.app_context():
            from models import db, ExportTask
            try:
                task = db.session.get(ExportTask, task_id)
                if not task:
                    return
                task.status = 'processing'
                task.progress_percent = 5
                task.progress_message = '正在获取数据...'
                db.session.commit()

                columns_config = task.columns_config or {}
                options = self._normalize_options(columns_config.get('options', {}))

                uploader_id = task.requester_id if options.get('only_mine') else None
                records, snapshot_time = self._fetch_data(task.event_id, uploader_id)
                task.data_snapshot_time = snapshot_time
                task.record_count = len(records)
                task.progress_percent = 15
                task.progress_message = f'已获取 {len(records)} 条记录'
                db.session.commit()

                # 校验并记录导出顺序，保证 PDF 与 Excel 一致
                logger.info(f'导出顺序验证: 共 {len(records)} 条记录, 按创建时间排序')
                for i, rec in enumerate(records):
                    logger.debug(f'  [{i}] id={rec["id"]} type={rec["type"]} '
                                 f'has_invoice={rec.get("has_invoice")} '
                                 f'created_at={rec.get("created_at")}')

                if not records:
                    task.status = 'failed'
                    task.error_message = '没有可导出的数据'
                    task.completed_at = datetime.now(timezone.utc)
                    db.session.commit()
                    return

                columns_config = task.columns_config or {}
                selected_columns = columns_config.get('columns', [])

                logger.info(f'导出配置: columns={selected_columns}, options={options}')

                import tempfile
                with tempfile.TemporaryDirectory() as temp_dir:
                    task.progress_percent = 25
                    task.progress_message = '正在生成Excel文件...'
                    db.session.commit()

                    excel_path = self._generate_excel(records, selected_columns, temp_dir, temp_dir)

                    merged_pdf_path = None
                    invoice_files = []
                    if options.get('merged_pdf') or options.get('individual_invoices'):
                        task.progress_percent = 40
                        task.progress_message = '正在处理发票文件...'
                        db.session.commit()
                        invoice_files, merged_pdf_path = self._process_invoices(records, temp_dir, options)

                    receipt_folder = None
                    if options.get('receipt_images'):
                        task.progress_percent = 70
                        task.progress_message = '正在处理购物凭证图片...'
                        db.session.commit()
                        receipt_folder = self._process_receipt_images(records, temp_dir)

                    task.progress_percent = 85
                    task.progress_message = '正在打包ZIP文件...'
                    db.session.commit()

                    from models import Event
                    event = db.session.get(Event, task.event_id)
                    event_name = event.event_name if event else 'export'
                    zip_path = self._create_zip(event_name, excel_path, merged_pdf_path,
                                                invoice_files, receipt_folder, task.task_id)

                    task.file_path = zip_path
                    task.file_size = os.path.getsize(zip_path)
                    task.status = 'completed'
                    task.progress_percent = 100
                    task.progress_message = '导出完成'
                    task.completed_at = datetime.now(timezone.utc)
                    task.expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
                    db.session.commit()
                    logger.info(f'导出完成: task_id={task_id}, file={zip_path}, size={task.file_size}')

            except Exception as e:
                logger.error(f'导出失败: task_id={task_id}, error={str(e)}', exc_info=True)
                try:
                    task.status = 'failed'
                    task.error_message = str(e)
                    task.completed_at = datetime.now(timezone.utc)
                    db.session.commit()
                except Exception:
                    pass
            finally:
                try:
                    db.session.remove()
                except Exception:
                    pass

    def _normalize_options(self, options):
        """将前端 camelCase 键转换为后端 snake_case 键（兼容旧任务）。"""
        return normalize_export_options(options)

    # ------------------------------------------------------------------
    # 附件读取：明细表优先，旧单文件列兜底
    # ------------------------------------------------------------------

    @staticmethod
    def _file_rows_to_attachments(rows):
        """把 PurchaseRecordFile 行转换成导出用的附件字典。"""
        return [
            {
                'file_key': row.file_key or '',
                'preview_key': row.preview_key or '',
                'original_filename': row.original_filename or '',
                'file_size': row.file_size,
            }
            for row in rows
            if row.file_key
        ]

    @staticmethod
    def _legacy_attachments(record):
        """没有附件明细行时，退回旧单文件列（兼容历史数据/旧库）。"""
        receipts = []
        if record.receipt_image_url:
            receipts.append({
                'file_key': record.receipt_image_url,
                'preview_key': '',
                'original_filename': record.receipt_image_name or '',
                'file_size': None,
            })

        invoices = []
        if not record.cannot_invoice and record.has_invoice and record.invoice_file_key:
            invoices.append({
                'file_key': record.invoice_file_key,
                'preview_key': record.invoice_preview_key or '',
                'original_filename': record.invoice_original_filename or '',
                'file_size': None,
            })
        return receipts, invoices

    def _fetch_data(self, event_id, uploader_id=None):
        from models import db, PurchaseRecord, PurchaseRecordFile, Invoice, User

        purchase_query = PurchaseRecord.query.filter_by(event_id=event_id, is_deleted=False)
        invoice_query = Invoice.query.filter_by(event_id=event_id, is_deleted=False)
        if uploader_id:
            purchase_query = purchase_query.filter_by(uploader_id=uploader_id)
            invoice_query = invoice_query.filter_by(uploader_id=uploader_id)

        purchase_records = purchase_query.all()
        invoices = invoice_query.all()

        # 批量取上传人，避免逐条查询（附件多文件后记录数更多，N+1 放大明显）
        user_ids = {r.uploader_id for r in purchase_records} | {i.uploader_id for i in invoices}
        users = {}
        if user_ids:
            users = {
                user.user_id: user
                for user in User.query.filter(User.user_id.in_(user_ids)).all()
            }

        # 一次取出全部附件明细，按 记录 → 类型 → 顺序 归组
        attachment_rows = {}
        record_ids = [record.record_id for record in purchase_records]
        if record_ids:
            rows = (
                PurchaseRecordFile.query
                .filter(PurchaseRecordFile.record_id.in_(record_ids))
                .order_by(
                    PurchaseRecordFile.record_id,
                    PurchaseRecordFile.sort_order,
                    PurchaseRecordFile.file_id,
                )
                .all()
            )
            for row in rows:
                attachment_rows.setdefault(row.record_id, []).append(row)

        logger.info(
            f'获取数据: event_id={event_id}, purchase_records={len(purchase_records)}, '
            f'invoices={len(invoices)}, attachment_rows={sum(len(v) for v in attachment_rows.values())}'
        )

        all_records = []
        max_updated = None

        for record in purchase_records:
            uploader = users.get(record.uploader_id)
            updated = record.updated_at or record.created_at
            if max_updated is None or (updated and updated > max_updated):
                max_updated = updated

            rows = attachment_rows.get(record.record_id, [])
            receipt_files = self._file_rows_to_attachments(
                [row for row in rows if row.file_type == PurchaseRecord.FILE_TYPE_RECEIPT]
            )
            invoice_files = self._file_rows_to_attachments(
                [row for row in rows if row.file_type == PurchaseRecord.FILE_TYPE_INVOICE]
            )

            legacy_receipts, legacy_invoices = self._legacy_attachments(record)
            if not receipt_files:
                receipt_files = legacy_receipts
            if not invoice_files:
                invoice_files = legacy_invoices

            primary_receipt = receipt_files[0] if receipt_files else {}
            primary_invoice = invoice_files[0] if invoice_files else {}

            rec = {
                'type': 'purchase',
                'id': f'P{record.record_id}',
                'item_name': record.item_name or '',
                'purchase_platform': record.purchase_platform or '',
                'amount': float(record.amount) if record.amount else 0,
                'purchase_date': record.purchase_date.strftime('%Y-%m-%d') if record.purchase_date else '',
                'invoice_date': record.invoice_date.strftime('%Y-%m-%d') if record.invoice_date else '',
                'uploader_name': uploader.real_name if uploader else '未知',
                'invoice_tax_number': record.invoice_tax_number or '',
                'invoice_number': record.invoice_number or '',
                'has_invoice': bool(invoice_files),
                'receipt_files': receipt_files,
                'invoice_files': invoice_files,
                'receipt_count': len(receipt_files),
                'invoice_count': len(invoice_files),
                # 兼容字段：仍指向「第一个文件」，供图片列/旧逻辑使用
                'invoice_file_key': primary_invoice.get('file_key', ''),
                'invoice_preview_key': primary_invoice.get('preview_key', ''),
                'invoice_original_filename': primary_invoice.get('original_filename', ''),
                'receipt_image_url': primary_receipt.get('file_key', ''),
                'receipt_image_name': primary_receipt.get('original_filename', ''),
                'created_at': record.created_at.strftime('%Y-%m-%d %H:%M:%S') if record.created_at else '',
                'raw_created_at': record.created_at,
            }
            all_records.append(rec)
            logger.debug(
                f'  购买记录 {rec["id"]}: 凭证={rec["receipt_count"]} 张, '
                f'发票={rec["invoice_count"]} 张, has_invoice={rec["has_invoice"]}'
            )

        for invoice in invoices:
            uploader = users.get(invoice.uploader_id)
            updated = invoice.updated_at or invoice.created_at
            if max_updated is None or (updated and updated > max_updated):
                max_updated = updated

            invoice_files = []
            if invoice.image_url:
                invoice_files.append({
                    'file_key': invoice.image_url,
                    'preview_key': invoice.preview_image_url or '',
                    'original_filename': invoice.file_name or '',
                    'file_size': None,
                })

            rec = {
                'type': 'invoice',
                'id': f'I{invoice.invoice_id}',
                'item_name': invoice.project_name or '',
                'purchase_platform': '发票上传',
                'amount': float(invoice.amount) if invoice.amount else 0,
                'purchase_date': invoice.invoice_date.strftime('%Y-%m-%d') if invoice.invoice_date else '',
                'invoice_date': invoice.invoice_date.strftime('%Y-%m-%d') if invoice.invoice_date else '',
                'uploader_name': uploader.real_name if uploader else '未知',
                'invoice_tax_number': '',  # Invoice 模型没有 tax_number 字段
                'invoice_number': invoice.invoice_number or '',
                'has_invoice': bool(invoice_files),
                'receipt_files': [],
                'invoice_files': invoice_files,
                'receipt_count': 0,
                'invoice_count': len(invoice_files),
                'invoice_file_key': invoice_files[0]['file_key'] if invoice_files else '',
                'invoice_preview_key': invoice_files[0]['preview_key'] if invoice_files else '',
                'invoice_original_filename': invoice_files[0]['original_filename'] if invoice_files else '',
                'receipt_image_url': '',
                'receipt_image_name': '',
                'created_at': invoice.created_at.strftime('%Y-%m-%d %H:%M:%S') if invoice.created_at else '',
                'raw_created_at': invoice.created_at,
            }
            all_records.append(rec)
            logger.debug(f'  发票记录 {rec["id"]}: 发票={rec["invoice_count"]} 张')

        all_records.sort(key=lambda x: x.get('raw_created_at') or datetime.min.replace(tzinfo=timezone.utc))
        return all_records, max_updated

    def _generate_excel(self, records, selected_columns, output_dir, temp_dir):
        wb = Workbook()
        ws = wb.active
        ws.title = '购物记录'

        header_fill = PatternFill(start_color='667eea', end_color='667eea', fill_type='solid')
        header_font = Font(name='微软雅黑', size=11, bold=True, color='FFFFFF')
        header_alignment = Alignment(horizontal='center', vertical='center')
        thin_border = Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'), bottom=Side(style='thin')
        )

        if not selected_columns:
            raise ValueError('selected_columns is empty')

        has_image_cols = any(c in IMAGE_COLUMNS for c in selected_columns)
        logger.info(f'生成Excel: 列={selected_columns}, 含图片列={has_image_cols}')

        # 写入表头
        for col_idx, col_key in enumerate(selected_columns, 1):
            cell = ws.cell(row=1, column=col_idx, value=COLUMN_DEFINITIONS[col_key]['label'])
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment
            cell.border = thin_border
            col_letter = get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = COLUMN_DEFINITIONS[col_key]['width']

        # 图片列需要更宽的列宽以容纳嵌入的图片
        for col_idx, col_key in enumerate(selected_columns, 1):
            if col_key in IMAGE_COLUMNS:
                col_letter = get_column_letter(col_idx)
                ws.column_dimensions[col_letter].width = (IMG_TARGET_WIDTH_PX / 7) + 2

        # 写入数据行
        data_font = Font(name='微软雅黑', size=10)
        img_fallback_font = Font(name='微软雅黑', size=8, color='999999')
        cell_alignment = Alignment(vertical='center', wrap_text=True)
        img_success_count = 0
        img_fail_count = 0

        for row_idx, record in enumerate(records, 2):
            # 判断该行是否包含嵌入图片，以确定行高
            row_has_image = False
            for col_key in selected_columns:
                if col_key in IMAGE_COLUMNS:
                    fk = self._get_image_file_key(record, col_key)
                    if fk:
                        row_has_image = True
                        break

            if row_has_image:
                ws.row_dimensions[row_idx].height = IMG_TARGET_HEIGHT_PX * 0.8
            else:
                ws.row_dimensions[row_idx].height = 22

            for col_idx, col_key in enumerate(selected_columns, 1):
                if col_key in IMAGE_COLUMNS:
                    files = self._get_image_files(record, col_key)
                    file_count = len(files)

                    # invoice_image 列的 has_invoice 保护判断
                    if col_key == 'invoice_image' and not record.get('has_invoice', False):
                        cell = ws.cell(row=row_idx, column=col_idx, value='无发票信息')
                        cell.font = data_font
                        cell.alignment = cell_alignment
                        cell.border = thin_border
                        continue

                    file_key = self._get_image_file_key(record, col_key)
                    if not file_key:
                        label = '无发票信息' if col_key == 'invoice_image' else '无'
                        cell = ws.cell(row=row_idx, column=col_idx, value=label)
                        cell.font = data_font
                        cell.alignment = cell_alignment
                        cell.border = thin_border
                        if col_key == 'invoice_image':
                            img_fail_count += 1
                        continue

                    img_path = self._download_and_save_image(file_key, temp_dir, record, col_key)
                    if img_path and os.path.exists(img_path):
                        try:
                            img = self._fit_xl_image(img_path)
                            cell_ref = f'{get_column_letter(col_idx)}{row_idx}'
                            ws.add_image(img, cell_ref)
                            placeholder = '[图片]' if file_count <= 1 else f'[图片 1/{file_count}]'
                            cell = ws.cell(row=row_idx, column=col_idx, value=placeholder)
                            cell.font = img_fallback_font
                            cell.alignment = cell_alignment
                            cell.border = thin_border
                            img_success_count += 1
                        except Exception as e:
                            logger.warning(f'插入图片失败: record={record.get("id")}, col={col_key}, path={img_path}, error={str(e)}')
                            cell = ws.cell(row=row_idx, column=col_idx, value='图片加载失败')
                            cell.font = data_font
                            cell.alignment = cell_alignment
                            cell.border = thin_border
                            img_fail_count += 1
                    else:
                        logger.debug(f'图片下载失败: record={record.get("id")}, col={col_key}, key={file_key[:60] if file_key else "空"}')
                        cell = ws.cell(row=row_idx, column=col_idx, value='资源未找到')
                        cell.font = data_font
                        cell.alignment = cell_alignment
                        cell.border = thin_border
                        img_fail_count += 1
                else:
                    value = self._get_column_value(record, col_key)
                    cell = ws.cell(row=row_idx, column=col_idx, value=value)
                    cell.font = data_font
                    cell.border = thin_border
                    if col_key == 'amount':
                        cell.number_format = '#,##0.00'
                        cell.alignment = Alignment(horizontal='right', vertical='center')
                    else:
                        cell.alignment = cell_alignment

        logger.info(f'Excel图片统计: 成功={img_success_count}, 失败={img_fail_count}')
        self._write_attachment_sheet(wb, records, header_fill, header_font, header_alignment, thin_border, data_font, cell_alignment)
        excel_path = os.path.join(output_dir, '购物信息.xlsx')
        wb.save(excel_path)
        return excel_path

    @staticmethod
    def _fit_xl_image(img_path):
        """按目标像素框等比缩放图片，避免凭证/发票被拉伸变形。"""
        img = XlImage(img_path)
        try:
            origin_width, origin_height = img.width, img.height
        except Exception:
            origin_width, origin_height = None, None

        if not origin_width or not origin_height:
            img.width = IMG_TARGET_WIDTH_PX
            img.height = IMG_TARGET_HEIGHT_PX
            return img

        scale = min(
            IMG_TARGET_WIDTH_PX / float(origin_width),
            IMG_TARGET_HEIGHT_PX / float(origin_height),
        )
        img.width = max(1, int(origin_width * scale))
        img.height = max(1, int(origin_height * scale))
        return img

    @staticmethod
    def _write_attachment_sheet(wb, records, header_fill, header_font, header_alignment,
                                thin_border, data_font, cell_alignment):
        """把每条记录的全部附件列成「附件清单」工作表，多文件时便于核对。"""
        rows = []
        for record in records:
            for file_type, label, files in (
                ('receipt', '购物凭证', record.get('receipt_files') or []),
                ('invoice', '发票', record.get('invoice_files') or []),
            ):
                for index, attachment in enumerate(files, 1):
                    rows.append((
                        record.get('id', ''),
                        record.get('item_name', ''),
                        label,
                        index,
                        attachment.get('original_filename') or os.path.basename(
                            (attachment.get('file_key') or '').split('?')[0]
                        ),
                        attachment.get('file_key', ''),
                    ))

        if not rows:
            return

        ws = wb.create_sheet(title='附件清单')
        headers = ['记录编号', '记录名称', '附件类型', '序号', '文件名', '存储键']
        widths = [12, 25, 12, 8, 40, 60]
        for col_idx, (header, width) in enumerate(zip(headers, widths), 1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment
            cell.border = thin_border
            ws.column_dimensions[get_column_letter(col_idx)].width = width

        for row_idx, row_values in enumerate(rows, 2):
            for col_idx, value in enumerate(row_values, 1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.font = data_font
                cell.border = thin_border
                cell.alignment = cell_alignment

        ws.freeze_panes = 'A2'
        logger.info(f'附件清单: 共 {len(rows)} 个附件文件')

    @staticmethod
    def _get_image_files(record, col_key):
        """图片列对应的附件列表（多文件全部返回）。"""
        if col_key == 'receipt_image':
            return record.get('receipt_files') or []
        if col_key == 'invoice_image':
            return record.get('invoice_files') or []
        return []

    def _get_image_file_key(self, record, col_key):
        """获取图片列嵌入 Excel 时使用的第一个文件 key。"""
        files = self._get_image_files(record, col_key)
        if not files:
            return ''
        if col_key == 'invoice_image':
            # 嵌入 Excel 时优先使用预览 JPG，而非原始 PDF
            primary = files[0]
            return primary.get('preview_key') or primary.get('file_key') or ''
        return files[0].get('file_key') or ''

    def _download_and_save_image(self, file_key, temp_dir, record, col_key):
        """下载图片文件并保存到临时目录，返回本地路径。"""
        if not file_key:
            return None

        # 确定文件名与扩展名
        files = self._get_image_files(record, col_key)
        original_name = ''
        if files:
            original_name = files[0].get('original_filename') or ''
        if col_key == 'receipt_image':
            prefix = 'receipt'
        else:
            original_name = original_name or record.get('file_name', '')
            prefix = 'invoice'

        # 优先从 file_key（实际文件）取扩展名，其次从原始文件名取，最后用默认值
        ext = ''
        if file_key:
            ext = os.path.splitext(file_key.split('?')[0])[1].lower()
        if not ext and original_name:
            ext = os.path.splitext(original_name)[1].lower()
        if not ext:
            ext = '.jpg'  # 默认值

        record_id = record.get('id', 'unknown')
        safe_filename = f'{prefix}_{record_id}{ext}'
        local_path = os.path.join(temp_dir, 'img_temp', safe_filename)

        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        # 下载文件字节
        file_bytes = self._download_file(file_key)
        if not file_bytes:
            return None

        logger.info(f'图片下载成功: record={record_id}, col={col_key}, size={len(file_bytes)} bytes')

        with open(local_path, 'wb') as f:
            f.write(file_bytes)

        # 对于 PDF 文件，将首页转换为图片
        if ext == '.pdf':
            try:
                import fitz  # PyMuPDF
                pdf_doc = fitz.open(local_path)
                if pdf_doc.page_count > 0:
                    page = pdf_doc[0]
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    img_path = local_path.replace('.pdf', '.png')
                    pix.save(img_path)
                    pdf_doc.close()
                    logger.info(f'PDF转图片成功: {img_path}')
                    return img_path
                pdf_doc.close()
            except Exception as e:
                logger.warning(f'PDF转图片失败: {local_path}, error={str(e)}')
                return None

        # 非图片文件则跳过
        if ext not in IMAGE_EXTENSIONS:
            logger.warning(f'不支持的图片格式: ext={ext}, record={record.get("id")}, file_key={file_key[:80]}')
            return None

        return local_path

    def _get_column_value(self, record, col_key):
        if col_key == 'item_name':
            return record.get('item_name', '')
        elif col_key == 'purchase_platform':
            return record.get('purchase_platform', '')
        elif col_key == 'amount':
            return record.get('amount', 0)
        elif col_key == 'purchase_date':
            return record.get('purchase_date', '')
        elif col_key == 'invoice_date':
            return record.get('invoice_date', '')
        elif col_key == 'uploader':
            return record.get('uploader_name', '')
        elif col_key == 'invoice_tax_number':
            if not record.get('has_invoice', False):
                return '无发票信息'
            tax = record.get('invoice_tax_number', '') or record.get('invoice_number', '')
            return tax if tax else '无'
        elif col_key == 'invoice_number':
            if not record.get('has_invoice', False):
                return '无发票信息'
            return record.get('invoice_number', '') or '无'
        elif col_key == 'receipt_count':
            return record.get('receipt_count', 0)
        elif col_key == 'invoice_count':
            return record.get('invoice_count', 0)
        return ''

    def _extract_cos_key(self, file_key):
        """从各种格式（预签名 URL、完整 URL 或原始 key）中提取纯 COS key。"""
        if not file_key:
            return None

        # 若看起来像 URL，则解析并提取路径
        if file_key.startswith('http://') or file_key.startswith('https://'):
            try:
                parsed = urlparse(file_key)
                # 路径形如 /invoices/xxx/file.jpg —— 去掉开头的 /
                path = unquote(parsed.path).lstrip('/')
                if path:
                    return path
            except Exception:
                pass
            return None

        # 已经是纯 COS key 或本地路径
        return file_key

    def _download_file(self, file_key):
        """根据 key 下载文件，支持预签名 URL、COS key 和本地路径。"""
        if not file_key:
            return None

        logger.debug(f'尝试下载文件: {file_key[:80]}')

        # 策略 1：优先检查本地 uploads 目录（最快）
        uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')

        # 处理 /uploads/xxx 本地路径
        if file_key.startswith('/uploads/'):
            local_path = os.path.join(uploads_dir, file_key.replace('/uploads/', ''))
            if os.path.exists(local_path):
                logger.debug(f'从本地读取: {local_path}')
                with open(local_path, 'rb') as f:
                    return f.read()
            logger.warning(f'本地文件不存在: {local_path}')
            return None

        # 策略 2：若是完整 URL，则直接通过 HTTP 下载
        if file_key.startswith('http://') or file_key.startswith('https://'):
            try:
                import requests as requests_lib
                resp = requests_lib.get(file_key, timeout=30)
                resp.raise_for_status()
                logger.debug(f'从URL下载成功: {len(resp.content)} bytes')
                return resp.content
            except Exception as e:
                logger.warning(f'从URL下载失败: {file_key[:80]}, error={str(e)}')
            return None

        # 策略 3：使用存储后端（本地或 COS）
        try:
            from utils.storage import storage_manager
            if storage_manager.is_available():
                content = storage_manager.download_file(file_key)
                if content:
                    logger.debug(f'存储下载成功: {len(content)} bytes')
                    return content
        except Exception as e:
            logger.warning(f'存储下载失败: {file_key}, error={str(e)}')

        # 策略 4：尝试作为 uploads 目录下的相对路径
        local_path = os.path.join(uploads_dir, file_key)
        if os.path.exists(local_path):
            logger.debug(f'从本地相对路径读取: {local_path}')
            with open(local_path, 'rb') as f:
                return f.read()

        logger.warning(f'文件下载失败(所有方式): {file_key[:80]}')
        return None

    def _process_invoices(self, records, temp_dir, options):
        """导出全部发票附件（购买记录的多个发票 + 独立发票上传记录）。"""
        invoice_files = []
        invoices_dir = os.path.join(temp_dir, '发票单独')
        os.makedirs(invoices_dir, exist_ok=True)

        download_count = 0
        skip_count = 0
        sequence = 0

        for record in records:
            tax_number = _sanitize_filename(record.get('invoice_tax_number', ''), fallback='')
            for file_index, attachment in enumerate(record.get('invoice_files') or [], 1):
                file_key = attachment.get('file_key')
                if not file_key:
                    skip_count += 1
                    continue

                file_bytes = self._download_file(file_key)
                if not file_bytes:
                    skip_count += 1
                    continue

                sequence += 1
                download_count += 1
                original = attachment.get('original_filename', '')
                ext = _file_extension(file_key, original, fallback='.pdf')
                base = _sanitize_filename(
                    os.path.splitext(original.split('?')[0])[0] if original else '',
                    fallback=f'发票{file_index}',
                )
                parts = [f'{sequence:03d}', record.get('id', '')]
                if tax_number:
                    parts.append(tax_number)
                parts.append(base)
                filename = '_'.join(part for part in parts if part) + ext

                filepath = _unique_file_path(invoices_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(file_bytes)
                invoice_files.append(filepath)

        logger.info(f'发票处理: 下载={download_count}, 跳过={skip_count}, 总文件={len(invoice_files)}')

        merged_pdf_path = None
        if options.get('merged_pdf') and invoice_files:
            merged_pdf_path = self._merge_invoice_files(invoice_files, temp_dir)

        return invoice_files, merged_pdf_path

    def _merge_invoice_files(self, invoice_paths, temp_dir):
        """按导出顺序把全部发票合并成一个 PDF；图片型发票先转成 PDF。"""
        merger = PdfMerger()
        merged_count = 0
        for pdf_file in invoice_paths:
            try:
                source_path = pdf_file
                if os.path.splitext(pdf_file)[1].lower() != '.pdf':
                    source_path = self._convert_image_to_pdf(pdf_file, temp_dir)
                if not source_path:
                    continue
                merger.append(source_path)
                merged_count += 1
            except Exception as e:
                logger.warning(f'合并PDF失败: {pdf_file}, error={str(e)}')

        if merged_count == 0:
            merger.close()
            logger.warning('PDF合并失败: 所有文件都无法合并，已跳过生成合并PDF')
            return None

        merged_pdf_path = os.path.join(temp_dir, '发票汇总.pdf')
        merger.write(merged_pdf_path)
        merger.close()
        logger.info(f'PDF合并成功: {merged_count}/{len(invoice_paths)} 个文件')
        return merged_pdf_path

    @staticmethod
    def _convert_image_to_pdf(image_path, temp_dir):
        """把图片发票转成单页 PDF，供汇总 PDF 使用。"""
        try:
            import fitz  # PyMuPDF

            pix = fitz.Pixmap(image_path)
            width, height = pix.width, pix.height
            pix = None

            doc = fitz.open()
            page = doc.new_page(width=width, height=height)
            page.insert_image(page.rect, filename=image_path)
            pdf_path = os.path.join(temp_dir, '图片转PDF', os.path.basename(image_path) + '.pdf')
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            doc.save(pdf_path)
            doc.close()
            return pdf_path
        except Exception as e:
            logger.warning(f'图片转PDF失败: {image_path}, error={str(e)}')
            return None

    def _process_receipt_images(self, records, temp_dir):
        """导出全部购物凭证文件（多文件全部导出）。"""
        receipt_dir = os.path.join(temp_dir, '购物凭证')
        os.makedirs(receipt_dir, exist_ok=True)

        download_count = 0
        skip_count = 0
        sequence = 0

        for record in records:
            item_name = _sanitize_filename(record.get('item_name', ''), fallback='购物凭证')
            for file_index, attachment in enumerate(record.get('receipt_files') or [], 1):
                file_key = attachment.get('file_key')
                if not file_key:
                    skip_count += 1
                    continue

                file_bytes = self._download_file(file_key)
                if not file_bytes:
                    skip_count += 1
                    continue

                sequence += 1
                download_count += 1
                original = attachment.get('original_filename', '')
                ext = _file_extension(file_key, original, fallback='.jpg')
                filename = f'{sequence:03d}_{record.get("id", "")}_{item_name}_{file_index}{ext}'

                filepath = _unique_file_path(receipt_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(file_bytes)

        logger.info(f'购物凭证处理: 下载={download_count}, 跳过={skip_count}, 总文件={download_count}')
        return receipt_dir

    def _create_zip(self, event_name, excel_path, merged_pdf_path, invoice_files, receipt_folder, task_id):
        safe_name = "".join(c for c in event_name if c.isalnum() or c in (' ', '-', '_')).strip()
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        zip_filename = f'{safe_name}_{task_id}_{timestamp}.zip'
        zip_path = os.path.join(self.exports_dir, zip_filename)

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            if excel_path and os.path.exists(excel_path):
                zf.write(excel_path, os.path.basename(excel_path))
                logger.info(f'  ZIP: 添加Excel ({os.path.getsize(excel_path)} bytes)')

            if merged_pdf_path and os.path.exists(merged_pdf_path):
                zf.write(merged_pdf_path, '发票汇总.pdf')
                logger.info(f'  ZIP: 添加发票汇总 ({os.path.getsize(merged_pdf_path)} bytes)')

            for pdf_file in invoice_files:
                if os.path.exists(pdf_file):
                    zf.write(pdf_file, f'发票单独/{os.path.basename(pdf_file)}')
            logger.info(f'  ZIP: 添加 {len(invoice_files)} 个单独发票文件')

            if receipt_folder and os.path.exists(receipt_folder):
                receipt_count = 0
                for root, dirs, files in os.walk(receipt_folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, receipt_folder)
                        zf.write(file_path, f'购物凭证/{arcname}')
                        receipt_count += 1
                logger.info(f'  ZIP: 添加 {receipt_count} 个购物凭证文件')
            else:
                logger.info(f'  ZIP: 无购物凭证文件夹 (receipt_folder={receipt_folder})')

        return zip_path

    def check_cache(self, event_id, columns_config):
        from models import db, ExportTask, PurchaseRecord, Invoice

        self._cleanup_expired()

        columns_hash = str(sorted(columns_config.get('columns', [])))
        options = normalize_export_options(columns_config.get('options', {}))

        recent_task = ExportTask.query.filter_by(
            event_id=event_id,
            status='completed'
        ).order_by(ExportTask.created_at.desc()).first()

        if not recent_task:
            return None

        if not recent_task.file_path or not os.path.exists(recent_task.file_path):
            return None

        if recent_task.expires_at and recent_task.expires_at < datetime.now(timezone.utc):
            return None

        stored_config = recent_task.columns_config or {}
        # 导出产物格式升级（附件多文件、图片发票转 PDF 合并等）后，旧任务全部作废
        if stored_config.get('format_version') != EXPORT_FORMAT_VERSION:
            return None
        if str(sorted(stored_config.get('columns', []))) != columns_hash:
            return None
        if normalize_export_options(stored_config.get('options', {})) != options:
            return None

        max_updated = db.session.query(
            db.func.max(PurchaseRecord.updated_at)
        ).filter_by(event_id=event_id, is_deleted=False).scalar()

        max_updated_inv = db.session.query(
            db.func.max(Invoice.updated_at)
        ).filter_by(event_id=event_id, is_deleted=False).scalar()

        latest_update = max(
            x for x in [max_updated, max_updated_inv, recent_task.data_snapshot_time]
            if x is not None
        ) if any(x is not None for x in [max_updated, max_updated_inv, recent_task.data_snapshot_time]) else None

        if latest_update and recent_task.data_snapshot_time and latest_update > recent_task.data_snapshot_time:
            return None

        return recent_task

    def _cleanup_expired(self):
        from models import db, ExportTask

        expired_tasks = ExportTask.query.filter(
            ExportTask.expires_at < datetime.now(timezone.utc),
            ExportTask.status == 'completed'
        ).all()

        for task in expired_tasks:
            if task.file_path and os.path.exists(task.file_path):
                try:
                    os.remove(task.file_path)
                    logger.info(f'已清理过期导出文件: {task.file_path}')
                except Exception as e:
                    logger.warning(f'清理文件失败: {task.file_path}, error={str(e)}')

            db.session.delete(task)

        db.session.commit()
