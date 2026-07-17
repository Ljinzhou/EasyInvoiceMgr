from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Voucher, Event, User, EventMember
from utils.storage import storage_manager
from datetime import datetime
import logging
import hashlib
import urllib.parse

logger = logging.getLogger(__name__)
vouchers_bp = Blueprint('vouchers', __name__)


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
        logger.warning(f'记录操作日志失败: {str(e)}')


# 字段中文标签（用于操作日志的 description）
VOUCHER_FIELD_LABELS = {
    'item_name': '物品名称',
    'voucher_type': '凭证类型',
    'purchase_channel': '购买渠道',
    'purchase_date': '购入日期',
    'amount': '金额',
    'remarks': '备注',
}


def _format_voucher_value(field, value):
    """将字段值格式化为人类可读的描述文本片段。"""
    if value is None or value == '':
        return '空'
    if field == 'amount':
        try:
            return f'{float(value):.2f}'
        except (TypeError, ValueError):
            return str(value)
    if field == 'purchase_date':
        if hasattr(value, 'strftime') and value:
            return value.strftime('%Y-%m-%d')
    if field in ('item_name', 'voucher_type', 'purchase_channel', 'remarks'):
        return f'"{value}"'
    return str(value)


def _voucher_values_equal(field, old_value, new_value):
    """比较两个凭证字段值是否变更。"""
    if field == 'amount':
        try:
            return float(old_value or 0) == float(new_value or 0)
        except (TypeError, ValueError):
            return str(old_value) == str(new_value)
    if field == 'purchase_date':
        old_str = old_value.strftime('%Y-%m-%d') if hasattr(old_value, 'strftime') and old_value else str(old_value or '')
        new_str = str(new_value) if new_value else ''
        return old_str == new_str
    if old_value is None and (new_value is None or new_value == ''):
        return True
    return str(old_value if old_value is not None else '') == str(new_value if new_value is not None else '')


