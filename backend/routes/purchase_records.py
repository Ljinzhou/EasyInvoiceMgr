from flask import Blueprint, request, jsonify, Response, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, PurchaseRecord, PurchaseRecordFile, Event, User, EventMember
from datetime import datetime, timezone
from utils.storage import storage_manager
from utils.invoice_parser import invoice_parser
from utils.glm_vision_service import glm_vision_service
from utils.permissions import ensure_event_membership, check_student_event_access
from utils.pdf_converter import PDFConverter
import logging
import os
from utils.operation_log import log_operation
from utils.event_stats import recalc_event_stats
import uuid


logger = logging.getLogger(__name__)
purchase_records_bp = Blueprint('purchase_records', __name__)


def get_presigned_url(file_key: str, expires: int = 3600 * 24) -> str:
    """获取文件预签名URL"""
    if not file_key:
        return None
    
    if storage_manager.is_available():
        if file_key.startswith('invoices/') or file_key.startswith('uploads/'):
            try:
                return storage_manager.get_presigned_url(file_key, expires=expires)
            except Exception as e:
                logger.warning(f'生成预签名URL失败: {file_key}, 错误: {str(e)}')
                return None
    
    if file_key.startswith('/uploads/'):
        return file_key
    
    return None


# ---------------------------------------------------------------------------
# 附件（购物凭证 / 发票）多文件支持
# ---------------------------------------------------------------------------

def _clean_text(value):
    """去掉首尾空白；空值统一返回 None。"""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _serialize_record_file(row):
    """附件行 → 前端可直接展示/下载的结构。"""
    if row.file_type == PurchaseRecord.FILE_TYPE_INVOICE:
        file_url = get_presigned_url(row.file_key)
        preview_url = get_presigned_url(row.preview_key) or file_url
    else:
        file_url = get_presigned_url(row.file_key) or row.file_key
        preview_url = file_url

    return {
        'file_id': row.file_id,
        'file_type': row.file_type,
        'file_key': row.file_key,
        'preview_key': row.preview_key,
        'file_url': file_url,
        'preview_url': preview_url,
        'original_filename': row.original_filename,
        'file_md5': row.file_md5,
        'sort_order': row.sort_order or 0,
        'is_pdf': bool(row.file_key and row.file_key.lower().endswith('.pdf')),
        'download_url': (f'/api/records/{row.record_id}/files/{row.file_id}/download'
                         if row.file_id else None),
    }


def _legacy_record_files(record):
    """旧库（附件表还没回填）时用单文件列兜底，保证旧数据仍能展示。"""
    receipt_files = []
    if record.receipt_image_url:
        receipt_url = get_presigned_url(record.receipt_image_url) or record.receipt_image_url
        receipt_files.append({
            'file_id': None,
            'file_type': PurchaseRecord.FILE_TYPE_RECEIPT,
            'file_key': record.receipt_image_url,
            'preview_key': None,
            'file_url': receipt_url,
            'preview_url': receipt_url,
            'original_filename': record.receipt_image_name,
            'file_md5': record.receipt_file_md5,
            'sort_order': 0,
            'is_pdf': False,
            'download_url': None,
        })

    invoice_files = []
    if record.invoice_file_key:
        invoice_url = get_presigned_url(record.invoice_file_key)
        invoice_files.append({
            'file_id': None,
            'file_type': PurchaseRecord.FILE_TYPE_INVOICE,
            'file_key': record.invoice_file_key,
            'preview_key': record.invoice_preview_key,
            'file_url': invoice_url,
            'preview_url': get_presigned_url(record.invoice_preview_key) or invoice_url,
            'original_filename': record.invoice_original_filename,
            'file_md5': record.invoice_md5,
            'sort_order': 0,
            'is_pdf': bool(record.invoice_file_key.lower().endswith('.pdf')),
            'download_url': None,
        })

    return receipt_files, invoice_files


def _record_files_payload(record):
    """返回 (购物凭证列表, 发票列表)。"""
    rows = list(record.files or [])
    receipt_files = [
        _serialize_record_file(row) for row in rows
        if row.file_type == PurchaseRecord.FILE_TYPE_RECEIPT
    ]
    invoice_files = [
        _serialize_record_file(row) for row in rows
        if row.file_type == PurchaseRecord.FILE_TYPE_INVOICE
    ]

    legacy_receipts, legacy_invoices = _legacy_record_files(record)
    if not receipt_files:
        receipt_files = legacy_receipts
    if not invoice_files:
        invoice_files = legacy_invoices
    return receipt_files, invoice_files


def _normalize_file_entries(raw_files):
    """把前端提交的附件数组整理成统一结构（过滤空项、按 file_key 去重、保持顺序）。"""
    if not isinstance(raw_files, list):
        return []

    entries = []
    seen = set()
    for item in raw_files:
        if isinstance(item, str):
            item = {'file_key': item}
        if not isinstance(item, dict):
            continue

        file_key = _clean_text(
            item.get('file_key') or item.get('receipt_image_url') or item.get('key')
        )
        if not file_key or file_key in seen:
            continue
        seen.add(file_key)
        entries.append({
            'file_key': file_key,
            'preview_key': _clean_text(item.get('preview_key') or item.get('invoice_preview_key')),
            'original_filename': _clean_text(
                item.get('original_filename')
                or item.get('receipt_image_name')
                or item.get('invoice_original_filename')
            ),
            'file_md5': _clean_text(item.get('file_md5') or item.get('invoice_md5')),
        })
    return entries


def _collect_submitted_files(data, file_type):
    """从请求体里取某一类附件。

    - 返回 None：本次请求没有提交该类附件，保持数据库里的现状；
    - 返回 []：明确提交了空列表，表示要清空该类附件；
    - 返回条目列表：以本次提交为准整体替换。

    同时兼容旧客户端的单文件字段（receipt_image_url / invoice_file_key）。
    """
    if file_type == PurchaseRecord.FILE_TYPE_RECEIPT:
        if 'receipt_files' in data:
            return _normalize_file_entries(data.get('receipt_files'))
        if 'receipt_image_url' in data:
            return _normalize_file_entries([{
                'file_key': data.get('receipt_image_url'),
                'original_filename': data.get('receipt_image_name'),
                'file_md5': data.get('receipt_file_md5'),
            }])
        return None

    if 'invoice_files' in data:
        return _normalize_file_entries(data.get('invoice_files'))
    if 'invoice_file_key' in data:
        return _normalize_file_entries([{
            'file_key': data.get('invoice_file_key'),
            'preview_key': data.get('invoice_preview_key'),
            'original_filename': data.get('invoice_original_filename'),
            'file_md5': data.get('invoice_md5'),
        }])
    return None


