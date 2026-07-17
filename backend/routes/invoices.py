from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Invoice, Event, User, EventMember
from utils.storage import storage_manager
from datetime import datetime
from routes.events import ensure_event_membership
from models import EventMember, Event
import logging


def _check_student_event_access(event_id: int, user) -> bool:
    """Check if a student user can access (modify) an event. Admin/teacher/student_admin always pass."""
    if user.user_type in ['admin', 'teacher', 'student_admin']:
        return True
    if user.user_type == 'student':
        is_member = EventMember.query.filter_by(
            event_id=event_id, user_id=user.user_id, is_deleted=False
        ).first()
        event = Event.query.get(event_id)
        if event and event.creator_id == user.user_id:
            return True
        return is_member is not None
    return False
import hashlib
import io
import os
import urllib.parse
import tempfile

logger = logging.getLogger(__name__)
invoices_bp = Blueprint('invoices', __name__)


def _log_operation(user_id, username, action_type, action_description, target_type=None, target_id=None, target_name=None, event_id=None, event_name=None, detail=None):
    """记录操作日志"""
    try:
        from utils.operation_log import LogService
        LogService.log(
            user_id=user_id,
            username=username,
            action_type=action_type,
            action_description=action_description,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            event_id=event_id,
            event_name=event_name,
            detail=detail
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f'记录操作日志失败: {str(e)}')


# 字段中文标签（用于操作日志的 description）
INVOICE_FIELD_LABELS = {
    'invoice_type': '发票类型',
    'project_name': '项目名称',
    'amount': '金额',
    'total_amount': '价税合计',
    'invoice_date': '开票日期',
    'invoice_number': '发票号码',
    'remarks': '备注',
}


def _format_invoice_value(field, value):
    """将字段值格式化为人类可读的描述文本片段。"""
    if value is None or value == '':
        return '空'
    if field in ('amount', 'total_amount'):
        try:
            return f'{float(value):.2f}'
        except (TypeError, ValueError):
            return str(value)
    if field == 'invoice_date':
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d')
        try:
            if hasattr(value, 'strftime'):
                return value.strftime('%Y-%m-%d')
        except Exception:
            pass
    if field in ('invoice_type', 'project_name', 'invoice_number', 'remarks'):
        return f'"{value}"'
    return str(value)


def _invoice_values_equal(field, old_value, new_value):
    """比较两个发票字段值是否变更。"""
    if field in ('amount', 'total_amount'):
        try:
            return float(old_value or 0) == float(new_value or 0)
        except (TypeError, ValueError):
            return str(old_value) == str(new_value)
    if field == 'invoice_date':
        old_str = old_value.strftime('%Y-%m-%d') if hasattr(old_value, 'strftime') and old_value else str(old_value or '')
        new_str = str(new_value) if new_value else ''
        return old_str == new_str
    if old_value is None and (new_value is None or new_value == ''):
        return True
    return str(old_value if old_value is not None else '') == str(new_value if new_value is not None else '')


