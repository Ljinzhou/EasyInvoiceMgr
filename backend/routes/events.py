from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Event, User, Invoice, PurchaseRecord, EventMember
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
events_bp = Blueprint('events', __name__)


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
EVENT_FIELD_LABELS = {
    'event_name': '项目名称',
    'description': '描述',
    'total_budget': '预算',
    'status': '状态',
    'event_start_time': '开始时间',
    'event_end_time': '结束时间',
    'upload_start_time': '上传开始时间',
    'upload_end_time': '上传结束时间',
    'leader_id': '负责人',
}


def _normalize_event_value(field, value):
    """将字段值归一化以便进行变更对比。"""
    if value is None:
        return None
    if field == 'total_budget':
        try:
            return float(value)
        except (TypeError, ValueError):
            return value
    if field in ('event_start_time', 'event_end_time', 'upload_start_time', 'upload_end_time'):
        if isinstance(value, datetime):
            return value.isoformat()
    return value


def _format_event_value(field, value):
    """将字段值格式化为人类可读的描述文本片段。"""
    if value is None:
        return '无'
    if field == 'total_budget':
        try:
            return f'{float(value):.2f}'
        except (TypeError, ValueError):
            return str(value)
    if field in ('event_start_time', 'event_end_time', 'upload_start_time', 'upload_end_time'):
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M')
    if field == 'leader_id':
        user_obj = User.query.get(value)
        return f'"{user_obj.real_name}"' if user_obj and user_obj.real_name else f'"{value}"'
    if field in ('event_name', 'description', 'status'):
        return f'"{value}"'
    return str(value)