def _replace_record_files(record, file_type, entries):
    """用新的附件列表整体替换某一类附件（entries 为 None 时保持原样）。"""
    if entries is None:
        return

    for row in list(record.files):
        if row.file_type == file_type:
            record.files.remove(row)

    for index, entry in enumerate(entries):
        record.files.append(PurchaseRecordFile(
            file_type=file_type,
            file_key=entry['file_key'],
            preview_key=entry['preview_key'],
            original_filename=entry['original_filename'],
            file_md5=entry['file_md5'],
            sort_order=index,
        ))


def _sync_legacy_file_columns(record):
    """附件表 → 旧单文件列（只保留第一个文件），导出等旧逻辑继续可用。"""
    receipt = next(
        (row for row in record.files if row.file_type == PurchaseRecord.FILE_TYPE_RECEIPT),
        None,
    )
    invoice = next(
        (row for row in record.files if row.file_type == PurchaseRecord.FILE_TYPE_INVOICE),
        None,
    )

    if receipt is not None:
        record.receipt_image_url = receipt.file_key
        record.receipt_image_name = receipt.original_filename
        record.receipt_file_md5 = receipt.file_md5

    if invoice is not None and not record.cannot_invoice:
        record.has_invoice = True
        record.invoice_file_key = invoice.file_key
        record.invoice_preview_key = invoice.preview_key
        record.invoice_original_filename = invoice.original_filename
        record.invoice_md5 = invoice.file_md5
    else:
        record.has_invoice = False
        record.invoice_file_key = None
        record.invoice_preview_key = None
        record.invoice_original_filename = None
        record.invoice_md5 = None


def _apply_submitted_files(record, data):
    """把请求里的附件写入附件表，并同步旧单文件列。

    返回 (购物凭证数量, 发票数量)。购物凭证至少要有一份。
    """
    changed = False

    receipt_entries = _collect_submitted_files(data, PurchaseRecord.FILE_TYPE_RECEIPT)
    if receipt_entries is not None:
        if not receipt_entries:
            raise ValueError('必须至少上传一张购物凭证')
        _replace_record_files(record, PurchaseRecord.FILE_TYPE_RECEIPT, receipt_entries)
        changed = True

    invoice_entries = _collect_submitted_files(data, PurchaseRecord.FILE_TYPE_INVOICE)
    if record.cannot_invoice:
        # 「无法开票」时不允许挂发票，顺手清空历史发票
        invoice_entries = []
    if invoice_entries is not None:
        _replace_record_files(record, PurchaseRecord.FILE_TYPE_INVOICE, invoice_entries)
        changed = True

    _sync_legacy_file_columns(record)

    if changed:
        # 附件变动必须刷新记录的 updated_at，否则导出缓存会误判为「数据未变」，
        # 继续命中旧的单文件版本导出结果。
        record.updated_at = datetime.now(timezone.utc)

    receipt_count = sum(
        1 for row in record.files if row.file_type == PurchaseRecord.FILE_TYPE_RECEIPT
    )
    invoice_count = sum(
        1 for row in record.files if row.file_type == PurchaseRecord.FILE_TYPE_INVOICE
    )
    return receipt_count, invoice_count


def _first_invoice_file(record):
    """第一条发票附件（附件表优先，旧单文件列兜底）。"""
    for row in record.files:
        if row.file_type == PurchaseRecord.FILE_TYPE_INVOICE:
            return {
                'file_key': row.file_key,
                'preview_key': row.preview_key,
                'original_filename': row.original_filename or row.file_key.split('/')[-1],
            }

    if record.invoice_file_key:
        return {
            'file_key': record.invoice_file_key,
            'preview_key': record.invoice_preview_key,
            'original_filename': record.invoice_original_filename
            or record.invoice_file_key.split('/')[-1],
        }
    return None


def _read_file_bytes(file_key):
    """从 COS 或本地 uploads 目录读取文件内容。找不到返回 None。"""
    if storage_manager.is_available() and (
        file_key.startswith('invoices/') or file_key.startswith('uploads/')
    ):
        try:
            return storage_manager.download_file(file_key)
        except Exception as e:
            logger.error(f'从COS下载文件失败: {str(e)}')
            return None

    uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
    filename = file_key.replace('/uploads/', '').replace('uploads/', '')
    local_path = os.path.join(uploads_dir, filename)
    if os.path.exists(local_path):
        with open(local_path, 'rb') as f:
            return f.read()
    return None


def _store_preview_image(jpg_bytes):
    """保存发票预览 JPG（COS 优先、本地兜底），返回可持久化的 file_key。"""
    if not jpg_bytes:
        return None

    unique_id = uuid.uuid4().hex
    if storage_manager.is_available():
        preview_key = f"invoices/{unique_id}_preview.jpg"
        try:
            storage_manager.upload_bytes(jpg_bytes, preview_key)
            return preview_key
        except Exception as e:
            logger.error(f'发票预览图上传失败: {str(e)}')
            return None

    uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
    try:
        os.makedirs(uploads_dir, exist_ok=True)
        filename = f"{unique_id}_preview.jpg"
        with open(os.path.join(uploads_dir, filename), 'wb') as f:
            f.write(jpg_bytes)
        return f"/uploads/{filename}"
    except Exception as e:
        logger.error(f'发票预览图本地保存失败: {str(e)}')
        return None


def _persist_invoice_preview(record, file_key, preview_key):
    """把发票预览 key 落库（附件行 + 旧单文件列），已有则覆盖。"""
    if not preview_key:
        return

    changed = False
    for row in record.files:
        if row.file_type == PurchaseRecord.FILE_TYPE_INVOICE and row.file_key == file_key:
            if row.preview_key != preview_key:
                row.preview_key = preview_key
                changed = True
            break

    if record.invoice_file_key == file_key and not record.cannot_invoice:
        if record.invoice_preview_key != preview_key:
            record.invoice_preview_key = preview_key
            changed = True

    if changed:
        db.session.commit()


