from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Event, ExportTask
from datetime import datetime, timezone
import threading
import os
import logging

logger = logging.getLogger(__name__)
export_bp = Blueprint('export', __name__)

export_service = None


def init_export_service(app):
    global export_service
    from utils.export_service import ExportService
    export_service = ExportService(app)


@export_bp.route('/events/<int:event_id>/export', methods=['POST'])
@jwt_required()
def start_export(event_id):
    try:
        current_user_id = get_jwt_identity()
        user = db.session.get(User, current_user_id)
        if not user:
            return jsonify({'code': 401, 'message': '用户不存在', 'data': None}), 401

        event = db.session.get(Event, event_id)
        if not event or event.is_deleted:
            return jsonify({'code': 2001, 'message': '赛事不存在', 'data': None}), 404

        data = request.get_json() or {}
        columns = data.get('columns', [])
        options = data.get('options', {})

        if not columns:
            return jsonify({'code': 400, 'message': '请至少选择一个导出列', 'data': None}), 400

        columns_config = {'columns': columns, 'options': options}

        cached_task = export_service.check_cache(event_id, columns_config)
        if cached_task:
            return jsonify({
                'code': 200,
                'message': '存在缓存的导出结果',
                'data': {
                    'task_id': cached_task.task_id,
                    'status': cached_task.status,
                    'cached': True
                }
            })

        task = ExportTask(
            event_id=event_id,
            requester_id=current_user_id,
            status='pending',
            columns_config=columns_config
        )
        db.session.add(task)
        db.session.commit()

        thread = threading.Thread(
            target=export_service.run_export,
            args=(task.task_id,),
            daemon=True
        )
        thread.start()

        logger.info(f'导出任务已创建: task_id={task.task_id}, event_id={event_id}')

        return jsonify({
            'code': 200,
            'message': '导出任务已创建',
            'data': {
                'task_id': task.task_id,
                'status': 'pending'
            }
        })

    except Exception as e:
        logger.error(f'创建导出任务异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


@export_bp.route('/events/<int:event_id>/export/status', methods=['GET'])
@jwt_required()
def export_status(event_id):
    try:
        task_id = request.args.get('task_id', type=int)
        if not task_id:
            return jsonify({'code': 400, 'message': '缺少task_id参数', 'data': None}), 400

        task = db.session.get(ExportTask, task_id)
        if not task or task.event_id != event_id:
            return jsonify({'code': 404, 'message': '导出任务不存在', 'data': None}), 404

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'task_id': task.task_id,
                'status': task.status,
                'progress_percent': task.progress_percent or 0,
                'progress_message': task.progress_message or '',
                'record_count': task.record_count,
                'file_size': task.file_size,
                'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S') if task.created_at else None,
                'completed_at': task.completed_at.strftime('%Y-%m-%d %H:%M:%S') if task.completed_at else None,
                'error_message': task.error_message
            }
        })

    except Exception as e:
        logger.error(f'查询导出状态异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


@export_bp.route('/events/<int:event_id>/export/download', methods=['GET'])
@jwt_required()
def download_export(event_id):
    try:
        task_id = request.args.get('task_id', type=int)
        if not task_id:
            return jsonify({'code': 400, 'message': '缺少task_id参数', 'data': None}), 400

        task = db.session.get(ExportTask, task_id)
        if not task or task.event_id != event_id:
            return jsonify({'code': 404, 'message': '导出任务不存在', 'data': None}), 404

        if task.status != 'completed':
            return jsonify({'code': 400, 'message': '导出任务尚未完成', 'data': None}), 400

        if task.expires_at and task.expires_at < datetime.now(timezone.utc):
            return jsonify({'code': 410, 'message': '导出文件已过期，请重新导出', 'data': None}), 410

        if not task.file_path or not os.path.exists(task.file_path):
            return jsonify({'code': 404, 'message': '导出文件不存在', 'data': None}), 404

        return send_file(
            task.file_path,
            as_attachment=True,
            download_name=os.path.basename(task.file_path)
        )

    except Exception as e:
        logger.error(f'下载导出文件异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500