@events_bp.route('/events', methods=['POST'])
@jwt_required()
def create_event():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'code': 403, 'message': '用户不存在', 'data': None}), 403
        # All authenticated users can create events

        data = request.get_json()
        
        required_fields = ['event_name', 'event_start_time', 'event_end_time']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'code': 400, 'message': f'{field} 不能为空', 'data': None}), 400
        
        try:
            event_start_time = datetime.fromisoformat(data['event_start_time'].replace('Z', '+00:00'))
            event_end_time = datetime.fromisoformat(data['event_end_time'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'code': 400, 'message': '日期格式错误', 'data': None}), 400
        
        if event_start_time >= event_end_time:
            return jsonify({'code': 400, 'message': '开始时间必须早于结束时间', 'data': None}), 400
        
        upload_start_time = None
        upload_end_time = None
        if 'upload_start_time' in data and data['upload_start_time']:
            upload_start_time = datetime.fromisoformat(data['upload_start_time'].replace('Z', '+00:00'))
        if 'upload_end_time' in data and data['upload_end_time']:
            upload_end_time = datetime.fromisoformat(data['upload_end_time'].replace('Z', '+00:00'))
        
        total_budget = float(data.get('total_budget', 0))
        if total_budget < 0:
            return jsonify({'code': 400, 'message': '预算不能为负数', 'data': None}), 400
        
        event = Event(
            event_name=data['event_name'],
            description=data.get('description'),
            status='ongoing',
            event_start_time=event_start_time,
            event_end_time=event_end_time,
            upload_start_time=upload_start_time,
            upload_end_time=upload_end_time,
            creator_id=current_user_id,
            leader_id=data.get('leader_id'),
            total_budget=total_budget,
            remaining_budget=total_budget
        )
        
        db.session.add(event)
        db.session.flush()  # 获取 event_id 但不提交事务

        # 如果指定了负责人，自动将负责人添加为赛事成员
        if event.leader_id:
            existing = EventMember.query.filter_by(
                event_id=event.event_id, user_id=event.leader_id, is_deleted=False
            ).first()
            if not existing:
                leader_user = User.query.get(event.leader_id)
                role = leader_user.user_type if leader_user and leader_user.user_type in ['teacher', 'student_admin'] else 'teacher'
                leader_member = EventMember(
                    event_id=event.event_id,
                    user_id=event.leader_id,
                    role_in_event=role
                )
                db.session.add(leader_member)

        # 同时将创建者添加为赛事成员
        if event.creator_id != event.leader_id:
            existing_creator = EventMember.query.filter_by(
                event_id=event.event_id, user_id=event.creator_id, is_deleted=False
            ).first()
            if not existing_creator:
                creator_member = EventMember(
                    event_id=event.event_id,
                    user_id=event.creator_id,
                    role_in_event='teacher'
                )
                db.session.add(creator_member)

        db.session.commit()

        # 记录日志
        _log_operation(
            user_id=int(current_user_id),
            username=user.username,
            action_type='create_event',
            action_description=f'创建项目「{event.event_name}」',
            target_type='event',
            target_id=event.event_id,
            target_name=event.event_name,
            event_id=event.event_id,
            event_name=event.event_name,
            detail={'budget': total_budget, 'description': data.get('description')}
        )

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'event_id': event.event_id,
                'event_name': event.event_name,
                'description': event.description,
                'status': event.status,
                'event_start_time': event.event_start_time.isoformat() if event.event_start_time else None,
                'event_end_time': event.event_end_time.isoformat() if event.event_end_time else None,
                'upload_start_time': event.upload_start_time.isoformat() if event.upload_start_time else None,
                'upload_end_time': event.upload_end_time.isoformat() if event.upload_end_time else None,
                'creator_id': event.creator_id,
                'leader_id': event.leader_id,
                'total_budget': float(event.total_budget),
                'reimbursed_amount': float(event.reimbursed_amount),
                'remaining_budget': float(event.remaining_budget),
                'invoice_count': event.invoice_count,
                'invoice_total_amount': float(event.invoice_total_amount)
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@events_bp.route('/events', methods=['GET'])
@jwt_required()
def get_events():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        status = request.args.get('status')

        query = Event.query.filter_by(is_deleted=False)

        if status:
            query = query.filter_by(status=status)
        
        total = query.count()
        events = query.order_by(Event.created_at.desc()).paginate(page=page, per_page=page_size, error_out=False)
        
        # Build set of event IDs where current user is a member (for is_member flag)
        member_event_ids = set()
        if user and user.user_type not in ['admin', 'teacher', 'student_admin']:
            member_rows = db.session.query(EventMember.event_id).filter_by(
                user_id=current_user_id, is_deleted=False
            ).all()
            member_event_ids = {row[0] for row in member_rows}

        events_data = []
        for event in events.items:
            leader = User.query.get(event.leader_id) if event.leader_id else None

            # Compute is_member: can the current user operate on this event?
            is_member = True
            if user and user.user_type not in ['admin', 'teacher', 'student_admin']:
                is_member = (event.creator_id == current_user_id) or (event.event_id in member_event_ids)
            
            invoice_count = Invoice.query.filter_by(event_id=event.event_id, is_deleted=False).count()
            purchase_count = PurchaseRecord.query.filter_by(event_id=event.event_id, is_deleted=False).count()

            # 发票总额：来自Invoice表 + PurchaseRecord中有发票的记录
            invoice_table_total = db.session.query(db.func.sum(Invoice.amount)).filter_by(
                event_id=event.event_id, is_deleted=False
            ).scalar() or 0
            purchase_invoice_total = db.session.query(db.func.sum(PurchaseRecord.total_amount)).filter_by(
                event_id=event.event_id, is_deleted=False, has_invoice=True
            ).scalar() or 0
            invoice_total = float(invoice_table_total) + float(purchase_invoice_total)

            purchase_total = db.session.query(db.func.sum(PurchaseRecord.amount)).filter_by(
                event_id=event.event_id, is_deleted=False
            ).scalar() or 0

            total_spent = float(invoice_table_total) + float(purchase_total)

            # 已报销金额：动态计算，确保数据准确
            invoice_reimbursed = db.session.query(db.func.sum(Invoice.total_amount)).filter_by(
                event_id=event.event_id, is_deleted=False, is_reimbursed=True
            ).scalar() or 0
            purchase_reimbursed = db.session.query(db.func.sum(PurchaseRecord.total_amount)).filter_by(
                event_id=event.event_id, is_deleted=False, has_invoice=True, is_reimbursed=True
            ).scalar() or 0
            reimbursed_amount = float(invoice_reimbursed) + float(purchase_reimbursed)

            events_data.append({
                'event_id': event.event_id,
                'event_name': event.event_name,
                'description': event.description,
                'status': event.status,
                'event_start_time': event.event_start_time.isoformat() if event.event_start_time else None,
                'event_end_time': event.event_end_time.isoformat() if event.event_end_time else None,
                'upload_start_time': event.upload_start_time.isoformat() if event.upload_start_time else None,
                'upload_end_time': event.upload_end_time.isoformat() if event.upload_end_time else None,
                'total_budget': float(event.total_budget),
                'reimbursed_amount': reimbursed_amount,
                'remaining_budget': float(event.total_budget) - reimbursed_amount,
                'spent_amount': total_spent,
                'invoice_total_amount': invoice_total,
                'purchase_total_amount': float(purchase_total),
                'invoice_count': invoice_count,
                'purchase_record_count': purchase_count,
                'voucher_count': invoice_count + purchase_count,
                'creator_id': event.creator_id,
                'leader_id': event.leader_id,
                'leader_name': leader.real_name if leader else None,
                'is_member': is_member
            })
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'total': total,
                'page': page,
                'page_size': page_size,
                'data': events_data
            }
        }), 200
        
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@events_bp.route('/events/<int:event_id>', methods=['PUT'])
@jwt_required()
def update_event(event_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or user.user_type not in ['admin', 'teacher', 'student_admin']:
            return jsonify({'code': 403, 'message': '权限不足', 'data': None}), 403

        event = Event.query.filter_by(event_id=event_id, is_deleted=False).first()

        if not event:
            return jsonify({'code': 2001, 'message': '赛事不存在', 'data': None}), 404

        # 自动检查并添加赛事成员
        ensure_event_membership(event_id, int(current_user_id))

        data = request.get_json()

        # 在修改前获取旧值，用于日志记录变更详情
        old_event_name = event.event_name
        old_description = event.description
        old_total_budget = float(event.total_budget or 0)
        old_status = event.status
        old_event_start_time = event.event_start_time
        old_event_end_time = event.event_end_time
        old_upload_start_time = event.upload_start_time
        old_upload_end_time = event.upload_end_time
        old_leader_id = event.leader_id

        if 'event_name' in data:
            event.event_name = data['event_name']
        if 'description' in data:
            event.description = data['description']
        if 'event_start_time' in data and data['event_start_time']:
            event.event_start_time = datetime.fromisoformat(data['event_start_time'].replace('Z', '+00:00'))
        if 'event_end_time' in data and data['event_end_time']:
            event.event_end_time = datetime.fromisoformat(data['event_end_time'].replace('Z', '+00:00'))
        if 'upload_start_time' in data and data['upload_start_time']:
            event.upload_start_time = datetime.fromisoformat(data['upload_start_time'].replace('Z', '+00:00'))
        if 'upload_end_time' in data and data['upload_end_time']:
            event.upload_end_time = datetime.fromisoformat(data['upload_end_time'].replace('Z', '+00:00'))
        if 'leader_id' in data:
            event.leader_id = data['leader_id']
            # 如果设置了负责人，确保负责人是赛事成员
            if event.leader_id:
                existing = EventMember.query.filter_by(
                    event_id=event_id, user_id=event.leader_id, is_deleted=False
                ).first()
                if not existing:
                    leader_user = User.query.get(event.leader_id)
                    role = leader_user.user_type if leader_user and leader_user.user_type in ['teacher', 'student_admin'] else 'teacher'
                    leader_member = EventMember(
                        event_id=event_id,
                        user_id=event.leader_id,
                        role_in_event=role
                    )
                    db.session.add(leader_member)
        if 'total_budget' in data:
            event.total_budget = data['total_budget']
            reimbursed = float(event.reimbursed_amount or 0)
            event.remaining_budget = float(data['total_budget']) - reimbursed
        if 'status' in data and data['status'] is not None:
            # 数据库枚举值: 'ongoing', 'finished'
            valid_statuses = ['ongoing', 'finished']
            new_status = data['status']
            if new_status in valid_statuses:
                old_status = event.status
                event.status = new_status
                logger.info(f'赛事状态变更: event_id={event_id}, {old_status} -> {new_status}')
            else:
                return jsonify({'code': 400, 'message': f'无效的状态值 "{new_status}"，有效值为: {", ".join(valid_statuses)}', 'data': None}), 400

        # 在 commit 前构造变更字典（与真实更新的字段保持一致）
        changes = {}
        if 'event_name' in data and data['event_name'] != old_event_name:
            changes['event_name'] = {'old': old_event_name, 'new': data['event_name']}
        if 'description' in data and data['description'] != old_description:
            changes['description'] = {'old': old_description, 'new': data['description']}
        if 'total_budget' in data:
            try:
                new_budget_val = float(data['total_budget'])
            except (TypeError, ValueError):
                new_budget_val = data['total_budget']
            if new_budget_val != old_total_budget:
                changes['total_budget'] = {'old': old_total_budget, 'new': new_budget_val}
        if 'status' in data and data['status'] is not None and data['status'] != old_status:
            changes['status'] = {'old': old_status, 'new': data['status']}
        if 'event_start_time' in data and data['event_start_time']:
            new_est = datetime.fromisoformat(data['event_start_time'].replace('Z', '+00:00'))
            if new_est != old_event_start_time:
                changes['event_start_time'] = {'old': old_event_start_time, 'new': new_est}
        if 'event_end_time' in data and data['event_end_time']:
            new_eet = datetime.fromisoformat(data['event_end_time'].replace('Z', '+00:00'))
            if new_eet != old_event_end_time:
                changes['event_end_time'] = {'old': old_event_end_time, 'new': new_eet}
        if 'upload_start_time' in data and data['upload_start_time']:
            new_ust = datetime.fromisoformat(data['upload_start_time'].replace('Z', '+00:00'))
            if new_ust != old_upload_start_time:
                changes['upload_start_time'] = {'old': old_upload_start_time, 'new': new_ust}
        if 'upload_end_time' in data and data['upload_end_time']:
            new_uet = datetime.fromisoformat(data['upload_end_time'].replace('Z', '+00:00'))
            if new_uet != old_upload_end_time:
                changes['upload_end_time'] = {'old': old_upload_end_time, 'new': new_uet}
        if 'leader_id' in data and data['leader_id'] != old_leader_id:
            changes['leader_id'] = {'old': old_leader_id, 'new': data['leader_id']}

        # 构造 action_description（在 commit 前完成，避免依赖 commit 后的状态）
        if changes:
            change_parts = []
            for field in ['event_name', 'description', 'total_budget', 'status',
                          'event_start_time', 'event_end_time',
                          'upload_start_time', 'upload_end_time', 'leader_id']:
                if field in changes:
                    label = EVENT_FIELD_LABELS.get(field, field)
                    old_part = _format_event_value(field, changes[field]['old'])
                    new_part = _format_event_value(field, changes[field]['new'])
                    change_parts.append(f'{label} {old_part}→{new_part}')
            change_text = '、'.join(change_parts)
            action_desc = f'修改项目「{event.event_name}」: {change_text}'
        else:
            action_desc = f'修改项目「{event.event_name}」'

        db.session.commit()
        logger.info(f'赛事更新成功: event_id={event_id}, event_name={event.event_name}, status={event.status}')

        # 记录日志
        _log_operation(
            user_id=int(current_user_id),
            username=user.username,
            action_type='update_event',
            action_description=action_desc,
            target_type='event',
            target_id=event_id,
            target_name=event.event_name,
            event_id=event_id,
            event_name=event.event_name,
            detail={'changes': changes}
        )

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'event_id': event.event_id,
                'event_name': event.event_name,
                'description': event.description,
                'status': event.status or 'ongoing',
                'event_start_time': event.event_start_time.isoformat() if event.event_start_time else None,
                'event_end_time': event.event_end_time.isoformat() if event.event_end_time else None,
                'upload_start_time': event.upload_start_time.isoformat() if event.upload_start_time else None,
                'upload_end_time': event.upload_end_time.isoformat() if event.upload_end_time else None,
                'creator_id': event.creator_id,
                'leader_id': event.leader_id,
                'total_budget': float(event.total_budget or 0),
                'reimbursed_amount': float(event.reimbursed_amount or 0),
                'remaining_budget': float(event.remaining_budget or 0)
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'更新赛事失败: event_id={event_id}, error={str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': f'服务器错误: {str(e)}', 'data': None}), 500