def _file_download_response(file_key, original_filename):
    """构造附件下载响应（COS 直出字节流，本地文件 send_file）。"""
    if storage_manager.is_available() and (
        file_key.startswith('invoices/') or file_key.startswith('uploads/')
    ):
        file_bytes = storage_manager.download_file(file_key)
        content_type = 'application/pdf' if file_key.lower().endswith('.pdf') else 'image/jpeg'
        return Response(
            file_bytes,
            mimetype=content_type,
            headers={'Content-Disposition': f'attachment; filename="{original_filename}"'},
        )

    uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
    filename = file_key.replace('/uploads/', '').replace('uploads/', '')
    file_path = os.path.join(uploads_dir, filename)
    if not os.path.exists(file_path):
        return None
    return send_file(file_path, as_attachment=True, download_name=original_filename)


@purchase_records_bp.route('/events/<int:event_id>/records', methods=['GET'])
@jwt_required()
def get_purchase_records(event_id):
    logger.info(f'=== 获取购买记录列表: event_id={event_id} ===')
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({'code': 401, 'message': '用户不存在', 'data': None}), 401
        
        event = Event.query.get(event_id)
        if not event:
            return jsonify({'code': 404, 'message': '赛事不存在', 'data': None}), 404

        # 分页参数
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 30, type=int)
        page = max(1, page)
        page_size = min(max(1, page_size), 100)  # 限制最大100条

        query = PurchaseRecord.query.filter_by(
            event_id=event_id,
            is_deleted=False
        ).order_by(PurchaseRecord.created_at.desc())

        uploader_id = request.args.get('uploader_id', type=int)
        if uploader_id:
            query = query.filter_by(uploader_id=uploader_id)

        # 计算总数
        total = query.count()
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        
        # 分页查询
        records = query.offset((page - 1) * page_size).limit(page_size).all()
        
        records_data = []
        for record in records:
            uploader = User.query.get(record.uploader_id)
            
            invoice_file_url = get_presigned_url(record.invoice_file_key)
            invoice_preview_url = get_presigned_url(record.invoice_preview_key) or invoice_file_url
            receipt_image_url = get_presigned_url(record.receipt_image_url) or record.receipt_image_url
            receipt_files, invoice_files = _record_files_payload(record)

            records_data.append({
                'record_id': record.record_id,
                'event_id': record.event_id,
                'item_name': record.item_name,
                'purchase_platform': record.purchase_platform,
                'purchase_date': record.purchase_date.isoformat() if record.purchase_date else None,
                'amount': float(record.amount),
                'receipt_image_url': receipt_image_url,
                'receipt_image_name': record.receipt_image_name,
                'receipt_files': receipt_files,
                'receipt_count': len(receipt_files),
                'cannot_invoice': record.cannot_invoice,
                'has_invoice': record.has_invoice,
                'invoice_files': invoice_files,
                'invoice_count': len(invoice_files),
                'invoice_file_key': record.invoice_file_key,
                'invoice_preview_key': record.invoice_preview_key,
                'invoice_url': invoice_file_url,
                'invoice_preview_url': invoice_preview_url,
                'invoice_original_filename': record.invoice_original_filename,
                'invoice_type': record.invoice_type,
                'invoice_number': record.invoice_number,
                'invoice_tax_number': record.invoice_tax_number or '',
                'total_amount': float(record.total_amount) if record.total_amount else 0,
                'invoice_date': record.invoice_date.isoformat() if record.invoice_date else None,
                'is_reimbursed': record.is_reimbursed,
                'remarks': record.remarks,
                'uploader_id': record.uploader_id,
                'uploader_name': uploader.real_name if uploader else None,
                'created_at': record.created_at.isoformat() if record.created_at else None
            })
        
        total_amount = sum(r['amount'] for r in records_data)
        invoice_total = sum(r['total_amount'] for r in records_data if r['has_invoice'])
        pending_reimburse = sum(r['total_amount'] for r in records_data if r['has_invoice'] and not r['is_reimbursed'])
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'records': records_data,
                'total_count': total,
                'total_amount': str(total_amount),
                'invoice_total': str(invoice_total),
                'pending_reimburse': str(pending_reimburse),
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total': total,
                    'total_pages': total_pages
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f'获取购买记录异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


