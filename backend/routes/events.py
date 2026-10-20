from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Event, User, Invoice, PurchaseRecord, EventMember, EventJoinRequest
from utils.operation_log import log_operation
from utils.permissions import (
    ensure_event_membership,
    is_event_reviewer,
    resolve_auto_reviewer_id,
)
from utils.event_stats import recalc_event_stats
from datetime import datetime, timezone
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)
events_bp = Blueprint('events', __name__)


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
    'join_review_mode': '加入审核方式',
}

# 加入审核方式取值与中文标签
JOIN_REVIEW_MODES = ('auto', 'manual')
JOIN_REVIEW_MODE_LABELS = {'auto': '自动审核加入', 'manual': '人工审核加入'}

# 成员加入途径的展示文案
JOIN_SOURCE_LABELS = {
    'creator': '创建项目',
    'leader': '设为负责人',
    'direct_add': '直接添加',
    'auto_review': '自动审核通过',
    'manual_review': '人工审核通过',
    'privileged_auto': '权限自动加入',
    'legacy': '历史数据',
}


def _parse_join_review_mode(value, default='manual'):
    """校验并归一化加入审核方式；非法值抛 ValueError。"""
    if value is None or value == '':
        return default
    if value not in JOIN_REVIEW_MODES:
        raise ValueError(f'无效的加入审核方式 "{value}"，有效值为: auto、manual')
    return value


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
    if field == 'join_review_mode':
        return f'"{JOIN_REVIEW_MODE_LABELS.get(value, value)}"'
    return str(value)


def _iso(value):
    return value.isoformat() if value else None


def _serialize_join_request(join_request):
    """序列化一条加入申请（含申请人/审核人姓名）。"""
    applicant = join_request.user
    reviewer = join_request.reviewer
    return {
        'request_id': join_request.request_id,
        'event_id': join_request.event_id,
        'user_id': join_request.user_id,
        'username': applicant.username if applicant else None,
        'real_name': applicant.real_name if applicant else None,
        'status': join_request.status,
        'review_mode': join_request.review_mode,
        'reviewer_id': join_request.reviewer_id,
        'reviewer_name': reviewer.real_name if reviewer else None,
        'review_time': _iso(join_request.review_time),
        'reject_reason': join_request.reject_reason,
        'created_at': _iso(join_request.created_at)
    }


def _serialize_my_join_request(event_id, user_id):
    """当前用户在该赛事里最近一次（未删除的）加入申请。"""
    if not user_id:
        return None
    latest = EventJoinRequest.query.filter_by(
        event_id=event_id, user_id=user_id, is_deleted=False
    ).order_by(EventJoinRequest.request_id.desc()).first()
    return _serialize_join_request(latest) if latest else None


def _grant_membership(event, user_id, reviewer_id, join_source, role=None):
    """把用户加进赛事成员表，并记录是审核人/操作人加的。

    已存在的成员行不重复插入，只补齐此前为空的 joined_by/join_source。
    返回 (member, created)。
    """
    existing = EventMember.query.filter_by(
        event_id=event.event_id, user_id=user_id, is_deleted=False
    ).first()
    if existing:
        if not existing.joined_by:
            existing.joined_by = reviewer_id
        if not existing.join_source:
            existing.join_source = join_source
        return existing, False

    member_user = User.query.get(user_id)
    if role is None:
        role = 'teacher' if (member_user and member_user.user_type == 'teacher') else 'member'
    member = EventMember(
        event_id=event.event_id,
        user_id=user_id,
        role_in_event=role,
        joined_by=reviewer_id,
        join_source=join_source
    )
    db.session.add(member)
    return member, True


