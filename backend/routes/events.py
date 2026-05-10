from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Event, User, Invoice, PurchaseRecord, EventMember
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
events_bp = Blueprint('events', __name__)

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
            remaining_budget=total_budget,
            need_invoice_review=data.get('need_invoice_review', True)
        )
        
        db.session.add(event)
        db.session.commit()
        
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
                'invoice_total_amount': float(event.invoice_total_amount),
                'need_invoice_review': event.need_invoice_review
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

        # Non-admin/teacher users can only see events they created or are members of
        if user and user.user_type not in ['admin', 'teacher']:
            member_event_ids = db.session.query(EventMember.event_id).filter_by(
                user_id=current_user_id, is_deleted=False
            ).subquery()
            query = query.filter(
                db.or_(
                    Event.creator_id == current_user_id,
                    Event.event_id.in_(member_event_ids)
                )
            )

        if status:
            query = query.filter_by(status=status)
        
        total = query.count()
        events = query.order_by(Event.created_at.desc()).paginate(page=page, per_page=page_size, error_out=False)
        
        events_data = []
        for event in events.items:
            leader = User.query.get(event.leader_id) if event.leader_id else None
            
            invoice_count = Invoice.query.filter_by(event_id=event.event_id, is_deleted=False).count()
            purchase_count = PurchaseRecord.query.filter_by(event_id=event.event_id, is_deleted=False).count()
            
            invoice_total = db.session.query(db.func.sum(Invoice.amount)).filter_by(
                event_id=event.event_id, is_deleted=False
            ).scalar() or 0
            
            purchase_total = db.session.query(db.func.sum(PurchaseRecord.amount)).filter_by(
                event_id=event.event_id, is_deleted=False
            ).scalar() or 0
            
            total_spent = float(invoice_total) + float(purchase_total)
            
            events_data.append({
                'event_id': event.event_id,
                'event_name': event.event_name,
                'description': event.description,
                'status': event.status,
                'event_start_time': event.event_start_time.isoformat() if event.event_start_time else None,
                'event_end_time': event.event_end_time.isoformat() if event.event_end_time else None,
                'total_budget': float(event.total_budget),
                'reimbursed_amount': float(event.reimbursed_amount),
                'remaining_budget': float(event.remaining_budget),
                'spent_amount': total_spent,
                'invoice_total_amount': float(invoice_total),
                'purchase_total_amount': float(purchase_total),
                'invoice_count': invoice_count,
                'purchase_record_count': purchase_count,
                'voucher_count': invoice_count + purchase_count,
                'creator_id': event.creator_id,
                'leader_name': leader.real_name if leader else None,
                'need_invoice_review': event.need_invoice_review
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
        
        if not user or user.user_type not in ['admin', 'teacher']:
            return jsonify({'code': 403, 'message': '权限不足', 'data': None}), 403
        
        event = Event.query.filter_by(event_id=event_id, is_deleted=False).first()
        
        if not event:
            return jsonify({'code': 2001, 'message': '赛事不存在', 'data': None}), 404
        
        data = request.get_json()
        
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
        if 'total_budget' in data:
            event.total_budget = data['total_budget']
            event.remaining_budget = data['total_budget'] - float(event.reimbursed_amount)
        if 'need_invoice_review' in data:
            event.need_invoice_review = bool(data['need_invoice_review'])
        
        db.session.commit()
        
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
                'need_invoice_review': event.need_invoice_review
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@events_bp.route('/events/<int:event_id>', methods=['GET'])
@jwt_required()
def get_event(event_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        event = Event.query.filter_by(event_id=event_id, is_deleted=False).first()

        if not event:
            return jsonify({'code': 2001, 'message': '赛事不存在', 'data': None}), 404

        # Non-admin/teacher users can only view events they created or are members of
        if user and user.user_type not in ['admin', 'teacher']:
            is_member = EventMember.query.filter_by(
                event_id=event_id, user_id=current_user_id, is_deleted=False
            ).first()
            if event.creator_id != current_user_id and not is_member:
                return jsonify({'code': 403, 'message': '无权访问该项目', 'data': None}), 403

        leader = User.query.get(event.leader_id) if event.leader_id else None
        
        invoice_count = Invoice.query.filter_by(event_id=event_id, is_deleted=False).count()
        purchase_count = PurchaseRecord.query.filter_by(event_id=event_id, is_deleted=False).count()
        
        invoice_total = db.session.query(db.func.sum(Invoice.amount)).filter_by(
            event_id=event_id, is_deleted=False
        ).scalar() or 0
        
        purchase_total = db.session.query(db.func.sum(PurchaseRecord.amount)).filter_by(
            event_id=event_id, is_deleted=False
        ).scalar() or 0
        
        total_spent = float(invoice_total) + float(purchase_total)
        
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
                'reimbursed_amount': float(event.reimbursed_amount),
                'remaining_budget': float(event.remaining_budget),
                'spent_amount': total_spent,
                'invoice_total_amount': float(invoice_total),
                'purchase_total_amount': float(purchase_total),
                'invoice_count': invoice_count,
                'purchase_record_count': purchase_count,
                'voucher_count': invoice_count + purchase_count,
                'need_invoice_review': event.need_invoice_review
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
        
        if user.user_type not in ['admin', 'teacher']:
            logger.warning(f'权限不足: 用户类型={user.user_type}')
            return jsonify({'code': 403, 'message': '权限不足，只有管理员或教师可以删除项目', 'data': None}), 403
        
        event = Event.query.filter_by(event_id=event_id, is_deleted=False).first()
        
        if not event:
            logger.warning(f'赛事不存在: event_id={event_id}')
            return jsonify({'code': 2001, 'message': '赛事不存在', 'data': None}), 404
        
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
        role_in_event = data.get('role_in_event', 'member')
        
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
        return jsonify({
            'code': 200,
            'message': '移除成员成功',
            'data': None
        }), 200
        
    except Exception as e:
        logger.error(f'移除赛事成员异常: {str(e)}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500
