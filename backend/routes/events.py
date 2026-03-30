from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Event, User
from datetime import datetime

events_bp = Blueprint('events', __name__)

@events_bp.route('/events', methods=['POST'])
@jwt_required()
def create_event():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or user.user_type not in ['admin', 'teacher']:
            return jsonify({'code': 403, 'message': '权限不足', 'data': None}), 403
        
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
            category=data.get('category'),
            location=data.get('location'),
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
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'event_id': event.event_id,
                'event_name': event.event_name,
                'description': event.description,
                'category': event.category,
                'location': event.location,
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
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        status = request.args.get('status')
        category = request.args.get('category')
        
        query = Event.query.filter_by(is_deleted=False)
        
        if status:
            query = query.filter_by(status=status)
        if category:
            query = query.filter_by(category=category)
        
        total = query.count()
        events = query.order_by(Event.created_at.desc()).paginate(page=page, per_page=page_size, error_out=False)
        
        events_data = []
        for event in events.items:
            events_data.append({
                'event_id': event.event_id,
                'event_name': event.event_name,
                'description': event.description,
                'category': event.category,
                'location': event.location,
                'status': event.status,
                'event_start_time': event.event_start_time.isoformat() if event.event_start_time else None,
                'event_end_time': event.event_end_time.isoformat() if event.event_end_time else None,
                'total_budget': float(event.total_budget),
                'reimbursed_amount': float(event.reimbursed_amount),
                'remaining_budget': float(event.remaining_budget),
                'invoice_count': event.invoice_count
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
        if 'category' in data:
            event.category = data['category']
        if 'location' in data:
            event.location = data['location']
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
        
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'event_id': event.event_id,
                'event_name': event.event_name,
                'description': event.description,
                'category': event.category,
                'location': event.location,
                'status': event.status,
                'event_start_time': event.event_start_time.isoformat() if event.event_start_time else None,
                'event_end_time': event.event_end_time.isoformat() if event.event_end_time else None,
                'upload_start_time': event.upload_start_time.isoformat() if event.upload_start_time else None,
                'upload_end_time': event.upload_end_time.isoformat() if event.upload_end_time else None,
                'creator_id': event.creator_id,
                'leader_id': event.leader_id,
                'total_budget': float(event.total_budget),
                'reimbursed_amount': float(event.reimbursed_amount),
                'remaining_budget': float(event.remaining_budget)
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500

@events_bp.route('/events/<int:event_id>', methods=['GET'])
@jwt_required()
def get_event(event_id):
    try:
        event = Event.query.filter_by(event_id=event_id, is_deleted=False).first()
        
        if not event:
            return jsonify({'code': 2001, 'message': '赛事不存在', 'data': None}), 404
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'event_id': event.event_id,
                'event_name': event.event_name,
                'description': event.description,
                'category': event.category,
                'location': event.location,
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
        }), 200
        
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500