@vouchers_bp.route('/vouchers', methods=['GET'])
@jwt_required()
def get_vouchers():
    logger.info('=== 获取凭证列表请求 ===')
    try:
        current_user_id = get_jwt_identity()
        
        event_id = request.args.get('event_id')
        if not event_id:
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
        
        vouchers = Voucher.query.filter_by(
            event_id=event_id,
            is_deleted=False
        ).order_by(Voucher.created_at.desc()).paginate(
            page=page,
            per_page=page_size,
            error_out=False
        )
        
        voucher_list = []
        for voucher in vouchers.items:
            voucher_data = {
                'voucher_id': voucher.voucher_id,
                'event_id': voucher.event_id,
                'uploader_id': voucher.uploader_id,
                'uploader_name': voucher.uploader.real_name if voucher.uploader else None,
                'file_name': voucher.file_name,
                'item_name': voucher.item_name,
                'voucher_type': voucher.voucher_type,
                'purchase_channel': voucher.purchase_channel,
                'purchase_date': voucher.purchase_date.isoformat() if voucher.purchase_date else None,
                'amount': float(voucher.amount),
                'is_reimbursed': voucher.is_reimbursed,
                'reimbursed_at': voucher.reimbursed_at.isoformat() if voucher.reimbursed_at else None,
                'remarks': voucher.remarks,
                'created_at': voucher.created_at.isoformat() if voucher.created_at else None,
                'record_type': 'voucher'
            }
            
            if storage_manager.is_available() and voucher.file_url:
                try:
                    voucher_data['file_url'] = storage_manager.get_presigned_url(voucher.file_url, expires=3600)
                except Exception as e:
                    logger.error(f'生成凭证临时URL失败: {str(e)}')
                    voucher_data['file_url'] = voucher.file_url
            else:
                voucher_data['file_url'] = voucher.file_url
            
            voucher_list.append(voucher_data)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'data': voucher_list,
                'total': vouchers.total,
                'page': page,
                'page_size': page_size,
                'total_pages': vouchers.pages
            }
        }), 200
        
    except Exception as e:
        logger.error(f'获取凭证列表异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@vouchers_bp.route('/vouchers', methods=['POST'])
@jwt_required()
def create_voucher():
    logger.info('=== 创建凭证请求 ===')
    try:
        current_user_id = get_jwt_identity()
        
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({'code': 401, 'message': '用户不存在', 'data': None}), 401
        
        if 'file' not in request.files:
            return jsonify({'code': 400, 'message': '请上传凭证文件', 'data': None}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'code': 400, 'message': '请选择文件', 'data': None}), 400
        
        allowed_extensions = {'pdf', 'png', 'jpg', 'jpeg'}
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if file_ext not in allowed_extensions:
            return jsonify({
                'code': 400,
                'message': '文件格式不支持',
                'data': None
            }), 400
        
        event_id = request.form.get('event_id')
        if not event_id:
            return jsonify({'code': 400, 'message': '缺少比赛ID', 'data': None}), 400
        
        event = Event.query.filter_by(event_id=event_id, is_deleted=False).first()
        if not event:
            return jsonify({'code': 2001, 'message': '比赛不存在', 'data': None}), 404
        
        from decimal import Decimal
        
        item_name = request.form.get('item_name')
        if not item_name:
            return jsonify({'code': 400, 'message': '物品名称不能为空', 'data': None}), 400
        
        file_md5 = None
        if storage_manager.is_available():
            file_content = file.read()
            file_md5 = hashlib.md5(file_content).hexdigest()
            file.seek(0)
            
            upload_result = storage_manager.upload_file(int(event_id), file, file.filename)
            file_url = upload_result['file_key']
        else:
            file_url = f'/uploads/vouchers/{file.filename}'
        
        voucher = Voucher(
            event_id=int(event_id),
            uploader_id=int(current_user_id),
            file_name=file.filename,
            file_md5=file_md5,
            file_url=file_url,
            item_name=item_name,
            voucher_type=request.form.get('voucher_type'),
            purchase_channel=request.form.get('purchase_channel'),
            purchase_date=datetime.strptime(request.form.get('purchase_date'), '%Y-%m-%d') if request.form.get('purchase_date') else None,
            amount=Decimal(str(request.form.get('amount', 0))),
            remarks=request.form.get('remarks')
        )
        
        db.session.add(voucher)
        
        event.voucher_count += 1
        event.voucher_total_amount += voucher.amount
        
        db.session.commit()

        logger.info(f'凭证创建成功: voucher_id={voucher.voucher_id}')

        _log_operation(
            user_id=int(current_user_id),
            username=user.username,
            action_type='create_voucher',
            action_description=f'上传凭证「{voucher.item_name}」',
            target_type='voucher',
            target_id=voucher.voucher_id,
            target_name=voucher.item_name,
            event_id=voucher.event_id,
            event_name=event.event_name if event else None,
            detail={'file_name': voucher.file_name, 'amount': float(voucher.amount), 'voucher_type': voucher.voucher_type}
        )

        return jsonify({
            'code': 200,
            'message': '凭证上传成功',
            'data': {
                'voucher_id': voucher.voucher_id,
                'file_name': voucher.file_name
            }
        }), 200
        
    except Exception as e:
        logger.error(f'创建凭证异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@vouchers_bp.route('/vouchers/<int:voucher_id>', methods=['DELETE'])
@jwt_required()
def delete_voucher(voucher_id):
    logger.info(f'=== 删除凭证: voucher_id={voucher_id} ===')
    try:
        current_user_id = get_jwt_identity()
        
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({'code': 401, 'message': '用户不存在', 'data': None}), 401
        
        voucher = Voucher.query.filter_by(voucher_id=voucher_id, is_deleted=False).first()
        if not voucher:
            return jsonify({'code': 3001, 'message': '凭证不存在', 'data': None}), 404
        
        if user.user_type not in ['admin', 'teacher'] and voucher.uploader_id != int(current_user_id):
            return jsonify({'code': 403, 'message': '权限不足', 'data': None}), 403
        
        event = Event.query.get(voucher.event_id)
        
        voucher.is_deleted = True
        
        if event:
            event.voucher_count = max(0, event.voucher_count - 1)
            event.voucher_total_amount = max(0, event.voucher_total_amount - voucher.amount)

        db.session.commit()

        _log_operation(
            user_id=int(current_user_id),
            username=user.username,
            action_type='delete_voucher',
            action_description=f'删除凭证「{voucher.item_name}」',
            target_type='voucher',
            target_id=voucher_id,
            target_name=voucher.item_name,
            event_id=voucher.event_id,
            event_name=event.event_name if event else None,
            detail={'file_name': voucher.file_name, 'amount': float(voucher.amount)}
        )

        return jsonify({
            'code': 200,
            'message': '凭证删除成功',
            'data': None
        }), 200
        
    except Exception as e:
        logger.error(f'删除凭证异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@vouchers_bp.route('/vouchers/<int:voucher_id>/download', methods=['GET'])
@jwt_required()
def download_voucher(voucher_id):
    logger.info(f'=== 下载凭证: voucher_id={voucher_id} ===')
    try:
        voucher = Voucher.query.filter_by(voucher_id=voucher_id, is_deleted=False).first()
        if not voucher:
            return jsonify({'code': 3001, 'message': '凭证不存在', 'data': None}), 404
        
        if not voucher.file_url:
            return jsonify({'code': 400, 'message': '凭证没有关联的文件', 'data': None}), 400
        
        if storage_manager.is_available():
            file_content = storage_manager.download_file(voucher.file_url)
            if not file_content:
                return jsonify({'code': 500, 'message': '无法获取文件', 'data': None}), 500
            
            from flask import Response
            safe_filename = urllib.parse.quote(voucher.file_name)
            return Response(
                file_content,
                mimetype='application/octet-stream',
                headers={
                    'Content-Disposition': f"attachment; filename*=UTF-8''{safe_filename}"
                }
            )
        else:
            from flask import send_file
            local_path = voucher.file_url.lstrip('/')
            if not __import__('os').path.exists(local_path):
                return jsonify({'code': 500, 'message': '文件不存在', 'data': None}), 500
            
            return send_file(local_path, as_attachment=True, download_name=voucher.file_name)
            
    except Exception as e:
        logger.error(f'下载凭证异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@vouchers_bp.route('/vouchers/<int:voucher_id>', methods=['PUT'])
@jwt_required()
def update_voucher(voucher_id):
    logger.info(f'=== 更新凭证: voucher_id={voucher_id} ===')
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        voucher = Voucher.query.filter_by(voucher_id=voucher_id, is_deleted=False).first()
        if not voucher:
            return jsonify({'code': 3001, 'message': '凭证不存在', 'data': None}), 404

        data = request.get_json()
        from decimal import Decimal

        # 在 commit 前获取旧值，用于日志记录变更详情
        old_item_name = voucher.item_name
        old_voucher_type = voucher.voucher_type
        old_purchase_channel = voucher.purchase_channel
        old_purchase_date = voucher.purchase_date
        old_amount = float(voucher.amount) if voucher.amount is not None else None
        old_remarks = voucher.remarks

        if 'item_name' in data and data['item_name']:
            voucher.item_name = data['item_name']
        if 'voucher_type' in data:
            voucher.voucher_type = data['voucher_type']
        if 'purchase_channel' in data:
            voucher.purchase_channel = data['purchase_channel']
        if 'purchase_date' in data and data['purchase_date']:
            voucher.purchase_date = datetime.strptime(data['purchase_date'], '%Y-%m-%d').date()
        if 'amount' in data:
            old_amount_dec = voucher.amount
            new_amount = Decimal(str(data['amount']))
            event = Event.query.get(voucher.event_id)
            if event:
                event.voucher_total_amount = event.voucher_total_amount - old_amount_dec + new_amount
            voucher.amount = new_amount
        if 'remarks' in data:
            voucher.remarks = data['remarks']

        # 在 commit 前构造变更字典
        changes = {}
        if 'item_name' in data and not _voucher_values_equal('item_name', old_item_name, data['item_name']):
            changes['item_name'] = {'old': old_item_name, 'new': data['item_name']}
        if 'voucher_type' in data and not _voucher_values_equal('voucher_type', old_voucher_type, data['voucher_type']):
            changes['voucher_type'] = {'old': old_voucher_type, 'new': data['voucher_type']}
        if 'purchase_channel' in data and not _voucher_values_equal('purchase_channel', old_purchase_channel, data['purchase_channel']):
            changes['purchase_channel'] = {'old': old_purchase_channel, 'new': data['purchase_channel']}
        if 'purchase_date' in data and data['purchase_date']:
            new_date = datetime.strptime(data['purchase_date'], '%Y-%m-%d').date()
            if not _voucher_values_equal('purchase_date', old_purchase_date, new_date):
                changes['purchase_date'] = {'old': old_purchase_date, 'new': new_date}
        if 'amount' in data:
            try:
                new_amount_val = float(Decimal(str(data['amount'])))
            except Exception:
                new_amount_val = data['amount']
            if not _voucher_values_equal('amount', old_amount, new_amount_val):
                changes['amount'] = {'old': old_amount, 'new': new_amount_val}
        if 'remarks' in data and not _voucher_values_equal('remarks', old_remarks, data['remarks']):
            changes['remarks'] = {'old': old_remarks, 'new': data['remarks']}

        # 构造 action_description（在 commit 前完成）
        related_event = Event.query.get(voucher.event_id)
        event_name_str = related_event.event_name if related_event else None
        if changes:
            change_parts = []
            for field in ['item_name', 'voucher_type', 'purchase_channel',
                          'purchase_date', 'amount', 'remarks']:
                if field in changes:
                    label = VOUCHER_FIELD_LABELS.get(field, field)
                    old_part = _format_voucher_value(field, changes[field]['old'])
                    new_part = _format_voucher_value(field, changes[field]['new'])
                    change_parts.append(f'{label} {old_part}→{new_part}')
            change_text = '、'.join(change_parts)
            action_desc = f'修改凭证「{voucher.item_name}」: {change_text}'
        else:
            action_desc = f'修改凭证「{voucher.item_name}」'

        db.session.commit()

        _log_operation(
            user_id=int(current_user_id),
            username=user.username if user else '',
            action_type='update_voucher',
            action_description=action_desc,
            target_type='voucher',
            target_id=voucher_id,
            target_name=voucher.item_name,
            event_id=voucher.event_id,
            event_name=event_name_str,
            detail={'changes': changes}
        )

        return jsonify({
            'code': 200,
            'message': '凭证信息更新成功',
            'data': None
        }), 200
        
    except Exception as e:
        logger.error(f'更新凭证异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@vouchers_bp.route('/check-file-md5', methods=['GET'])
@jwt_required()
def check_file_md5():
    logger.info('=== 检查文件MD5 ===')
    try:
        md5_hash = request.args.get('md5')
        event_id = request.args.get('event_id')
        
        if not md5_hash:
            return jsonify({'code': 400, 'message': '缺少md5参数', 'data': None}), 400
        
        # 检查购买记录中的购物凭证
        from models import PurchaseRecord
        existing_record = PurchaseRecord.query.filter_by(
            receipt_file_md5=md5_hash,
            is_deleted=False
        ).first()
        
        if existing_record:
            uploader = User.query.get(existing_record.uploader_id)
            return jsonify({
                'code': 200,
                'message': '找到重复文件',
                'data': {
                    'exists': True,
                    'uploader_name': uploader.real_name if uploader else '未知用户',
                    'upload_time': existing_record.created_at.isoformat() if existing_record.created_at else None,
                    'file_name': existing_record.receipt_image_name,
                    'type': 'receipt'
                }
            }), 200
        
        # 检查凭证表
        existing_voucher = Voucher.query.filter_by(
            file_md5=md5_hash,
            is_deleted=False
        ).first()
        
        if existing_voucher:
            uploader = User.query.get(existing_voucher.uploader_id)
            return jsonify({
                'code': 200,
                'message': '找到重复文件',
                'data': {
                    'exists': True,
                    'uploader_name': uploader.real_name if uploader else '未知用户',
                    'upload_time': existing_voucher.created_at.isoformat() if existing_voucher.created_at else None,
                    'file_name': existing_voucher.file_name,
                    'type': 'voucher'
                }
            }), 200
        
        return jsonify({
            'code': 200,
            'message': '未找到重复文件',
            'data': {
                'exists': False
            }
        }), 200
        
    except Exception as e:
        logger.error(f'检查文件MD5异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@vouchers_bp.route('/vouchers/batch-reimburse', methods=['POST'])
@jwt_required()
def batch_reimburse_vouchers():
    logger.info('=== 批量报销凭证 ===')
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or user.user_type not in ['admin', 'teacher']:
            return jsonify({'code': 403, 'message': '权限不足', 'data': None}), 403
        
        data = request.get_json()
        voucher_ids = data.get('voucher_ids', [])
        
        if not voucher_ids:
            return jsonify({'code': 400, 'message': '请选择要报销的凭证', 'data': None}), 400
        
        count = 0
        reimbursed_vouchers = []
        for vid in voucher_ids:
            voucher = Voucher.query.filter_by(voucher_id=vid, is_deleted=False).first()
            if voucher and not voucher.is_reimbursed:
                voucher.is_reimbursed = True
                voucher.reimbursed_at = datetime.utcnow()

                event = Event.query.get(voucher.event_id)
                if event:
                    event.reimbursed_amount += voucher.amount
                    event.remaining_budget = event.total_budget - event.reimbursed_amount

                reimbursed_vouchers.append({
                    'voucher_id': voucher.voucher_id,
                    'item_name': voucher.item_name,
                    'amount': float(voucher.amount),
                    'event_id': voucher.event_id
                })
                count += 1

        db.session.commit()

        total_amount = sum(v['amount'] for v in reimbursed_vouchers)
        _log_operation(
            user_id=int(current_user_id),
            username=user.username,
            action_type='batch_reimburse_vouchers',
            action_description=f'批量报销凭证 {count} 张，金额合计 ¥{total_amount:.2f}',
            target_type='voucher',
            event_id=reimbursed_vouchers[0]['event_id'] if reimbursed_vouchers else None,
            detail={
                'count': count,
                'total_amount': total_amount,
                'voucher_ids': [v['voucher_id'] for v in reimbursed_vouchers]
            }
        )

        return jsonify({
            'code': 200,
            'message': f'成功报销 {count} 张凭证',
            'data': {'count': count}
        }), 200
        
    except Exception as e:
        logger.error(f'批量报销凭证异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500