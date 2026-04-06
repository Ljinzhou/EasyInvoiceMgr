from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, PurchaseRecord, Event, User
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)
purchase_records_bp = Blueprint('purchase_records', __name__)

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
        
        records = PurchaseRecord.query.filter_by(
            event_id=event_id, 
            is_deleted=False
        ).order_by(PurchaseRecord.created_at.desc()).all()
        
        records_data = []
        for record in records:
            uploader = User.query.get(record.uploader_id)
            reviewer = User.query.get(record.reviewer_id) if record.reviewer_id else None
            
            records_data.append({
                'record_id': record.record_id,
                'event_id': record.event_id,
                'item_name': record.item_name,
                'purchase_platform': record.purchase_platform,
                'purchase_date': record.purchase_date.isoformat() if record.purchase_date else None,
                'amount': float(record.amount),
                'receipt_image_url': record.receipt_image_url,
                'receipt_image_name': record.receipt_image_name,
                'has_invoice': record.has_invoice,
                'invoice_url': record.invoice_url,
                'invoice_type': record.invoice_type,
                'invoice_number': record.invoice_number,
                'total_amount': float(record.total_amount) if record.total_amount else 0,
                'invoice_date': record.invoice_date.isoformat() if record.invoice_date else None,
                'status': record.status,
                'is_reimbursed': record.is_reimbursed,
                'remarks': record.remarks,
                'uploader_id': record.uploader_id,
                'uploader_name': uploader.real_name if uploader else None,
                'reviewer_name': reviewer.real_name if reviewer else None,
                'created_at': record.created_at.isoformat() if record.created_at else None,
                'rejection_reason': record.rejection_reason
            })
        
        total_amount = sum(r['amount'] for r in records_data)
        invoice_total = sum(r['total_amount'] for r in records_data if r['has_invoice'])
        pending_reimburse = sum(r['total_amount'] for r in records_data if r['has_invoice'] and not r['is_reimbursed'])
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'records': records_data,
                'total_count': len(records_data),
                'total_amount': str(total_amount),
                'invoice_total': str(invoice_total),
                'pending_reimburse': str(pending_reimburse)
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
        
        if 'receipt_image_url' not in data or not data['receipt_image_url']:
            return jsonify({'code': 400, 'message': '必须上传购物凭证图片', 'data': None}), 400
        
        record = PurchaseRecord(
            event_id=event_id,
            uploader_id=current_user_id,
            item_name=data['item_name'],
            purchase_platform=data['purchase_platform'],
            purchase_date=datetime.strptime(data['purchase_date'], '%Y-%m-%d').date() if isinstance(data['purchase_date'], str) else data['purchase_date'],
            amount=float(data['amount']) if data.get('amount') is not None else 0.0,
            receipt_image_url=data['receipt_image_url'],
            receipt_image_name=data.get('receipt_image_name'),
            receipt_file_md5=data.get('receipt_file_md5'),
            has_invoice=bool(data.get('invoice_url')),
            invoice_url=data.get('invoice_url'),
            invoice_name=data.get('invoice_name'),
            invoice_md5=data.get('invoice_md5'),
            invoice_preview_url=data.get('invoice_preview_url'),
            invoice_type=data.get('invoice_type'),
            invoice_number=data.get('invoice_number'),
            total_amount=float(data.get('total_amount')) if data.get('total_amount') is not None else 0.0,
            invoice_date=datetime.strptime(data['invoice_date'], '%Y-%m-%d').date() if data.get('invoice_date') else None,
            remarks=data.get('remarks')
        )
        
        db.session.add(record)
        db.session.commit()
        
        logger.info(f'购买记录创建成功: record_id={record.record_id}')
        
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
        
        if 'item_name' in data:
            record.item_name = data['item_name']
        if 'purchase_platform' in data:
            record.purchase_platform = data['purchase_platform']
        if 'purchase_date' in data:
            record.purchase_date = datetime.strptime(data['purchase_date'], '%Y-%m-%d').date() if isinstance(data['purchase_date'], str) else data['purchase_date']
        if 'amount' in data:
            record.amount = float(data['amount'])
        if 'receipt_image_url' in data:
            record.receipt_image_url = data['receipt_image_url']
        if 'receipt_image_name' in data:
            record.receipt_image_name = data['receipt_image_name']
        
        if 'invoice_url' in data:
            has_invoice = bool(data['invoice_url'])
            record.has_invoice = has_invoice
            record.invoice_url = data['invoice_url'] if has_invoice else None
            
        if 'invoice_name' in data:
            record.invoice_name = data['invoice_name']
        if 'invoice_md5' in data:
            record.invoice_md5 = data['invoice_md5']
        if 'invoice_preview_url' in data:
            record.invoice_preview_url = data['invoice_preview_url']
        if 'invoice_type' in data:
            record.invoice_type = data['invoice_type']
        if 'invoice_number' in data:
            record.invoice_number = data['invoice_number']
        if 'total_amount' in data:
            record.total_amount = float(data['total_amount']) if data['total_amount'] else 0
        if 'invoice_date' in data:
            record.invoice_date = datetime.strptime(data['invoice_date'], '%Y-%m-%d').date() if isinstance(data['invoice_date'], str) else data['invoice_date']
        if 'remarks' in data:
            record.remarks = data['remarks']
        
        db.session.commit()
        
        logger.info(f'购买记录更新成功: record_id={record_id}')
        
        return jsonify({
            'code': 200,
            'message': '更新成功',
            'data': {'record_id': record_id}
        }), 200
        
    except Exception as e:
        logger.error(f'更新购买记录异常: {str(e)}', exc_info=True)
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
        
        record.is_deleted = True
        db.session.commit()
        
        logger.info(f'购买记录删除成功: record_id={record_id}')
        
        return jsonify({
            'code': 200,
            'message': '删除成功',
            'data': None
        }), 200
        
    except Exception as e:
        logger.error(f'删除购买记录异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@purchase_records_bp.route('/records/<int:record_id>/approve', methods=['POST'])
@jwt_required()
def approve_purchase_record(record_id):
    logger.info(f'=== 审核购买记录: record_id={record_id} ===')
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or user.user_type not in ['admin', 'teacher', 'student_admin']:
            return jsonify({'code': 403, 'message': '权限不足', 'data': None}), 403
        
        record = PurchaseRecord.query.filter_by(record_id=record_id, is_deleted=False).first()
        if not record:
            return jsonify({'code': 404, 'message': '记录不存在', 'data': None}), 404
        
        data = request.get_json()
        status = data.get('status')
        rejection_reason = data.get('rejection_reason')
        
        if status not in ['approved', 'rejected']:
            return jsonify({'code': 400, 'message': '无效的状态', 'data': None}), 400
        
        if status == 'rejected' and not rejection_reason:
            return jsonify({'code': 400, 'message': '拒绝时必须填写原因', 'data': None}), 400
        
        record.status = status
        record.reviewer_id = int(current_user_id)
        record.review_time = datetime.utcnow()
        record.rejection_reason = rejection_reason if status == 'rejected' else None
        
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': f'{"审核通过" if status == "approved" else "已拒绝"}',
            'data': None
        }), 200
        
    except Exception as e:
        logger.error(f'审核购买记录异常: {str(e)}', exc_info=True)
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
        
        if not record.has_invoice:
            return jsonify({'code': 400, 'message': '该记录没有发票，无法报销', 'data': None}), 400
        
        if record.is_reimbursed:
            return jsonify({'code': 400, 'message': '该记录已经报销过了', 'data': None}), 400
        
        record.is_reimbursed = True
        record.reimbursed_at = datetime.utcnow()
        
        event = Event.query.get(record.event_id)
        if event:
            event.reimbursed_amount += record.total_amount or record.amount
            event.remaining_budget = event.total_budget - event.reimbursed_amount
        
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '报销成功',
            'data': None
        }), 200
        
    except Exception as e:
        logger.error(f'报销购买记录异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@purchase_records_bp.route('/records/<int:record_id>/download', methods=['GET'])
@jwt_required()
def download_purchase_record(record_id):
    logger.info(f'=== 下载购买记录文件: record_id={record_id} ===')
    try:
        record = PurchaseRecord.query.filter_by(record_id=record_id, is_deleted=False).first()
        if not record:
            return jsonify({'code': 404, 'message': '记录不存在', 'data': None}), 404
        
        files = []
        if record.receipt_image_url:
            files.append({
                'name': record.receipt_image_name or '购物凭证',
                'url': record.receipt_image_url,
                'type': 'receipt'
            })
        if record.invoice_url:
            files.append({
                'name': record.invoice_name or '发票文件',
                'url': record.invoice_url,
                'type': 'invoice'
            })
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'record_id': record_id,
                'files': files
            }
        }), 200
        
    except Exception as e:
        logger.error(f'下载购买记录异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500
