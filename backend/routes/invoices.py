from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Invoice, Event, User, EventMember
from utils.storage import storage_manager
from datetime import datetime
import logging
import hashlib
import io
import os
import urllib.parse
import tempfile

logger = logging.getLogger(__name__)
invoices_bp = Blueprint('invoices', __name__)

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

        # Check event membership for non-admin/teacher users
        user = User.query.get(current_user_id)
        if user and user.user_type not in ['admin', 'teacher']:
            event = Event.query.filter_by(event_id=event_id, is_deleted=False).first()
            if event:
                is_member = EventMember.query.filter_by(
                    event_id=event_id, user_id=current_user_id, is_deleted=False
                ).first()
                if event.creator_id != current_user_id and not is_member:
                    return jsonify({'code': 403, 'message': '无权访问该项目', 'data': None}), 403

        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        
        invoices = Invoice.query.filter_by(
            event_id=event_id,
            is_deleted=False
        ).order_by(Invoice.created_at.desc()).paginate(
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
            status='approved' if not event.need_invoice_review else 'pending',
            remarks=request.form.get('remarks')
        )
        
        if not event.need_invoice_review:
            invoice.reviewer_id = current_user_id
            invoice.review_time = datetime.utcnow()
        
        db.session.add(invoice)
        
        event.invoice_count += 1
        event.invoice_total_amount += invoice.amount
        
        db.session.commit()
        
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
        
        event = Event.query.get(invoice.event_id)
        
        invoice.is_deleted = True
        
        if event:
            event.invoice_count = max(0, event.invoice_count - 1)
            event.invoice_total_amount = max(0, event.invoice_total_amount - invoice.amount)
        
        if storage_manager.is_available() and invoice.image_url:
            storage_manager.delete_file(invoice.image_url)
        
        db.session.commit()
        
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
        
        if 'invoice_type' in data:
            invoice.invoice_type = data['invoice_type']
        if 'project_name' in data and data['project_name']:
            invoice.project_name = data['project_name']
        if 'amount' in data:
            new_amount = Decimal(str(data['amount']))
            old_amount = invoice.amount
            event = Event.query.get(invoice.event_id)
            if event:
                event.invoice_total_amount = event.invoice_total_amount - old_amount + new_amount
                if invoice.status == 'approved':
                    event.reimbursed_amount = event.reimbursed_amount - old_amount + new_amount
                    event.remaining_budget = event.total_budget - event.reimbursed_amount
            invoice.amount = new_amount
        if 'invoice_date' in data and data['invoice_date']:
            invoice.invoice_date = datetime.strptime(data['invoice_date'], '%Y-%m-%d').date()
        if 'invoice_number' in data:
            invoice.invoice_number = data['invoice_number']
        if 'remarks' in data:
            invoice.remarks = data['remarks']
        
        db.session.commit()
        
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
        for iid in invoice_ids:
            invoice = Invoice.query.filter_by(invoice_id=iid, is_deleted=False).first()
            if invoice and invoice.status == 'approved' and not invoice.is_reimbursed:
                invoice.is_reimbursed = True
                invoice.reimbursed_at = datetime.utcnow()
                
                event = Event.query.get(invoice.event_id)
                if event:
                    event.reimbursed_amount += invoice.amount
                    event.remaining_budget = event.total_budget - event.reimbursed_amount
                
                count += 1
        
        db.session.commit()
        
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
        
        return jsonify({
            'code': 200,
            'message': '发票报销成功',
            'data': None
        }), 200
        
    except Exception as e:
        logger.error(f'报销发票异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500