@events_bp.route('/events/<int:event_id>', methods=['GET'])
@jwt_required()
def get_event(event_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        event = Event.query.filter_by(event_id=event_id, is_deleted=False).first()

        if not event:
            return jsonify({'code': 2001, 'message': '赛事不存在', 'data': None}), 404

        # Compute is_member: can the current user operate on this event?
        event_is_member = True
        if user and user.user_type not in ['admin', 'teacher', 'student_admin']:
            member_check = EventMember.query.filter_by(
                event_id=event_id, user_id=current_user_id, is_deleted=False
            ).first()
            event_is_member = (event.creator_id == current_user_id) or (member_check is not None)

        leader = User.query.get(event.leader_id) if event.leader_id else None
        
        invoice_count = Invoice.query.filter_by(event_id=event_id, is_deleted=False).count()
        purchase_count = PurchaseRecord.query.filter_by(event_id=event_id, is_deleted=False).count()

        # 发票总额：来自Invoice表 + PurchaseRecord中有发票的记录
        invoice_table_total = db.session.query(db.func.sum(Invoice.amount)).filter_by(
            event_id=event_id, is_deleted=False
        ).scalar() or 0
        purchase_invoice_total = db.session.query(db.func.sum(PurchaseRecord.total_amount)).filter_by(
            event_id=event_id, is_deleted=False, has_invoice=True
        ).scalar() or 0
        invoice_total = float(invoice_table_total) + float(purchase_invoice_total)

        purchase_total = db.session.query(db.func.sum(PurchaseRecord.amount)).filter_by(
            event_id=event_id, is_deleted=False
        ).scalar() or 0

        total_spent = float(invoice_table_total) + float(purchase_total)

        # 已报销金额：动态计算，确保数据准确
        invoice_reimbursed = db.session.query(db.func.sum(Invoice.total_amount)).filter_by(
            event_id=event_id, is_deleted=False, is_reimbursed=True
        ).scalar() or 0
        purchase_reimbursed = db.session.query(db.func.sum(PurchaseRecord.total_amount)).filter_by(
            event_id=event_id, is_deleted=False, has_invoice=True, is_reimbursed=True
        ).scalar() or 0
        reimbursed_amount = float(invoice_reimbursed) + float(purchase_reimbursed)

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'event_id': event.event_id,
                'event_name': event.event_name,
                'description': event.description,
                'status': event.status,
                'event_start_time': event.event_start_time.isoformat() if event.event_start_time else None,
                'event_end_time': event.event_end_time.isoformat() if event.event_end_time else None,
                'upload_start_time': event.upload_start_time.isoformat() if event.upload_start_time else None,
                'upload_end_time': event.upload_end_time.isoformat() if event.upload_end_time else None,
                'creator_id': event.creator_id,
                'leader_id': event.leader_id,
                'leader_name': leader.real_name if leader else None,
                'total_budget': float(event.total_budget),
                'reimbursed_amount': reimbursed_amount,
                'remaining_budget': float(event.total_budget) - reimbursed_amount,
                'spent_amount': total_spent,
                'invoice_total_amount': invoice_total,
                'purchase_total_amount': float(purchase_total),
                'invoice_count': invoice_count,
                'purchase_record_count': purchase_count,
                'voucher_count': invoice_count + purchase_count,
                'is_member': event_is_member
            }
        }), 200

    except Exception as e:
        logger.error(f'获取赛事详情异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@events_bp.route('/events/<int:event_id>', methods=['DELETE'])
@jwt_required()
def delete_event(event_id):
    logger.info(f'=== 删除赛事请求: event_id={event_id} ===')
    try:
        current_user_id = get_jwt_identity()
        logger.info(f'当前用户ID: {current_user_id}')
        
        user = User.query.get(current_user_id)
        if not user:
            logger.warning(f'用户不存在: {current_user_id}')
            return jsonify({'code': 401, 'message': '用户不存在', 'data': None}), 401
        
        if user.user_type not in ['admin', 'teacher', 'student_admin']:
            logger.warning(f'权限不足: 用户类型={user.user_type}')
            return jsonify({'code': 403, 'message': '权限不足', 'data': None}), 403

        event = Event.query.filter_by(event_id=event_id, is_deleted=False).first()

        if not event:
            logger.warning(f'赛事不存在: event_id={event_id}')
            return jsonify({'code': 2001, 'message': '赛事不存在', 'data': None}), 404

        # 自动检查并添加赛事成员
        ensure_event_membership(event_id, int(current_user_id))

        invoice_count = Invoice.query.filter_by(event_id=event_id, is_deleted=False).count()
        logger.info(f'关联发票数量: {invoice_count}')
        
        if invoice_count > 0:
            logger.warning(f'赛事存在关联发票，无法删除: event_id={event_id}')
            return jsonify({
                'code': 400, 
                'message': f'该项目下存在 {invoice_count} 张发票，请先删除所有发票后再删除项目', 
                'data': None
            }), 400
        
        event.is_deleted = True
        db.session.commit()
        
        logger.info(f'赛事删除成功: event_id={event_id}, event_name={event.event_name}')

        # 记录日志
        _log_operation(
            user_id=int(current_user_id),
            username=user.username,
            action_type='delete_event',
            action_description=f'删除项目「{event.event_name}」',
            target_type='event',
            target_id=event_id,
            target_name=event.event_name,
            event_id=event_id,
            event_name=event.event_name
        )

        return jsonify({
            'code': 200,
            'message': '项目删除成功',
            'data': None
        }), 200
        
    except Exception as e:
        logger.error(f'删除赛事异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


@events_bp.route('/events/<int:event_id>/members', methods=['GET'])
@jwt_required()
def get_event_members(event_id):
    logger.info(f'=== 获取赛事成员列表: event_id={event_id} ===')
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({'code': 401, 'message': '用户不存在', 'data': None}), 401
        
        event = Event.query.filter_by(event_id=event_id, is_deleted=False).first()
        if not event:
            return jsonify({'code': 2001, 'message': '赛事不存在', 'data': None}), 404
        
        # 获取赛事成员
        members = db.session.query(User, EventMember.role_in_event).join(
            EventMember, User.user_id == EventMember.user_id
        ).filter(
            EventMember.event_id == event_id,
            EventMember.is_deleted == False,
            User.is_deleted == False
        ).all()
        
        members_data = []
        for user, role in members:
            members_data.append({
                'user_id': user.user_id,
                'username': user.username,
                'real_name': user.real_name,
                'email': user.email,
                'phone': user.phone,
                'user_type': user.user_type,
                'student_or_staff_id': user.student_or_staff_id,
                'avatar_url': user.avatar_url,
                'role_in_event': role,
                'created_at': user.created_at.isoformat() if user.created_at else None
            })
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'members': members_data,
                'total_count': len(members_data)
            }
        }), 200
        
    except Exception as e:
        logger.error(f'获取赛事成员列表异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


@events_bp.route('/events/<int:event_id>/members', methods=['POST'])
@jwt_required()
def add_event_member(event_id):
    logger.info(f'=== 添加赛事成员: event_id={event_id} ===')
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({'code': 401, 'message': '用户不存在', 'data': None}), 401
        
        event = Event.query.filter_by(event_id=event_id, is_deleted=False).first()
        if not event:
            return jsonify({'code': 2001, 'message': '赛事不存在', 'data': None}), 404
        
        data = request.get_json()
        user_id = data.get('user_id')
        role_in_event = data.get('role_in_event', 'student')
        
        if not user_id:
            return jsonify({'code': 400, 'message': '用户ID不能为空', 'data': None}), 400
        
        # 检查用户是否存在
        target_user = User.query.filter_by(user_id=user_id, is_deleted=False).first()
        if not target_user:
            return jsonify({'code': 404, 'message': '目标用户不存在', 'data': None}), 404
        
        # 检查用户是否已经是赛事成员
        existing_member = EventMember.query.filter_by(
            event_id=event_id,
            user_id=user_id,
            is_deleted=False
        ).first()
        
        if existing_member:
            return jsonify({'code': 400, 'message': '该用户已经是赛事成员', 'data': None}), 400
        
        # 添加成员
        member = EventMember(
            event_id=event_id,
            user_id=user_id,
            role_in_event=role_in_event
        )
        
        db.session.add(member)
        db.session.commit()
        
        logger.info(f'赛事成员添加成功: event_id={event_id}, user_id={user_id}, role={role_in_event}')

        # 记录日志
        _log_operation(
            user_id=int(current_user_id),
            username=user.username,
            action_type='add_member',
            action_description=f'添加成员「{target_user.real_name}」到项目「{event.event_name}」',
            target_type='event',
            target_id=event_id,
            target_name=event.event_name,
            event_id=event_id,
            event_name=event.event_name,
            detail={'added_user_id': user_id, 'added_user_name': target_user.real_name, 'role': role_in_event}
        )

        return jsonify({
            'code': 200,
            'message': '添加成员成功',
            'data': {
                'member_id': member.id,
                'user_id': user_id,
                'role_in_event': role_in_event
            }
        }), 201
        
    except Exception as e:
        logger.error(f'添加赛事成员异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


@events_bp.route('/events/<int:event_id>/members/<int:user_id>', methods=['DELETE'])
@jwt_required()
def remove_event_member(event_id, user_id):
    logger.info(f'=== 移除赛事成员: event_id={event_id}, user_id={user_id} ===')
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({'code': 401, 'message': '用户不存在', 'data': None}), 401
        
        event = Event.query.filter_by(event_id=event_id, is_deleted=False).first()
        if not event:
            return jsonify({'code': 2001, 'message': '赛事不存在', 'data': None}), 404
        
        # 检查成员是否存在
        member = EventMember.query.filter_by(
            event_id=event_id,
            user_id=user_id,
            is_deleted=False
        ).first()
        
        if not member:
            return jsonify({'code': 404, 'message': '成员不存在', 'data': None}), 404
        
        # 标记为删除
        member.is_deleted = True
        db.session.commit()
        
        logger.info(f'赛事成员移除成功: event_id={event_id}, user_id={user_id}')

        # 记录日志
        removed_user = User.query.get(user_id)
        _log_operation(
            user_id=int(current_user_id),
            username=user.username,
            action_type='remove_member',
            action_description=f'从项目「{event.event_name}」移除成员「{removed_user.real_name if removed_user else str(user_id)}」',
            target_type='event',
            target_id=event_id,
            target_name=event.event_name,
            event_id=event_id,
            event_name=event.event_name,
            detail={'removed_user_id': user_id}
        )

        return jsonify({
            'code': 200,
            'message': '移除成员成功',
            'data': None
        }), 200
        
    except Exception as e:
        logger.error(f'移除赛事成员异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


@events_bp.route('/events/<int:event_id>/members/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_event_member(event_id, user_id):
    logger.info(f'=== 更新赛事成员: event_id={event_id}, user_id={user_id} ===')
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({'code': 401, 'message': '用户不存在', 'data': None}), 401

        if user.user_type not in ['admin', 'teacher', 'student_admin']:
            return jsonify({'code': 403, 'message': '权限不足', 'data': None}), 403

        event = Event.query.filter_by(event_id=event_id, is_deleted=False).first()
        if not event:
            return jsonify({'code': 2001, 'message': '赛事不存在', 'data': None}), 404

        member = EventMember.query.filter_by(
            event_id=event_id,
            user_id=user_id,
            is_deleted=False
        ).first()

        if not member:
            return jsonify({'code': 404, 'message': '成员不存在', 'data': None}), 404

        data = request.get_json()
        role_in_event = data.get('role_in_event')

        if role_in_event and role_in_event not in ['student', 'student_admin', 'teacher']:
            return jsonify({'code': 400, 'message': '无效的角色类型', 'data': None}), 400

        if role_in_event:
            member.role_in_event = role_in_event

        db.session.commit()

        logger.info(f'赛事成员更新成功: event_id={event_id}, user_id={user_id}, role={member.role_in_event}')

        # 记录日志
        target_user = User.query.get(user_id)
        _log_operation(
            user_id=int(current_user_id),
            username=user.username,
            action_type='update_member_role',
            action_description=f'修改项目「{event.event_name}」成员「{target_user.real_name if target_user else str(user_id)}」的角色为{role_in_event}',
            target_type='event',
            target_id=event_id,
            target_name=event.event_name,
            event_id=event_id,
            event_name=event.event_name,
            detail={'target_user_id': user_id, 'new_role': role_in_event}
        )

        return jsonify({
            'code': 200,
            'message': '更新成员成功',
            'data': {
                'user_id': user_id,
                'role_in_event': member.role_in_event
            }
        }), 200

    except Exception as e:
        logger.error(f'更新赛事成员异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

from sqlalchemy import func

@events_bp.route('/events/stats/user-summary', methods=['GET'])
@jwt_required()
def get_user_summary():
    logger.info('=== 获取用户消费汇总排名 ===')
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({'code': 401, 'message': '用户不存在', 'data': None}), 401

        event_id = request.args.get('event_id', type=int)
        status = request.args.get('status')  # 'ongoing', 'finished', or None for all

        # Build a list of event IDs the user can access
        if event_id:
            event = Event.query.filter_by(event_id=event_id, is_deleted=False).first()
            if not event:
                return jsonify({'code': 404, 'message': '赛事不存在', 'data': None}), 404
            event_ids = [event_id]
        elif status == 'ongoing':
            events = Event.query.filter_by(is_deleted=False, status='ongoing').all()
            event_ids = [e.event_id for e in events]
        elif status == 'finished':
            events = Event.query.filter_by(is_deleted=False, status='finished').all()
            event_ids = [e.event_id for e in events]
        else:
            # 所有用户均可查看全部比赛的消费排名
            events = Event.query.filter_by(is_deleted=False).all()
            event_ids = [e.event_id for e in events]

        if not event_ids:
            return jsonify({'code': 200, 'message': 'success', 'data': {'rankings': []}}), 200

        # Aggregate purchase records per uploader
        pr_sq = db.session.query(
            PurchaseRecord.uploader_id,
            func.sum(PurchaseRecord.amount).label('pr_total'),
            func.count(PurchaseRecord.record_id).label('pr_count')
        ).filter(
            PurchaseRecord.event_id.in_(event_ids),
            PurchaseRecord.is_deleted == False
        ).group_by(PurchaseRecord.uploader_id).subquery()

        # Aggregate invoices per uploader
        inv_sq = db.session.query(
            Invoice.uploader_id,
            func.sum(Invoice.amount).label('inv_total'),
            func.count(Invoice.invoice_id).label('inv_count')
        ).filter(
            Invoice.event_id.in_(event_ids),
            Invoice.is_deleted == False
        ).group_by(Invoice.uploader_id).subquery()

        # Combine with user info
        results = db.session.query(
            User.user_id,
            User.real_name,
            User.user_type,
            func.coalesce(pr_sq.c.pr_total, 0).label('pr_total'),
            func.coalesce(inv_sq.c.inv_total, 0).label('inv_total'),
            func.coalesce(pr_sq.c.pr_count, 0).label('pr_count'),
            func.coalesce(inv_sq.c.inv_count, 0).label('inv_count')
        ).outerjoin(pr_sq, User.user_id == pr_sq.c.uploader_id
        ).outerjoin(inv_sq, User.user_id == inv_sq.c.uploader_id
        ).filter(
            db.or_(pr_sq.c.uploader_id != None, inv_sq.c.uploader_id != None)
        ).all()

        rankings = []
        for row in results:
            total_amount = float(row.pr_total or 0) + float(row.inv_total or 0)
            rankings.append({
                'user_id': row.user_id,
                'real_name': row.real_name,
                'user_type': row.user_type,
                'total_amount': round(total_amount, 2),
                'record_count': (row.pr_count or 0) + (row.inv_count or 0)
            })

        rankings.sort(key=lambda x: x['total_amount'], reverse=True)

        logger.info(f'用户消费汇总查询成功: {len(rankings)} 条记录')
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {'rankings': rankings}
        }), 200

    except Exception as e:
        logger.error(f'获取用户消费汇总异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


def ensure_event_membership(event_id: int, user_id: int) -> bool:
    """
    检查用户是否在赛事成员列表中，若不在则自动添加。
    仅对 admin/teacher/student_admin 用户执行此检查。

    返回 True 表示已是成员或已成功添加，False 表示添加失败。
    """
    try:
        from models import User, EventMember, Event

        user = db.session.get(User, user_id)
        if not user or user.user_type not in ['admin', 'teacher', 'student_admin']:
            return True  # 非特权用户，无需检查

        event = db.session.get(Event, event_id)
        if not event:
            return False

        existing = EventMember.query.filter_by(
            event_id=event_id, user_id=user_id, is_deleted=False
        ).first()
        if existing:
            return True  # 已在名单中

        # 自动添加为赛事成员
        role = user.user_type if user.user_type in ['teacher', 'student_admin'] else 'teacher'
        member = EventMember(
            event_id=event_id,
            user_id=user_id,
            role_in_event=role
        )
        db.session.add(member)
        logger.info(f'自动添加赛事成员: event_id={event_id}, user_id={user_id}, role={role}')
        return True
    except Exception as e:
        logger.error(f'自动添加赛事成员失败: {e}', exc_info=True)
        return False