@events_bp.route('/events', methods=['POST'])
@jwt_required()
def create_event():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'code': 403, 'message': '用户不存在', 'data': None}), 403
        # 所有已认证用户均可创建项目

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

        try:
            join_review_mode = _parse_join_review_mode(data.get('join_review_mode'))
        except ValueError as error:
            return jsonify({'code': 400, 'message': str(error), 'data': None}), 400

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
            join_review_mode=join_review_mode,
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
                    role_in_event=role,
                    joined_by=current_user_id,
                    join_source='leader'
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
                    role_in_event='teacher',
                    joined_by=current_user_id,
                    join_source='creator'
                )
                db.session.add(creator_member)

        db.session.commit()

        # 记录日志
        log_operation(
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
                'join_review_mode': event.join_review_mode or 'manual',
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
        
        # 构建当前用户所属的赛事 ID 集合（用于 is_member 标记）
        member_event_ids = set()
        if user and user.user_type not in ['admin', 'teacher', 'student_admin']:
            member_rows = db.session.query(EventMember.event_id).filter_by(
                user_id=current_user_id, is_deleted=False
            ).all()
            member_event_ids = {row[0] for row in member_rows}

        # 当前用户在每个赛事里最近一次加入申请的状态（用于前端按钮文案）
        my_request_status = {}
        request_rows = db.session.query(
            EventJoinRequest.event_id, EventJoinRequest.status, EventJoinRequest.request_id
        ).filter(
            EventJoinRequest.user_id == current_user_id,
            EventJoinRequest.is_deleted == False  # noqa: E712
        ).order_by(EventJoinRequest.request_id).all()
        for req_event_id, req_status, _req_id in request_rows:
            my_request_status[req_event_id] = req_status

        events_data = []
        for event in events.items:
            leader = User.query.get(event.leader_id) if event.leader_id else None

            # 计算 is_member：当前用户能否操作该赛事？
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
                'is_member': is_member,
                'join_review_mode': event.join_review_mode or 'manual',
                'join_request_status': my_request_status.get(event.event_id)
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
        old_join_review_mode = event.join_review_mode or 'manual'

        if 'join_review_mode' in data:
            try:
                event.join_review_mode = _parse_join_review_mode(
                    data['join_review_mode'], default=old_join_review_mode
                )
            except ValueError as error:
                return jsonify({'code': 400, 'message': str(error), 'data': None}), 400

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
        if 'join_review_mode' in data and (event.join_review_mode or 'manual') != old_join_review_mode:
            changes['join_review_mode'] = {'old': old_join_review_mode, 'new': event.join_review_mode}

        # 构造 action_description（在 commit 前完成，避免依赖 commit 后的状态）
        if changes:
            change_parts = []
            for field in ['event_name', 'description', 'total_budget', 'status',
                          'event_start_time', 'event_end_time',
                          'upload_start_time', 'upload_end_time', 'leader_id',
                          'join_review_mode']:
                if field in changes:
                    label = EVENT_FIELD_LABELS.get(field, field)
                    old_part = _format_event_value(field, changes[field]['old'])
                    new_part = _format_event_value(field, changes[field]['new'])
                    change_parts.append(f'{label} {old_part}→{new_part}')
            change_text = '、'.join(change_parts)
            action_desc = f'修改项目「{event.event_name}」: {change_text}'
        else:
            action_desc = f'修改项目「{event.event_name}」'

        # 预算变更会影响剩余额度，统一重算
        if 'total_budget' in data:
            recalc_event_stats(event_id)

        db.session.commit()
        logger.info(f'赛事更新成功: event_id={event_id}, event_name={event.event_name}, status={event.status}')

        # 记录日志
        log_operation(
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
                'join_review_mode': event.join_review_mode or 'manual',
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

        # 计算 is_member：当前用户能否操作该赛事？
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
                'is_member': event_is_member,
                'join_review_mode': event.join_review_mode or 'manual',
                'can_review_join': is_event_reviewer(event, user),
                'my_join_request': _serialize_my_join_request(event_id, current_user_id)
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
        log_operation(
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
        
        # 获取赛事成员（带加入时间与审核人）
        rows = db.session.query(EventMember, User).join(
            User, User.user_id == EventMember.user_id
        ).filter(
            EventMember.event_id == event_id,
            EventMember.is_deleted == False,  # noqa: E712
            User.is_deleted == False  # noqa: E712
        ).order_by(EventMember.join_time, EventMember.id).all()

        joiner_ids = {member_row.joined_by for member_row, _member_user in rows if member_row.joined_by}
        joiners = {}
        if joiner_ids:
            joiners = {
                joiner.user_id: joiner
                for joiner in User.query.filter(User.user_id.in_(joiner_ids)).all()
            }

        members_data = []
        for member_row, member_user in rows:
            joiner = joiners.get(member_row.joined_by)
            members_data.append({
                'user_id': member_user.user_id,
                'username': member_user.username,
                'real_name': member_user.real_name,
                'email': member_user.email,
                'phone': member_user.phone,
                'user_type': member_user.user_type,
                'student_or_staff_id': member_user.student_or_staff_id,
                'avatar_url': member_user.avatar_url,
                'role_in_event': member_row.role_in_event,
                'join_time': _iso(member_row.join_time),
                'joined_by': member_row.joined_by,
                'joined_by_name': joiner.real_name or joiner.username if joiner else None,
                'join_source': member_row.join_source,
                'join_source_label': JOIN_SOURCE_LABELS.get(member_row.join_source),
                'created_at': _iso(member_user.created_at)
            })

        can_review = is_event_reviewer(event, user)
        pending_count = 0
        if can_review:
            pending_count = EventJoinRequest.query.filter_by(
                event_id=event_id, status='pending', is_deleted=False
            ).count()

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'members': members_data,
                'total_count': len(members_data),
                'can_review_join': can_review,
                'pending_request_count': pending_count,
                'join_review_mode': event.join_review_mode or 'manual'
            }
        }), 200
        
    except Exception as e:
        logger.error(f'获取赛事成员列表异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


@events_bp.route('/events/<int:event_id>/join-requests', methods=['POST'])
@jwt_required()
def create_join_request(event_id):
    """提交加入比赛的申请。自动审核模式下当场通过，审核人记为 admin。"""
    logger.info(f'=== 提交加入申请: event_id={event_id} ===')
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({'code': 401, 'message': '用户不存在', 'data': None}), 401

        event = Event.query.filter_by(event_id=event_id, is_deleted=False).first()
        if not event:
            return jsonify({'code': 2001, 'message': '赛事不存在', 'data': None}), 404

        if (event.status or 'ongoing') != 'ongoing':
            return jsonify({'code': 400, 'message': '该比赛已结束，无法申请加入', 'data': None}), 400

        existing_member = EventMember.query.filter_by(
            event_id=event_id, user_id=current_user_id, is_deleted=False
        ).first()
        if existing_member:
            return jsonify({'code': 400, 'message': '您已经是该比赛成员，无需申请', 'data': None}), 400

        pending = EventJoinRequest.query.filter_by(
            event_id=event_id, user_id=current_user_id, status='pending', is_deleted=False
        ).first()
        if pending:
            return jsonify({'code': 400, 'message': '您的加入申请正在审核中，请耐心等待', 'data': None}), 400

        review_mode = event.join_review_mode or 'manual'
        now = datetime.now(timezone.utc)
        join_request = EventJoinRequest(
            event_id=event_id,
            user_id=current_user_id,
            status='pending',
            review_mode=review_mode
        )
        db.session.add(join_request)
        db.session.flush()

        is_member = False
        message = '加入申请已提交，请等待审核'
        if review_mode == 'auto':
            reviewer_id = resolve_auto_reviewer_id()
            join_request.status = 'approved'
            join_request.reviewer_id = reviewer_id
            join_request.review_time = now
            _grant_membership(event, current_user_id, reviewer_id, 'auto_review')
            is_member = True
            message = '已自动通过审核，您已加入该比赛'

        db.session.commit()

        log_operation(
            user_id=current_user_id,
            username=user.username,
            action_type='apply_join_event',
            action_description=f'申请加入项目「{event.event_name}」',
            target_type='event',
            target_id=event_id,
            target_name=event.event_name,
            event_id=event_id,
            event_name=event.event_name,
            detail={
                'request_id': join_request.request_id,
                'review_mode': review_mode,
                'auto_approved': is_member
            }
        )

        return jsonify({
            'code': 200,
            'message': message,
            'data': {
                'request': _serialize_join_request(join_request),
                'is_member': is_member
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f'提交加入申请异常: event_id={event_id}, error={str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': f'服务器错误: {str(e)}', 'data': None}), 500


@events_bp.route('/events/<int:event_id>/join-requests', methods=['GET'])
@jwt_required()
def get_join_requests(event_id):
    """列出加入申请。只有负责人/指导老师/admin 能看，其他人 403。"""
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({'code': 401, 'message': '用户不存在', 'data': None}), 401

        event = Event.query.filter_by(event_id=event_id, is_deleted=False).first()
        if not event:
            return jsonify({'code': 2001, 'message': '赛事不存在', 'data': None}), 404

        if not is_event_reviewer(event, user):
            return jsonify({
                'code': 403,
                'message': '只有该比赛的负责人、指导老师或管理员可以审核加入申请',
                'data': None
            }), 403

        status = request.args.get('status')
        query = EventJoinRequest.query.filter_by(event_id=event_id, is_deleted=False)
        if status:
            query = query.filter_by(status=status)

        rows = query.order_by(EventJoinRequest.request_id.desc()).all()
        pending_count = EventJoinRequest.query.filter_by(
            event_id=event_id, status='pending', is_deleted=False
        ).count()

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'requests': [_serialize_join_request(row) for row in rows],
                'pending_count': pending_count,
                'join_review_mode': event.join_review_mode or 'manual'
            }
        }), 200

    except Exception as e:
        logger.error(f'获取加入申请异常: event_id={event_id}, error={str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': f'服务器错误: {str(e)}', 'data': None}), 500