@purchase_records_bp.route('/events/<int:event_id>/records', methods=['POST'])
@jwt_required()
def create_purchase_record(event_id):
    logger.info(f'=== 创建购买记录: event_id={event_id} ===')
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({'code': 401, 'message': '用户不存在', 'data': None}), 401
        
        event = Event.query.get(event_id)
        if not event:
            return jsonify({'code': 404, 'message': '赛事不存在', 'data': None}), 404
        
        data = request.get_json()
        
        required_fields = ['item_name', 'purchase_platform', 'purchase_date', 'amount']
        for field in required_fields:
            if field not in data or data[field] is None or (isinstance(data[field], str) and not data[field].strip()):
                return jsonify({'code': 400, 'message': f'{field}不能为空', 'data': None}), 400
        
        # 检查学生是否有权限访问该项目
        if not check_student_event_access(event_id, user):
            return jsonify({'code': 403, 'message': '您未加入该项目，无法上传记录', 'data': None}), 403

        # 自动检查并添加赛事成员
        ensure_event_membership(event_id, int(current_user_id))

        cannot_invoice = bool(data.get('cannot_invoice'))
        receipt_entries = _collect_submitted_files(data, PurchaseRecord.FILE_TYPE_RECEIPT) or []
        if not receipt_entries:
            return jsonify({'code': 400, 'message': '必须至少上传一张购物凭证图片', 'data': None}), 400

        # 「可开票」但一份发票文件都没传时，直接按「无发票」状态落库
        invoice_entries = []
        if not cannot_invoice:
            invoice_entries = _collect_submitted_files(data, PurchaseRecord.FILE_TYPE_INVOICE) or []
        has_invoice = bool(invoice_entries)

        # 发票金额自动填充：有发票时，实际开销以发票解析结果为准
        invoice_total = float(data.get('total_amount')) if data.get('total_amount') is not None else 0.0
        if has_invoice and invoice_total > 0:
            actual_amount = invoice_total
        else:
            actual_amount = float(data['amount']) if data.get('amount') is not None else 0.0

        first_receipt = receipt_entries[0]
        first_invoice = invoice_entries[0] if invoice_entries else None

        record = PurchaseRecord(
            event_id=event_id,
            uploader_id=current_user_id,
            item_name=data['item_name'],
            purchase_platform=data['purchase_platform'],
            purchase_date=datetime.strptime(data['purchase_date'], '%Y-%m-%d').date() if isinstance(data['purchase_date'], str) else data['purchase_date'],
            amount=actual_amount,
            receipt_image_url=first_receipt['file_key'],
            receipt_image_name=first_receipt['original_filename'],
            receipt_file_md5=first_receipt['file_md5'],
            cannot_invoice=cannot_invoice,
            has_invoice=has_invoice,
            invoice_file_key=first_invoice['file_key'] if first_invoice else None,
            invoice_preview_key=first_invoice['preview_key'] if first_invoice else None,
            invoice_original_filename=first_invoice['original_filename'] if first_invoice else None,
            invoice_md5=first_invoice['file_md5'] if first_invoice else None,
            invoice_type=data.get('invoice_type'),
            invoice_number=data.get('invoice_number'),
            invoice_tax_number=data.get('invoice_tax_number'),
            total_amount=invoice_total,
            invoice_date=datetime.strptime(data['invoice_date'], '%Y-%m-%d').date() if data.get('invoice_date') else None,
            remarks=data.get('remarks')
        )

        db.session.add(record)
        db.session.flush()  # 在提交前获取 record_id

        # 写入多文件附件（旧单文件列同步为第一个文件）
        _replace_record_files(record, PurchaseRecord.FILE_TYPE_RECEIPT, receipt_entries)
        _replace_record_files(record, PurchaseRecord.FILE_TYPE_INVOICE, invoice_entries)

        # 更新赛事统计（统一按明细表重算）
        recalc_event_stats(record.event_id)

        db.session.commit()

        logger.info(f'购买记录创建成功: record_id={record.record_id}')

        log_operation(
            user_id=current_user_id,
            username=user.real_name or user.username,
            action_type='create_record',
            action_description=f'创建购买记录：{record.item_name}（金额：{record.amount}）',
            target_type='purchase_record',
            target_id=record.record_id,
            target_name=record.item_name,
            event_id=event_id,
            event_name=event.event_name,
            detail={
                'item_name': record.item_name,
                'purchase_platform': record.purchase_platform,
                'purchase_date': record.purchase_date.isoformat() if record.purchase_date else None,
                'amount': float(record.amount),
                'has_invoice': record.has_invoice,
                'cannot_invoice': record.cannot_invoice,
                'total_amount': float(record.total_amount or 0)
            }
        )

        return jsonify({
            'code': 200,
            'message': '购买记录创建成功',
            'data': {
                'record_id': record.record_id,
                'item_name': record.item_name,
                'has_invoice': record.has_invoice
            }
        }), 201
        
    except Exception as e:
        logger.error(f'创建购买记录异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


@purchase_records_bp.route('/records/<int:record_id>', methods=['PUT'])
@jwt_required()
def update_purchase_record(record_id):
    logger.info(f'=== 更新购买记录: record_id={record_id} ===')
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({'code': 401, 'message': '用户不存在', 'data': None}), 401
        
        record = PurchaseRecord.query.filter_by(record_id=record_id, is_deleted=False).first()
        if not record:
            return jsonify({'code': 404, 'message': '记录不存在', 'data': None}), 404
        
        data = request.get_json()

        # 仅上传者或 admin/teacher/student_admin 可修改
        is_admin_or_teacher = user.user_type in ['admin', 'teacher', 'student_admin']
        is_uploader = record.uploader_id == int(current_user_id)
        if not (is_admin_or_teacher or is_uploader):
            return jsonify({'code': 403, 'message': '只能修改自己的购买记录', 'data': None}), 403

        # 学生权限检查：必须是项目成员
        if not check_student_event_access(record.event_id, user):
            return jsonify({'code': 403, 'message': '您未加入该项目，无法修改记录', 'data': None}), 403

        # 自动检查并添加赛事成员
        if is_admin_or_teacher:
            ensure_event_membership(record.event_id, int(current_user_id))

        # 在更新前保存旧值
        old_values = {
            'item_name': record.item_name,
            'purchase_platform': record.purchase_platform,
            'purchase_date': record.purchase_date.strftime('%Y-%m-%d') if record.purchase_date else None,
            'amount': float(record.amount) if record.amount else 0,
            'remarks': record.remarks,
            'invoice_type': record.invoice_type,
            'invoice_number': record.invoice_number,
            'total_amount': float(record.total_amount) if record.total_amount else 0,
            'invoice_date': record.invoice_date.strftime('%Y-%m-%d') if record.invoice_date else None
        }

        if 'item_name' in data and data['item_name'] is not None:
            record.item_name = data['item_name']
        if 'purchase_platform' in data and data['purchase_platform'] is not None:
            record.purchase_platform = data['purchase_platform']
        if 'purchase_date' in data and data['purchase_date']:
            record.purchase_date = datetime.strptime(data['purchase_date'][:10], '%Y-%m-%d').date() if isinstance(data['purchase_date'], str) else data['purchase_date']
        if 'cannot_invoice' in data:
            record.cannot_invoice = bool(data['cannot_invoice'])
            if record.cannot_invoice:
                record.has_invoice = False
                record.invoice_type = None
                record.invoice_number = None
                record.invoice_tax_number = None
                record.total_amount = 0
                record.invoice_date = None

        # 多文件附件：本次提交的附件整体替换旧数据，并同步旧单文件列
        try:
            _apply_submitted_files(record, data)
        except ValueError as e:
            db.session.rollback()
            return jsonify({'code': 400, 'message': str(e), 'data': None}), 400

        if 'invoice_type' in data:
            record.invoice_type = data['invoice_type']
        if 'invoice_number' in data:
            record.invoice_number = data['invoice_number']
        if 'invoice_tax_number' in data:
            record.invoice_tax_number = data['invoice_tax_number']
        if 'total_amount' in data and data['total_amount'] is not None:
            record.total_amount = float(data['total_amount']) if data['total_amount'] else 0
        if 'invoice_date' in data and data['invoice_date']:
            record.invoice_date = datetime.strptime(data['invoice_date'][:10], '%Y-%m-%d').date() if isinstance(data['invoice_date'], str) else data['invoice_date']
        if 'remarks' in data:
            record.remarks = data['remarks']

        # 发票金额自动填充：有发票时，实际开销以发票价税合计为准，禁止手动修改
        if record.has_invoice and record.total_amount and float(record.total_amount) > 0:
            record.amount = float(record.total_amount)
        elif 'amount' in data and data['amount'] is not None:
            record.amount = float(data['amount']) if data['amount'] else 0.0

        # 允许管理员/教师/学生管理员修改上传人
        if 'uploader_id' in data and data['uploader_id'] is not None and is_admin_or_teacher:
            new_uploader_id = int(data['uploader_id'])
            new_uploader = User.query.get(new_uploader_id)
            if not new_uploader or new_uploader.is_deleted:
                return jsonify({'code': 400, 'message': '目标上传用户不存在', 'data': None}), 400
            record.uploader_id = new_uploader_id

        recalc_event_stats(record.event_id)

        db.session.commit()

        logger.info(f'购买记录更新成功: record_id={record_id}')

        event = Event.query.get(record.event_id)

        # 构造变更详情（记录修改的字段及新旧值）
        changes = {}
        for key in ['item_name', 'purchase_platform', 'purchase_date', 'amount', 'remarks',
                     'invoice_type', 'invoice_number', 'total_amount', 'invoice_date']:
            # 只处理前端明确发送且有实际内容的值
            raw = data.get(key)
            # 过滤：None、空字符串、"null"、数字0、空列表/字典、布尔值
            if raw is None or raw == '' or raw == 'null' or raw == 'NULL':
                continue
            if isinstance(raw, (int, float)) and raw == 0:
                continue
            if isinstance(raw, (list, dict, bool)):
                continue

            old_val = old_values.get(key)
            new_val = raw

            if key == 'purchase_date':
                new_val = raw[:10] if isinstance(raw, str) else str(raw)
            elif key == 'amount' or key == 'total_amount':
                new_val = float(raw) if raw else 0

            # 规范化比较：None 和空字符串视为等价
            old_norm = old_val if old_val is not None else ''
            new_norm = new_val if new_val is not None else ''
            if str(old_norm).strip() != str(new_norm).strip():
                changes[key] = {'old': old_val, 'new': new_val}

        # 中文字段名映射
        field_labels = {
            'item_name': '物品名称',
            'purchase_platform': '购买平台',
            'purchase_date': '购买日期',
            'amount': '金额',
            'remarks': '备注',
            'invoice_type': '发票类型',
            'invoice_number': '发票号码',
            'total_amount': '价税合计',
            'invoice_date': '开票日期'
        }

        def fmt_value(val):
            if val is None or val == '':
                return '（空）'
            return f'"{val}"'

        if changes:
            change_parts = []
            for k in changes.keys():
                label = field_labels.get(k, k)
                old_str = fmt_value(changes[k]['old'])
                new_str = fmt_value(changes[k]['new'])
                change_parts.append(f'{label}: {old_str} → {new_str}')
            action_desc = f'修改购买记录「{record.item_name}」: ' + '；'.join(change_parts)
        else:
            action_desc = f'修改购买记录「{record.item_name}」'

        log_operation(
            user_id=current_user_id,
            username=user.real_name or user.username,
            action_type='update_record',
            action_description=action_desc,
            target_type='purchase_record',
            target_id=record.record_id,
            target_name=record.item_name,
            event_id=record.event_id,
            event_name=event.event_name if event else None,
            detail={
                'record_id': record.record_id,
                'item_name': record.item_name,
                'changes': changes,
                'has_invoice': record.has_invoice,
                'is_reimbursed': record.is_reimbursed
            }
        )

        return jsonify({
            'code': 200,
            'message': '更新成功',
            'data': {'record_id': record_id}
        }), 200
        
    except Exception as e:
        logger.error(f'更新购买记录异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


@purchase_records_bp.route('/records/<int:record_id>/transfer', methods=['POST'])
@jwt_required()
def transfer_purchase_record(record_id):
    """将购买记录转移到其他比赛项目"""
    logger.info(f'=== 转移购买记录: record_id={record_id} ===')
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({'code': 401, 'message': '用户不存在', 'data': None}), 401

        record = PurchaseRecord.query.filter_by(record_id=record_id, is_deleted=False).first()
        if not record:
            return jsonify({'code': 404, 'message': '记录不存在', 'data': None}), 404

        data = request.get_json()
        if not data or 'target_event_id' not in data:
            return jsonify({'code': 400, 'message': '缺少目标比赛项目ID', 'data': None}), 400

        target_event_id = int(data['target_event_id'])

        # 检查目标项目是否存在
        target_event = Event.query.filter_by(event_id=target_event_id, is_deleted=False).first()
        if not target_event:
            return jsonify({'code': 404, 'message': '目标比赛项目不存在', 'data': None}), 404

        # 不能转移到同一个项目
        if target_event_id == record.event_id:
            return jsonify({'code': 400, 'message': '不能转移到同一个比赛项目', 'data': None}), 400

        is_admin_or_teacher = user.user_type in ['admin', 'teacher', 'student_admin']
        is_uploader = record.uploader_id == int(current_user_id)

        # 权限检查：只有上传者或管理员/教师/学生管理员可以转移
        if not (is_admin_or_teacher or is_uploader):
            return jsonify({'code': 403, 'message': '只能转移自己的购买记录', 'data': None}), 403

        # 学生权限检查：必须是源项目成员
        if not check_student_event_access(record.event_id, user):
            return jsonify({'code': 403, 'message': '您未加入源项目，无法转移记录', 'data': None}), 403

        # 检查用户是否有目标项目的操作权限
        if not check_student_event_access(target_event_id, user):
            return jsonify({'code': 403, 'message': '您未加入目标比赛项目，无法转移记录', 'data': None}), 403

        # 自动检查并添加赛事成员（管理员/教师）
        if is_admin_or_teacher:
            ensure_event_membership(record.event_id, int(current_user_id))
            ensure_event_membership(target_event_id, int(current_user_id))

        old_event_id = record.event_id
        record.event_id = target_event_id

        # 清除报销状态（因为换了项目，需要在新项目中重新确认报销）
        record.is_reimbursed = False
        record.reimbursed_at = None

        # 源项目与目标项目的统计都要重算
        recalc_event_stats(old_event_id)
        recalc_event_stats(target_event_id)

        db.session.commit()

        logger.info(f'购买记录转移成功: record_id={record_id}, {old_event_id} -> {target_event_id}')

        source_event = Event.query.get(old_event_id)
        log_operation(
            user_id=current_user_id,
            username=user.real_name or user.username,
            action_type='transfer_record',
            action_description=f'转移购买记录：{record.item_name}（从「{source_event.event_name if source_event else old_event_id}」到「{target_event.event_name}」）',
            target_type='purchase_record',
            target_id=record.record_id,
            target_name=record.item_name,
            event_id=target_event_id,
            event_name=target_event.event_name,
            detail={
                'source_event_id': old_event_id,
                'source_event_name': source_event.event_name if source_event else None,
                'target_event_id': target_event_id,
                'target_event_name': target_event.event_name,
                'amount': float(record.amount or 0),
                'has_invoice': record.has_invoice
            }
        )

        return jsonify({
            'code': 200,
            'message': '转移成功',
            'data': {
                'record_id': record_id,
                'old_event_id': old_event_id,
                'new_event_id': target_event_id,
                'target_event_name': target_event.event_name
            }
        }), 200

    except Exception as e:
        logger.error(f'转移购买记录异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


@purchase_records_bp.route('/records/batch-transfer', methods=['POST'])
@jwt_required()
def batch_transfer_purchase_records():
    """批量转移购买记录到其他比赛项目"""
    logger.info('=== 批量转移购买记录 ===')
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({'code': 401, 'message': '用户不存在', 'data': None}), 401

        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '请求数据无效', 'data': None}), 400

        record_ids_raw = data.get('record_ids', [])
        target_event_id = data.get('target_event_id')

        if not record_ids_raw or not isinstance(record_ids_raw, list) or len(record_ids_raw) == 0:
            return jsonify({'code': 400, 'message': '请选择要转移的记录', 'data': None}), 400

        if not target_event_id:
            return jsonify({'code': 400, 'message': '请选择目标比赛项目', 'data': None}), 400

        target_event_id = int(target_event_id)

        # 解析 record_id：支持 "P116" 格式，提取纯数字
        record_ids = []
        for rid in record_ids_raw:
            rid_str = str(rid).strip()
            # 去掉前缀字母，只保留数字部分
            numeric_id = ''.join(filter(str.isdigit, rid_str))
            if numeric_id:
                record_ids.append(int(numeric_id))

        if not record_ids:
            return jsonify({'code': 400, 'message': '记录ID无效', 'data': None}), 400

        # 检查目标项目是否存在
        target_event = Event.query.filter_by(event_id=target_event_id, is_deleted=False).first()
        if not target_event:
            return jsonify({'code': 404, 'message': '目标比赛项目不存在', 'data': None}), 404

        is_admin_or_teacher = user.user_type in ['admin', 'teacher', 'student_admin']
        touched_event_ids = {target_event_id}

        # 检查用户是否有目标项目的操作权限
        if not check_student_event_access(target_event_id, user):
            return jsonify({'code': 403, 'message': '您未加入目标比赛项目，无法转移记录', 'data': None}), 403

        # 获取所有要转移的记录
        records = PurchaseRecord.query.filter(
            PurchaseRecord.record_id.in_(record_ids),
            PurchaseRecord.is_deleted == False
        ).all()

        if len(records) == 0:
            return jsonify({'code': 404, 'message': '没有找到要转移的记录', 'data': None}), 404

        # 检查权限：对于每条记录，检查用户是否有权限
        if not is_admin_or_teacher:
            for record in records:
                if record.uploader_id != int(current_user_id):
                    return jsonify({'code': 403, 'message': '只能转移自己的购买记录', 'data': None}), 403
                if not check_student_event_access(record.event_id, user):
                    return jsonify({'code': 403, 'message': '您未加入部分记录所在的项目，无法转移', 'data': None}), 403

        # 执行转移
        success_count = 0
        failed_records = []
        transfer_details = []

        for record in records:
            # 不能转移到同一个项目
            if record.event_id == target_event_id:
                failed_records.append({
                    'record_id': record.record_id,
                    'item_name': record.item_name,
                    'reason': '不能转移到同一个比赛项目'
                })
                continue

            # 学生权限检查：必须是源项目成员
            if not is_admin_or_teacher and not check_student_event_access(record.event_id, user):
                failed_records.append({
                    'record_id': record.record_id,
                    'item_name': record.item_name,
                    'reason': '您未加入源项目'
                })
                continue

            old_event_id = record.event_id
            record.event_id = target_event_id
            # 清除报销状态
            record.is_reimbursed = False
            record.reimbursed_at = None
            touched_event_ids.add(old_event_id)

            # 获取源项目信息
            source_event = Event.query.get(old_event_id)

            success_count += 1
            transfer_details.append({
                'record_id': record.record_id,
                'item_name': record.item_name,
                'source_event_id': old_event_id,
                'source_event_name': source_event.event_name if source_event else None,
                'target_event_id': target_event_id,
                'target_event_name': target_event.event_name
            })

            log_operation(
                user_id=current_user_id,
                username=user.real_name or user.username,
                action_type='transfer_record',
                action_description=f'批量转移：{record.item_name}（从「{source_event.event_name if source_event else old_event_id}」到「{target_event.event_name}」）',
                target_type='purchase_record',
                target_id=record.record_id,
                target_name=record.item_name,
                event_id=target_event_id,
                event_name=target_event.event_name,
                detail={
                    'source_event_id': old_event_id,
                    'source_event_name': source_event.event_name if source_event else None,
                    'target_event_id': target_event_id,
                    'target_event_name': target_event.event_name,
                    'amount': float(record.amount or 0),
                    'has_invoice': record.has_invoice,
                    'batch_transfer': True
                }
            )

        # 源项目与目标项目的统计都要重算
        for eid in touched_event_ids:
            recalc_event_stats(eid)

        db.session.commit()

        logger.info(f'批量转移完成: 成功 {success_count} 条, 失败 {len(failed_records)} 条')

        return jsonify({
            'code': 200,
            'message': f'批量转移完成：成功 {success_count} 条，失败 {len(failed_records)} 条',
            'data': {
                'success_count': success_count,
                'failed_count': len(failed_records),
                'failed_records': failed_records,
                'transfer_details': transfer_details
            }
        }), 200

    except Exception as e:
        logger.error(f'批量转移购买记录异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


@purchase_records_bp.route('/records/<int:record_id>', methods=['DELETE'])
@jwt_required()
def delete_purchase_record(record_id):
    logger.info(f'=== 删除购买记录: record_id={record_id} ===')
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({'code': 401, 'message': '用户不存在', 'data': None}), 401
        
        record = PurchaseRecord.query.filter_by(record_id=record_id, is_deleted=False).first()
        if not record:
            return jsonify({'code': 404, 'message': '记录不存在', 'data': None}), 404
        
        is_admin_or_teacher = user.user_type in ['admin', 'teacher', 'student_admin']
        is_uploader = record.uploader_id == int(current_user_id)
        
        if not (is_admin_or_teacher or is_uploader):
            return jsonify({'code': 403, 'message': '权限不足', 'data': None}), 403

        # 学生权限检查：必须是项目成员
        if not check_student_event_access(record.event_id, user):
            return jsonify({'code': 403, 'message': '您未加入该项目，无法删除记录', 'data': None}), 403

        # 自动检查并添加赛事成员
        if is_admin_or_teacher:
            ensure_event_membership(record.event_id, int(current_user_id))

        record.is_deleted = True
        db.session.commit()

        logger.info(f'购买记录删除成功: record_id={record_id}')

        event = Event.query.get(record.event_id)
        log_operation(
            user_id=current_user_id,
            username=user.real_name or user.username,
            action_type='delete_record',
            action_description=f'删除购买记录：{record.item_name}',
            target_type='purchase_record',
            target_id=record.record_id,
            target_name=record.item_name,
            event_id=record.event_id,
            event_name=event.event_name if event else None,
            detail={
                'item_name': record.item_name,
                'amount': float(record.amount or 0),
                'has_invoice': record.has_invoice,
                'total_amount': float(record.total_amount or 0),
                'is_reimbursed': record.is_reimbursed
            }
        )

        return jsonify({
            'code': 200,
            'message': '删除成功',
            'data': None
        }), 200
        
    except Exception as e:
        logger.error(f'删除购买记录异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


@purchase_records_bp.route('/records/<int:record_id>/reimburse', methods=['POST'])
@jwt_required()
def reimburse_purchase_record(record_id):
    logger.info(f'=== 报销购买记录: record_id={record_id} ===')
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or user.user_type not in ['admin', 'teacher', 'student_admin']:
            return jsonify({'code': 403, 'message': '权限不足', 'data': None}), 403

        record = PurchaseRecord.query.filter_by(record_id=record_id, is_deleted=False).first()
        if not record:
            return jsonify({'code': 404, 'message': '记录不存在', 'data': None}), 404

        # 自动检查并添加赛事成员
        ensure_event_membership(record.event_id, int(current_user_id))

        if not record.has_invoice:
            return jsonify({'code': 400, 'message': '该记录没有发票，无法报销', 'data': None}), 400
        
        if record.is_reimbursed:
            return jsonify({'code': 400, 'message': '该记录已经报销过了', 'data': None}), 400
        
        record.is_reimbursed = True
        record.reimbursed_at = datetime.now(timezone.utc)
        
        event = Event.query.get(record.event_id)
        recalc_event_stats(record.event_id)

        db.session.commit()

        log_operation(
            user_id=current_user_id,
            username=user.real_name or user.username,
            action_type='reimburse_record',
            action_description=f'报销购买记录：{record.item_name}（金额：{record.total_amount or record.amount}）',
            target_type='purchase_record',
            target_id=record.record_id,
            target_name=record.item_name,
            event_id=record.event_id,
            event_name=event.event_name if event else None,
            detail={
                'item_name': record.item_name,
                'amount': float(record.amount or 0),
                'total_amount': float(record.total_amount or 0),
                'has_invoice': record.has_invoice,
                'reimbursed_at': record.reimbursed_at.isoformat() if record.reimbursed_at else None
            }
        )

        return jsonify({
            'code': 200,
            'message': '报销成功',
            'data': None
        }), 200
        
    except Exception as e:
        logger.error(f'报销购买记录异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


@purchase_records_bp.route('/records/<int:record_id>/download-invoice', methods=['GET'])
@jwt_required()
def download_invoice(record_id):
    """下载原始发票文件（PDF或图片）"""
    logger.info(f'=== 下载发票文件: record_id={record_id} ===')
    try:
        current_user_id = get_jwt_identity()
        
        record = PurchaseRecord.query.filter_by(record_id=record_id, is_deleted=False).first()
        if not record:
            return jsonify({'code': 404, 'message': '记录不存在', 'data': None}), 404
        
        invoice_file = _first_invoice_file(record)
        if not invoice_file:
            return jsonify({'code': 404, 'message': '该记录没有发票文件', 'data': None}), 404

        response = _file_download_response(invoice_file['file_key'], invoice_file['original_filename'])
        if response is None:
            logger.error(f'发票文件不存在: {invoice_file["file_key"]}')
            return jsonify({'code': 404, 'message': '文件不存在', 'data': None}), 404

        logger.info(f'发票文件下载成功: {invoice_file["file_key"]}')
        return response
            
    except Exception as e:
        logger.error(f'下载发票文件异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


@purchase_records_bp.route('/records/<int:record_id>/files/<int:file_id>/download', methods=['GET'])
@jwt_required()
def download_record_file(record_id, file_id):
    """下载购买记录附件（多文件场景：购物凭证或发票指定 file_id）"""
    logger.info(f'=== 下载购买记录附件: record_id={record_id}, file_id={file_id} ===')
    try:
        get_jwt_identity()

        record = PurchaseRecord.query.filter_by(record_id=record_id, is_deleted=False).first()
        if not record:
            return jsonify({'code': 404, 'message': '记录不存在', 'data': None}), 404

        record_file = PurchaseRecordFile.query.filter_by(
            file_id=file_id, record_id=record_id
        ).first()
        if not record_file:
            return jsonify({'code': 404, 'message': '附件不存在', 'data': None}), 404

        original_filename = (record_file.original_filename
                             or record_file.file_key.split('/')[-1])
        response = _file_download_response(record_file.file_key, original_filename)
        if response is None:
            logger.error(f'附件文件不存在: {record_file.file_key}')
            return jsonify({'code': 404, 'message': '文件不存在', 'data': None}), 404

        return response

    except Exception as e:
        logger.error(f'下载购买记录附件异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


@purchase_records_bp.route('/records/<int:record_id>/preview-invoice', methods=['GET'])
@jwt_required()
def get_invoice_preview(record_id):
    """获取发票预览图片URL"""
    logger.info(f'=== 获取发票预览URL: record_id={record_id} ===')
    try:
        current_user_id = get_jwt_identity()
        
        record = PurchaseRecord.query.filter_by(record_id=record_id, is_deleted=False).first()
        if not record:
            return jsonify({'code': 404, 'message': '记录不存在', 'data': None}), 404
        
        invoice_file = _first_invoice_file(record)
        if not invoice_file:
            return jsonify({'code': 404, 'message': '该记录没有发票', 'data': None}), 404

        preview_key = invoice_file['preview_key'] or invoice_file['file_key']

        if not invoice_file['preview_key'] and invoice_file['file_key'].lower().endswith('.pdf'):
            # 兼容历史数据：早期上传的 PDF 发票没有预览图，这里按需补生成并落库
            pdf_bytes = _read_file_bytes(invoice_file['file_key'])
            if pdf_bytes:
                jpg_bytes, _, _, _ = PDFConverter.convert_pdf_to_jpg(pdf_bytes)
                if jpg_bytes:
                    generated_key = _store_preview_image(jpg_bytes)
                    if generated_key:
                        _persist_invoice_preview(record, invoice_file['file_key'], generated_key)
                        preview_key = generated_key
                        logger.info(f'历史 PDF 发票预览图已补生成: record_id={record_id}')

        preview_url = get_presigned_url(preview_key, expires=3600)
        
        if not preview_url:
            return jsonify({'code': 500, 'message': '无法生成预览URL', 'data': None}), 500
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'preview_url': preview_url,
                'is_pdf': invoice_file['file_key'].lower().endswith('.pdf')
            }
        }), 200
        
    except Exception as e:
        logger.error(f'获取发票预览URL异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


@purchase_records_bp.route('/records/<int:record_id>/re-parse-invoice', methods=['POST'])
@jwt_required()
def re_parse_invoice(record_id):
    """重新解析已上传的发票文件（使用GLM视觉模型）"""
    logger.info(f'=== 重新解析发票: record_id={record_id} ===')
    try:
        current_user_id = get_jwt_identity()

        record = PurchaseRecord.query.filter_by(record_id=record_id, is_deleted=False).first()
        if not record:
            return jsonify({'code': 404, 'message': '记录不存在', 'data': None}), 404

        invoice_file = _first_invoice_file(record)
        if not invoice_file:
            return jsonify({'code': 400, 'message': '该记录没有发票文件', 'data': None}), 400

        file_key = invoice_file['file_key']
        is_pdf = file_key.lower().endswith('.pdf')
        original_filename = invoice_file['original_filename']

        # 从对象存储或本地下载文件
        file_bytes = _read_file_bytes(file_key)
        if file_bytes:
            logger.info(f'发票文件读取成功: {file_key}')

        if not file_bytes:
            return jsonify({'code': 404, 'message': '无法获取发票文件', 'data': None}), 404

        # PDF文件：先转换为JPG图片再用GLM解析
        image_bytes_for_ai = file_bytes
        jpg_bytes = None
        if is_pdf:
            jpg_bytes, _, _, _ = PDFConverter.convert_pdf_to_jpg(file_bytes)
            if jpg_bytes:
                image_bytes_for_ai = jpg_bytes
                logger.info('PDF转换为JPG成功，使用JPG进行AI解析')
            else:
                logger.warning('PDF转换JPG失败，尝试直接解析')

        # 预览图：与解析结果解耦——只要发票是 PDF 且还没有预览图，就先转图保存
        preview_key = invoice_file.get('preview_key')
        if is_pdf and jpg_bytes and not preview_key:
            preview_key = _store_preview_image(jpg_bytes)
            if preview_key:
                _persist_invoice_preview(record, file_key, preview_key)
                logger.info(f'补生成发票预览图: {preview_key}')
        elif not is_pdf and not preview_key:
            # 图片发票本身即预览图
            preview_key = file_key
            _persist_invoice_preview(record, file_key, preview_key)

        # 调用解析服务
        parsed_info = None
        if invoice_parser.is_available():
            ai_filename = f'{record_id}.jpg' if is_pdf else original_filename
            result = invoice_parser.parse_file(image_bytes_for_ai, ai_filename)

            if result.get('success'):
                logger.info('发票重新解析成功')
                raw_data = result.get('data', {})
                parsed_info = {
                    'item_name': raw_data.get('project_name', '') or raw_data.get('item_name', ''),
                    'invoice_number': raw_data.get('invoice_number', ''),
                    'invoice_tax_number': raw_data.get('invoice_tax_number', '') or raw_data.get('tax_number', ''),
                    'amount': raw_data.get('total_amount', 0) or raw_data.get('amount', 0),
                    'date': raw_data.get('invoice_date', '')
                }
            else:
                logger.warning(f'发票重新解析失败（预览图已保存）: {result.get("message")}')
                return jsonify({
                    'code': 422,
                    'message': result.get('message', '解析失败'),
                    'data': {'preview_key': preview_key}
                }), 422
        else:
            return jsonify({
                'code': 503,
                'message': 'AI解析服务不可用',
                'data': {'preview_key': preview_key}
            }), 503

        return jsonify({
            'code': 200,
            'message': '重新解析成功',
            'data': {
                'parsed_info': parsed_info,
                'preview_key': preview_key,
                'extraction_method': 'glm_vision'
            }
        }), 200

    except Exception as e:
        logger.error(f'重新解析发票异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500