@invoices_bp.route('/invoices', methods=['GET'])
@jwt_required()
def get_invoices():
    logger.info('=== 获取发票列表请求 ===')
    try:
        current_user_id = get_jwt_identity()
        logger.info(f'当前用户ID: {current_user_id}')
        
        event_id = request.args.get('event_id')
        if not event_id:
            logger.warning('缺少event_id参数')
            return jsonify({'code': 400, 'message': '缺少event_id参数', 'data': None}), 400

        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        
        invoices_query = Invoice.query.filter_by(
            event_id=event_id,
            is_deleted=False
        ).order_by(Invoice.created_at.desc())

        uploader_id = request.args.get('uploader_id', type=int)
        if uploader_id:
            invoices_query = invoices_query.filter_by(uploader_id=uploader_id)

        invoices = invoices_query.paginate(
            page=page,
            per_page=page_size,
            error_out=False
        )
        
        invoice_list = []
        for invoice in invoices.items:
            invoice_data = {
                'invoice_id': invoice.invoice_id,
                'event_id': invoice.event_id,
                'uploader_id': invoice.uploader_id,
                'uploader_name': invoice.uploader.real_name if invoice.uploader else None,
                'file_name': invoice.file_name,
                'invoice_type': invoice.invoice_type,
                'invoice_number': invoice.invoice_number,
                'project_name': invoice.project_name,
                'amount': float(invoice.amount),
                'total_amount': float(invoice.total_amount) if invoice.total_amount else float(invoice.amount),
                'invoice_date': invoice.invoice_date.isoformat() if invoice.invoice_date else None,
                'status': invoice.status,
                'reviewer_id': invoice.reviewer_id,
                'reviewer_name': invoice.reviewer.real_name if invoice.reviewer else None,
                'review_time': invoice.review_time.isoformat() if invoice.review_time else None,
                'rejection_reason': invoice.rejection_reason,
                'remarks': invoice.remarks,
                'is_reimbursed': invoice.is_reimbursed,
                'reimbursed_at': invoice.reimbursed_at.isoformat() if invoice.reimbursed_at else None,
                'created_at': invoice.created_at.isoformat() if invoice.created_at else None
            }
            
            if storage_manager.is_available() and invoice.image_url:
                try:
                    invoice_data['image_url'] = storage_manager.get_presigned_url(
                        invoice.image_url,
                        expires=3600
                    )
                except Exception as e:
                    logger.error(f'生成临时URL失败: {str(e)}')
                    invoice_data['image_url'] = None
            else:
                invoice_data['image_url'] = invoice.image_url
            
            invoice_list.append(invoice_data)
        
        logger.info(f'成功获取发票列表，数量: {len(invoice_list)}')
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'data': invoice_list,
                'total': invoices.total,
                'page': page,
                'page_size': page_size,
                'total_pages': invoices.pages
            }
        }), 200
        
    except Exception as e:
        logger.error(f'获取发票列表异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@invoices_bp.route('/invoices', methods=['POST'])
@jwt_required()
def create_invoice():
    logger.info('=== 创建发票请求 ===')
    try:
        current_user_id = get_jwt_identity()
        logger.info(f'当前用户ID: {current_user_id}')
        
        user = User.query.get(current_user_id)
        if not user:
            logger.warning(f'用户不存在: {current_user_id}')
            return jsonify({'code': 401, 'message': '用户不存在', 'data': None}), 401
        
        if 'file' not in request.files:
            logger.warning('未上传文件')
            return jsonify({'code': 400, 'message': '请上传发票图片', 'data': None}), 400
        
        file = request.files['file']
        if file.filename == '':
            logger.warning('文件名为空')
            return jsonify({'code': 400, 'message': '请选择文件', 'data': None}), 400
        
        allowed_extensions = {'pdf', 'png', 'jpg', 'jpeg'}
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if file_ext not in allowed_extensions:
            logger.warning(f'文件格式不支持: {file_ext}')
            return jsonify({
                'code': 400, 
                'message': '文件格式不支持，请上传 PDF、PNG、JPG 或 JPEG 格式的文件', 
                'data': None
            }), 400
        
        event_id = request.form.get('event_id')
        if not event_id:
            logger.warning('缺少event_id参数')
            return jsonify({'code': 400, 'message': '缺少比赛ID', 'data': None}), 400
        
        event = Event.query.filter_by(event_id=event_id, is_deleted=False).first()
        if not event:
            logger.warning(f'比赛不存在: event_id={event_id}')
            return jsonify({'code': 2001, 'message': '比赛不存在', 'data': None}), 404
        
        # Always compute MD5 and check for duplicates (BUG-04 fix)
        file_content = file.read()
        file_md5 = hashlib.md5(file_content).hexdigest()
        file.seek(0)

        existing_invoice = Invoice.query.filter_by(
            event_id=int(event_id),
            file_md5=file_md5,
            is_deleted=False
        ).first()

        if existing_invoice:
            logger.warning(f'检测到重复上传: MD5={file_md5}, 已存在发票ID={existing_invoice.invoice_id}')
            return jsonify({
                'code': 4001,
                'message': '该发票文件已经上传过，请勿重复提交',
                'data': {
                    'existing_invoice_id': existing_invoice.invoice_id,
                    'upload_time': existing_invoice.created_at.isoformat() if existing_invoice.created_at else None
                }
            }), 400

        # 检查学生是否有权限访问该项目
        if not _check_student_event_access(int(event_id), user):
            return jsonify({'code': 403, 'message': '您未加入该项目，无法上传发票', 'data': None}), 403

        # 自动检查并添加赛事成员
        ensure_event_membership(int(event_id), int(current_user_id))

        if storage_manager.is_available():
            upload_result = storage_manager.upload_file(int(event_id), file, file.filename)
            image_url = upload_result['file_key']
            logger.info(f'文件上传成功: {image_url}')
        else:
            image_url = f'/uploads/{file.filename}'
            logger.warning('COS服务不可用，使用本地存储')
        
        from decimal import Decimal
        
        invoice = Invoice(
            event_id=int(event_id),
            uploader_id=int(current_user_id),
            file_name=file.filename,
            file_md5=file_md5,
            image_url=image_url,
            invoice_type=request.form.get('invoice_type'),
            invoice_number=request.form.get('invoice_number'),
            project_name=request.form.get('project_name'),
            amount=Decimal(str(request.form.get('amount', 0))),
            total_amount=Decimal(str(request.form.get('total_amount', request.form.get('amount', 0)))),
            invoice_date=datetime.strptime(request.form.get('invoice_date'), '%Y-%m-%d') if request.form.get('invoice_date') else None,
            status='approved',
            remarks=request.form.get('remarks')
        )
        
        invoice.reviewer_id = current_user_id
        invoice.review_time = datetime.utcnow()
        
        db.session.add(invoice)
        
        event.invoice_count += 1
        event.invoice_total_amount += invoice.amount
        
        db.session.commit()

        _log_operation(
            user_id=int(current_user_id),
            username=user.username,
            action_type='create_invoice',
            action_description=f'上传发票「{invoice.invoice_number or invoice.file_name}」，项目「{invoice.project_name or event.event_name}」',
            target_type='invoice',
            target_id=invoice.invoice_id,
            target_name=invoice.invoice_number or invoice.file_name,
            event_id=event.event_id,
            event_name=event.event_name,
            detail={
                'file_name': invoice.file_name,
                'invoice_number': invoice.invoice_number,
                'project_name': invoice.project_name,
                'amount': float(invoice.amount)
            }
        )
        
        logger.info(f'发票创建成功: invoice_id={invoice.invoice_id}')
        
        return jsonify({
            'code': 200,
            'message': '发票上传成功',
            'data': {
                'invoice_id': invoice.invoice_id,
                'file_name': invoice.file_name,
                'image_url': storage_manager.get_presigned_url(image_url) if storage_manager.is_available() and image_url else image_url
            }
        }), 200
        
    except Exception as e:
        logger.error(f'创建发票异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@invoices_bp.route('/invoices/<int:invoice_id>', methods=['DELETE'])
@jwt_required()
def delete_invoice(invoice_id):
    logger.info(f'=== 删除发票请求: invoice_id={invoice_id} ===')
    try:
        current_user_id = get_jwt_identity()
        logger.info(f'当前用户ID: {current_user_id}')
        
        user = User.query.get(current_user_id)
        if not user:
            logger.warning(f'用户不存在: {current_user_id}')
            return jsonify({'code': 401, 'message': '用户不存在', 'data': None}), 401
        
        invoice = Invoice.query.filter_by(invoice_id=invoice_id, is_deleted=False).first()
        
        if not invoice:
            logger.warning(f'发票不存在: invoice_id={invoice_id}')
            return jsonify({'code': 3001, 'message': '发票不存在', 'data': None}), 404
        
        if user.user_type not in ['admin', 'teacher'] and invoice.uploader_id != int(current_user_id):
            logger.warning(f'权限不足: 用户{current_user_id}无权删除发票{invoice_id}')
            return jsonify({'code': 403, 'message': '权限不足', 'data': None}), 403

        # 学生权限检查：必须是项目成员
        if not _check_student_event_access(invoice.event_id, user):
            return jsonify({'code': 403, 'message': '您未加入该项目，无法删除发票', 'data': None}), 403

        # 自动检查并添加赛事成员（特权用户）
        if user.user_type in ['admin', 'teacher']:
            ensure_event_membership(invoice.event_id, int(current_user_id))

        event = Event.query.get(invoice.event_id)
        
        invoice.is_deleted = True
        
        if event:
            event.invoice_count = max(0, event.invoice_count - 1)
            event.invoice_total_amount = max(0, event.invoice_total_amount - invoice.amount)
        
        if storage_manager.is_available() and invoice.image_url:
            storage_manager.delete_file(invoice.image_url)
        
        db.session.commit()

        _log_operation(
            user_id=int(current_user_id),
            username=user.username,
            action_type='delete_invoice',
            action_description=f'删除发票「{invoice.invoice_number or invoice.file_name}」，项目「{invoice.project_name or (event.event_name if event else "未知项目")}」',
            target_type='invoice',
            target_id=invoice_id,
            target_name=invoice.invoice_number or invoice.file_name,
            event_id=invoice.event_id,
            event_name=event.event_name if event else None,
            detail={
                'file_name': invoice.file_name,
                'invoice_number': invoice.invoice_number,
                'project_name': invoice.project_name,
                'amount': float(invoice.amount)
            }
        )
        
        logger.info(f'发票删除成功: invoice_id={invoice_id}')
        return jsonify({
            'code': 200,
            'message': '发票删除成功',
            'data': None
        }), 200
        
    except Exception as e:
        logger.error(f'删除发票异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@invoices_bp.route('/invoices/<int:invoice_id>/approve', methods=['POST'])
@jwt_required()
def approve_invoice(invoice_id):
    logger.info(f'=== 审批发票请求: invoice_id={invoice_id} ===')
    try:
        current_user_id = get_jwt_identity()
        logger.info(f'当前用户ID: {current_user_id}')
        
        user = User.query.get(current_user_id)
        if not user:
            logger.warning(f'用户不存在: {current_user_id}')
            return jsonify({'code': 401, 'message': '用户不存在', 'data': None}), 401
        
        if user.user_type not in ['admin', 'teacher', 'student_admin']:
            logger.warning(f'权限不足: 用户类型={user.user_type}')
            return jsonify({'code': 403, 'message': '权限不足，只有管理员、教师或学生管理员可以审核发票', 'data': None}), 403
        
        invoice = Invoice.query.filter_by(invoice_id=invoice_id, is_deleted=False).first()

        if not invoice:
            logger.warning(f'发票不存在: invoice_id={invoice_id}')
            return jsonify({'code': 3001, 'message': '发票不存在', 'data': None}), 404

        # 自动检查并添加赛事成员
        ensure_event_membership(invoice.event_id, int(current_user_id))

        data = request.get_json()
        status = data.get('status')
        rejection_reason = data.get('rejection_reason')
        
        if status not in ['approved', 'rejected']:
            logger.warning(f'无效的状态: {status}')
            return jsonify({'code': 400, 'message': '无效的审核状态', 'data': None}), 400
        
        if status == 'rejected' and not rejection_reason:
            logger.warning('缺少拒绝原因')
            return jsonify({'code': 400, 'message': '拒绝时必须填写拒绝原因', 'data': None}), 400
        
        invoice.status = status
        invoice.reviewer_id = int(current_user_id)
        invoice.review_time = datetime.utcnow()
        invoice.rejection_reason = rejection_reason
        
        if status == 'approved':
            event = Event.query.get(invoice.event_id)
            if event:
                event.reimbursed_amount += invoice.amount
                event.remaining_budget = event.total_budget - event.reimbursed_amount
        
        db.session.commit()

        event = Event.query.get(invoice.event_id)
        action_type = 'approve_invoice' if status == 'approved' else 'reject_invoice'
        action_name = '审批通过' if status == 'approved' else '拒绝'
        _log_operation(
            user_id=int(current_user_id),
            username=user.username,
            action_type=action_type,
            action_description=f'{action_name}发票「{invoice.invoice_number or invoice.file_name}」，项目「{invoice.project_name or (event.event_name if event else "未知项目")}」',
            target_type='invoice',
            target_id=invoice_id,
            target_name=invoice.invoice_number or invoice.file_name,
            event_id=invoice.event_id,
            event_name=event.event_name if event else None,
            detail={
                'status': status,
                'rejection_reason': rejection_reason,
                'invoice_number': invoice.invoice_number,
                'project_name': invoice.project_name,
                'amount': float(invoice.amount)
            }
        )
        
        logger.info(f'发票审核成功: invoice_id={invoice_id}, status={status}')
        return jsonify({
            'code': 200,
            'message': '审核成功',
            'data': None
        }), 200
        
    except Exception as e:
        logger.error(f'审核发票异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@invoices_bp.route('/invoices/<int:invoice_id>/preview', methods=['GET'])
@jwt_required()
def get_preview(invoice_id):
    logger.info(f'=== 获取发票预览图: invoice_id={invoice_id} ===')
    try:
        invoice = Invoice.query.filter_by(invoice_id=invoice_id, is_deleted=False).first()
        
        if not invoice:
            logger.warning(f'发票不存在: invoice_id={invoice_id}')
            return jsonify({'code': 3001, 'message': '发票不存在', 'data': None}), 404
        
        preview_url = None
        if invoice.preview_image_url:
            if storage_manager.is_available():
                try:
                    preview_url = storage_manager.get_presigned_url(
                        invoice.preview_image_url,
                        expires=3600
                    )
                except Exception as e:
                    logger.error(f'生成预览图临时URL失败: {str(e)}')
                    preview_url = invoice.preview_image_url
            else:
                preview_url = invoice.preview_image_url
        
        logger.info(f'获取预览图成功: has_preview={bool(preview_url)}')
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'preview_url': preview_url,
                'has_preview': bool(preview_url)
            }
        }), 200
        
    except Exception as e:
        logger.error(f'获取预览图异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@invoices_bp.route('/invoices/<int:invoice_id>/generate-preview', methods=['POST'])
@jwt_required()
def generate_preview(invoice_id):
    logger.info(f'=== 生成预览图: invoice_id={invoice_id} ===')
    try:
        invoice = Invoice.query.filter_by(invoice_id=invoice_id, is_deleted=False).first()
        
        if not invoice:
            logger.warning(f'发票不存在: invoice_id={invoice_id}')
            return jsonify({'code': 3001, 'message': '发票不存在', 'data': None}), 404
        
        if not invoice.image_url:
            logger.warning(f'发票没有文件: invoice_id={invoice_id}')
            return jsonify({'code': 400, 'message': '发票没有关联的文件', 'data': None}), 400
        
        file_ext = invoice.file_name.rsplit('.', 1)[1].lower() if '.' in invoice.file_name else ''
        
        if file_ext == 'pdf':
            if storage_manager.is_available():
                try:
                    preview_url = storage_manager.get_presigned_url(invoice.image_url, expires=3600)
                except Exception as e:
                    logger.error(f'生成PDF预览URL失败: {str(e)}')
                    preview_url = invoice.image_url
            else:
                preview_url = invoice.image_url

            invoice.preview_image_url = invoice.image_url
            db.session.commit()

            logger.info(f'PDF预览设置成功: invoice_id={invoice_id}')
            return jsonify({
                'code': 200,
                'message': 'PDF文件直接作为预览',
                'data': {
                    'preview_url': preview_url
                }
            }), 200
            
        elif file_ext in ['png', 'jpg', 'jpeg']:
            if storage_manager.is_available():
                try:
                    preview_url = storage_manager.get_presigned_url(invoice.image_url, expires=3600)
                except Exception as e:
                    logger.error(f'生成图片预览URL失败: {str(e)}')
                    preview_url = invoice.image_url
                
                invoice.preview_image_url = invoice.image_url
                db.session.commit()
                
                return jsonify({
                    'code': 200,
                    'message': '图片格式发票，直接使用原图',
                    'data': {
                        'preview_url': preview_url
                    }
                }), 200
            else:
                return jsonify({
                    'code': 200,
                    'message': '图片格式发票，直接使用原图',
                    'data': {
                        'preview_url': invoice.image_url
                    }
                }), 200
        else:
            return jsonify({'code': 400, 'message': '不支持的文件格式', 'data': None}), 400
            
    except Exception as e:
        logger.error(f'生成预览图异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@invoices_bp.route('/invoices/<int:invoice_id>/download', methods=['GET'])
@jwt_required()
def download_invoice(invoice_id):
    logger.info(f'=== 下载发票文件: invoice_id={invoice_id} ===')
    try:
        invoice = Invoice.query.filter_by(invoice_id=invoice_id, is_deleted=False).first()
        
        if not invoice:
            logger.warning(f'发票不存在: invoice_id={invoice_id}')
            return jsonify({'code': 3001, 'message': '发票不存在', 'data': None}), 404
        
        if not invoice.image_url:
            logger.warning(f'发票没有文件: invoice_id={invoice_id}')
            return jsonify({'code': 400, 'message': '发票没有关联的文件', 'data': None}), 400
        
        if storage_manager.is_available():
            file_content = storage_manager.download_file(invoice.image_url)
            
            if not file_content:
                logger.error(f'无法下载文件: {invoice.image_url}')
                return jsonify({'code': 500, 'message': '无法获取文件', 'data': None}), 500
            
            file_obj = io.BytesIO(file_content)
            
            from flask import Response
            safe_filename = urllib.parse.quote(invoice.file_name)
            response = Response(
                file_content,
                mimetype='application/octet-stream',
                headers={
                    'Content-Disposition': f"attachment; filename*=UTF-8''{safe_filename}"
                }
            )
            return response
        else:
            local_path = invoice.image_url.lstrip('/')
            if not os.path.exists(local_path):
                logger.error(f'本地文件不存在: {local_path}')
                return jsonify({'code': 500, 'message': '文件不存在', 'data': None}), 500
            
            return send_file(
                local_path,
                as_attachment=True,
                download_name=invoice.file_name
            )
            
    except Exception as e:
        logger.error(f'下载发票异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@invoices_bp.route('/invoices/<int:invoice_id>', methods=['PUT'])
@jwt_required()
def update_invoice(invoice_id):
    logger.info(f'=== 更新发票信息: invoice_id={invoice_id} ===')
    try:
        current_user_id = get_jwt_identity()
        logger.info(f'当前用户ID: {current_user_id}')
        
        user = User.query.get(current_user_id)
        if not user:
            logger.warning(f'用户不存在: {current_user_id}')
            return jsonify({'code': 401, 'message': '用户不存在', 'data': None}), 401
        
        invoice = Invoice.query.filter_by(invoice_id=invoice_id, is_deleted=False).first()
        
        if not invoice:
            logger.warning(f'发票不存在: invoice_id={invoice_id}')
            return jsonify({'code': 3001, 'message': '发票不存在', 'data': None}), 404
        
        data = request.get_json()
        logger.info(f'更新数据: {data}')

        from decimal import Decimal

        # 在 commit 前获取旧值，用于日志记录变更详情
        old_invoice_type = invoice.invoice_type
        old_project_name = invoice.project_name
        old_amount = float(invoice.amount) if invoice.amount is not None else None
        old_invoice_date = invoice.invoice_date
        old_invoice_number = invoice.invoice_number
        old_remarks = invoice.remarks

        if 'invoice_type' in data:
            invoice.invoice_type = data['invoice_type']
        if 'project_name' in data and data['project_name']:
            invoice.project_name = data['project_name']
        if 'amount' in data:
            new_amount = Decimal(str(data['amount']))
            old_amount_dec = invoice.amount
            event = Event.query.get(invoice.event_id)
            if event:
                event.invoice_total_amount = event.invoice_total_amount - old_amount_dec + new_amount
                if invoice.status == 'approved':
                    event.reimbursed_amount = event.reimbursed_amount - old_amount_dec + new_amount
                    event.remaining_budget = event.total_budget - event.reimbursed_amount
            invoice.amount = new_amount
        if 'invoice_date' in data and data['invoice_date']:
            invoice.invoice_date = datetime.strptime(data['invoice_date'], '%Y-%m-%d').date()
        if 'invoice_number' in data:
            invoice.invoice_number = data['invoice_number']
        if 'remarks' in data:
            invoice.remarks = data['remarks']

        # 在 commit 前构造变更字典
        changes = {}
        if 'invoice_type' in data and not _invoice_values_equal('invoice_type', old_invoice_type, data['invoice_type']):
            changes['invoice_type'] = {'old': old_invoice_type, 'new': data['invoice_type']}
        if 'project_name' in data and not _invoice_values_equal('project_name', old_project_name, data['project_name']):
            changes['project_name'] = {'old': old_project_name, 'new': data['project_name']}
        if 'amount' in data:
            try:
                new_amount_val = float(Decimal(str(data['amount'])))
            except Exception:
                new_amount_val = data['amount']
            if not _invoice_values_equal('amount', old_amount, new_amount_val):
                changes['amount'] = {'old': old_amount, 'new': new_amount_val}
        if 'invoice_date' in data and data['invoice_date']:
            new_date = datetime.strptime(data['invoice_date'], '%Y-%m-%d').date()
            if not _invoice_values_equal('invoice_date', old_invoice_date, new_date):
                changes['invoice_date'] = {'old': old_invoice_date, 'new': new_date}
        if 'invoice_number' in data and not _invoice_values_equal('invoice_number', old_invoice_number, data['invoice_number']):
            changes['invoice_number'] = {'old': old_invoice_number, 'new': data['invoice_number']}
        if 'remarks' in data and not _invoice_values_equal('remarks', old_remarks, data['remarks']):
            changes['remarks'] = {'old': old_remarks, 'new': data['remarks']}

        # 构造 action_description（在 commit 前完成）
        event = Event.query.get(invoice.event_id)
        target_name = invoice.invoice_number or invoice.file_name
        event_name_str = event.event_name if event else '未知项目'
        if changes:
            change_parts = []
            for field in ['invoice_type', 'project_name', 'amount', 'total_amount',
                          'invoice_date', 'invoice_number', 'remarks']:
                if field in changes:
                    label = INVOICE_FIELD_LABELS.get(field, field)
                    old_part = _format_invoice_value(field, changes[field]['old'])
                    new_part = _format_invoice_value(field, changes[field]['new'])
                    change_parts.append(f'{label} {old_part}→{new_part}')
            change_text = '、'.join(change_parts)
            action_desc = f'修改发票「{target_name}」，项目「{invoice.project_name or event_name_str}」: {change_text}'
        else:
            action_desc = f'修改发票「{target_name}」，项目「{invoice.project_name or event_name_str}」'

        db.session.commit()

        _log_operation(
            user_id=int(current_user_id),
            username=user.username,
            action_type='update_invoice',
            action_description=action_desc,
            target_type='invoice',
            target_id=invoice_id,
            target_name=target_name,
            event_id=invoice.event_id,
            event_name=event_name_str if event else None,
            detail={'changes': changes}
        )
        
        logger.info(f'发票更新成功: invoice_id={invoice_id}')
        return jsonify({
            'code': 200,
            'message': '发票信息更新成功',
            'data': None
        }), 200
        
    except Exception as e:
        logger.error(f'更新发票异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@invoices_bp.route('/invoices/batch-reimburse', methods=['POST'])
@jwt_required()
def batch_reimburse_invoices():
    logger.info('=== 批量报销发票 ===')
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or user.user_type not in ['admin', 'teacher']:
            return jsonify({'code': 403, 'message': '权限不足', 'data': None}), 403
        
        data = request.get_json()
        invoice_ids = data.get('invoice_ids', [])
        
        if not invoice_ids:
            return jsonify({'code': 400, 'message': '请选择要报销的发票', 'data': None}), 400
        
        count = 0
        reimbursed_invoices = []
        for iid in invoice_ids:
            invoice = Invoice.query.filter_by(invoice_id=iid, is_deleted=False).first()
            if invoice and invoice.status == 'approved' and not invoice.is_reimbursed:
                invoice.is_reimbursed = True
                invoice.reimbursed_at = datetime.utcnow()
                
                event = Event.query.get(invoice.event_id)
                if event:
                    event.reimbursed_amount += invoice.amount
                    event.remaining_budget = event.total_budget - event.reimbursed_amount
                
                reimbursed_invoices.append({
                    'invoice_id': invoice.invoice_id,
                    'invoice_number': invoice.invoice_number,
                    'file_name': invoice.file_name,
                    'project_name': invoice.project_name,
                    'event_id': invoice.event_id,
                    'event_name': event.event_name if event else None,
                    'amount': float(invoice.amount)
                })
                count += 1
        
        db.session.commit()

        event_ids = {item['event_id'] for item in reimbursed_invoices}
        event_names = sorted({
            item['event_name'] for item in reimbursed_invoices if item['event_name']
        })
        invoice_names = [
            item['invoice_number'] or item['file_name'] for item in reimbursed_invoices
        ]
        invoice_summary = f'「{"、".join(invoice_names)}」' if invoice_names else ''
        _log_operation(
            user_id=int(current_user_id),
            username=user.username,
            action_type='batch_reimburse_invoices',
            action_description=f'批量报销 {count} 张发票{invoice_summary}' + (f'，项目「{"、".join(event_names)}」' if event_names else ''),
            target_type='invoice',
            event_id=next(iter(event_ids)) if len(event_ids) == 1 else None,
            event_name=event_names[0] if len(event_names) == 1 else None,
            detail={
                'requested_invoice_ids': invoice_ids,
                'reimbursed_count': count,
                'invoices': reimbursed_invoices
            }
        )
        
        return jsonify({
            'code': 200,
            'message': f'成功报销 {count} 张发票',
            'data': {'count': count}
        }), 200
        
    except Exception as e:
        logger.error(f'批量报销发票异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@invoices_bp.route('/invoices/<int:invoice_id>/reimburse', methods=['POST'])
@jwt_required()
def reimburse_invoice(invoice_id):
    logger.info(f'=== 报销发票: invoice_id={invoice_id} ===')
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or user.user_type not in ['admin', 'teacher']:
            return jsonify({'code': 403, 'message': '权限不足', 'data': None}), 403

        invoice = Invoice.query.filter_by(invoice_id=invoice_id, is_deleted=False).first()
        if not invoice:
            return jsonify({'code': 3001, 'message': '发票不存在', 'data': None}), 404

        # 自动检查并添加赛事成员
        ensure_event_membership(invoice.event_id, int(current_user_id))

        if invoice.status != 'approved':
            return jsonify({'code': 400, 'message': '只能报销已审核通过的发票', 'data': None}), 400
        
        if invoice.is_reimbursed:
            return jsonify({'code': 400, 'message': '该发票已报销', 'data': None}), 400
        
        invoice.is_reimbursed = True
        invoice.reimbursed_at = datetime.utcnow()
        
        event = Event.query.get(invoice.event_id)
        if event:
            event.reimbursed_amount += invoice.amount
            event.remaining_budget = event.total_budget - event.reimbursed_amount
        
        db.session.commit()

        _log_operation(
            user_id=int(current_user_id),
            username=user.username,
            action_type='reimburse_invoice',
            action_description=f'报销发票「{invoice.invoice_number or invoice.file_name}」，项目「{invoice.project_name or (event.event_name if event else "未知项目")}」',
            target_type='invoice',
            target_id=invoice_id,
            target_name=invoice.invoice_number or invoice.file_name,
            event_id=invoice.event_id,
            event_name=event.event_name if event else None,
            detail={
                'invoice_number': invoice.invoice_number,
                'project_name': invoice.project_name,
                'amount': float(invoice.amount),
                'reimbursed_at': invoice.reimbursed_at.isoformat() if invoice.reimbursed_at else None
            }
        )
        
        return jsonify({
            'code': 200,
            'message': '发票报销成功',
            'data': None
        }), 200
        
    except Exception as e:
        logger.error(f'报销发票异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500