@events_bp.route('/events/<int:event_id>/join-requests/<int:request_id>/review', methods=['POST'])
@jwt_required()
def review_join_request(event_id, request_id):
    """审核加入申请：approve 通过并加入成员，reject 驳回。"""
    logger.info(f'=== 审核加入申请: event_id={event_id}, request_id={request_id} ===')
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({'code': 401, 'message': '用户不存在', 'data': None}), 401

        event = Event.query.filter_by(event_id=event_id, is_deleted=False).first()
        if not event:
            return jsonify({'code': 2001, 'message': '赛事不存在', 'data': None}), 404

        if not is_event_reviewer(event, user):
            return jsonify({
                'code': 403,
                'message': '只有该比赛的负责人、指导老师或管理员可以审核加入申请',
                'data': None
            }), 403

        join_request = EventJoinRequest.query.filter_by(
            event_id=event_id, request_id=request_id, is_deleted=False
        ).first()
        if not join_request:
            return jsonify({'code': 2002, 'message': '加入申请不存在', 'data': None}), 404

        if join_request.status != 'pending':
            return jsonify({
                'code': 400,
                'message': f'该申请已处理（当前状态：{join_request.status}），不能重复审核',
                'data': None
            }), 400

        data = request.get_json(silent=True) or {}
        action = data.get('action')
        if action not in ('approve', 'reject'):
            return jsonify({'code': 400, 'message': 'action 必须是 approve 或 reject', 'data': None}), 400

        now = datetime.now(timezone.utc)
        applicant = User.query.get(join_request.user_id)
        applicant_name = (applicant.real_name or applicant.username) if applicant else str(join_request.user_id)

        join_request.reviewer_id = current_user_id
        join_request.review_time = now

        if action == 'approve':
            join_request.status = 'approved'
            join_request.reject_reason = None
            _grant_membership(event, join_request.user_id, current_user_id, 'manual_review')
            action_desc = f'通过「{applicant_name}」加入项目「{event.event_name}」的申请'
        else:
            join_request.status = 'rejected'
            join_request.reject_reason = (data.get('reject_reason') or '').strip() or None
            action_desc = f'驳回「{applicant_name}」加入项目「{event.event_name}」的申请'

        db.session.commit()

        log_operation(
            user_id=current_user_id,
            username=user.username,
            action_type='review_join_request',
            action_description=action_desc,
            target_type='event',
            target_id=event_id,
            target_name=event.event_name,
            event_id=event_id,
            event_name=event.event_name,
            detail={
                'request_id': request_id,
                'applicant_id': join_request.user_id,
                'applicant_name': applicant_name,
                'action': action,
                'reject_reason': join_request.reject_reason
            }
        )

        return jsonify({
            'code': 200,
            'message': '审核通过，该用户已加入比赛' if action == 'approve' else '已驳回该申请',
            'data': {
                'request': _serialize_join_request(join_request),
                'is_member': action == 'approve'
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'审核加入申请异常: event_id={event_id}, error={str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': f'服务器错误: {str(e)}', 'data': None}), 500


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
            role_in_event=role_in_event,
            joined_by=current_user_id,
            join_source='direct_add'
        )
        
        db.session.add(member)
        db.session.commit()
        
        logger.info(f'赛事成员添加成功: event_id={event_id}, user_id={user_id}, role={role_in_event}')

        # 记录日志
        log_operation(
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
        log_operation(
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
        log_operation(
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
        status = request.args.get('status')  # 'ongoing'、'finished'，或 None 表示全部

        # 构建用户可访问的赛事 ID 列表
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

        # 按上传人聚合购买记录
        pr_sq = db.session.query(
            PurchaseRecord.uploader_id,
            func.sum(PurchaseRecord.amount).label('pr_total'),
            func.count(PurchaseRecord.record_id).label('pr_count')
        ).filter(
            PurchaseRecord.event_id.in_(event_ids),
            PurchaseRecord.is_deleted == False
        ).group_by(PurchaseRecord.uploader_id).subquery()

        # 按上传人聚合发票
        inv_sq = db.session.query(
            Invoice.uploader_id,
            func.sum(Invoice.amount).label('inv_total'),
            func.count(Invoice.invoice_id).label('inv_count')
        ).filter(
            Invoice.event_id.in_(event_ids),
            Invoice.is_deleted == False
        ).group_by(Invoice.uploader_id).subquery()

        # 与用户信息合并
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

