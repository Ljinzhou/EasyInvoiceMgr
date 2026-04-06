from flask import Blueprint, request, jsonify, make_response
from flask_cors import cross_origin
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.invoice_parser import invoice_parser
from utils.cos_manager import cos_manager
import logging
import uuid
import os

logger = logging.getLogger(__name__)
parse_bp = Blueprint('parse', __name__)

@parse_bp.route('/upload-file', methods=['POST', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000', 'http://127.0.0.1:3000'], supports_credentials=True)
def upload_file():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response
    
    try:
        from flask_jwt_extended import verify_jwt_in_request
        verify_jwt_in_request()
        current_user_id = get_jwt_identity()
        logger.info(f'用户ID: {current_user_id}')
    except Exception as e:
        logger.warning(f'JWT验证失败: {str(e)}')
        return jsonify({'code': 401, 'message': '请先登录', 'data': None}), 401
    
    logger.info('=== 文件上传请求（不解析）===')
    try:
        
        if 'file' not in request.files:
            logger.warning('请求中没有文件')
            return jsonify({'code': 400, 'message': '请上传文件', 'data': None}), 400
        
        file = request.files['file']
        logger.info(f'收到文件: {file.filename}')
        
        if file.filename == '':
            logger.warning('文件名为空')
            return jsonify({'code': 400, 'message': '请选择文件', 'data': None}), 400
        
        allowed_extensions = {'pdf', 'png', 'jpg', 'jpeg'}
        
        if '.' not in file.filename:
            logger.warning(f'文件名没有扩展名: {file.filename}')
            return jsonify({'code': 400, 'message': '文件名需要包含扩展名', 'data': None}), 400
        
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        logger.info(f'文件扩展名: {file_ext}')
        
        if file_ext not in allowed_extensions:
            logger.warning(f'不支持的文件格式: {file_ext}')
            return jsonify({'code': 400, 'message': f'文件格式不支持，请上传 PDF、PNG、JPG 或 JPEG 格式', 'data': None}), 400
        
        file_bytes = file.read()
        logger.info(f'文件大小: {len(file_bytes)} bytes')
        
        unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
        cos_path = f"uploads/{unique_filename}"
        
        image_url = None
        preview_url = None
        
        try:
            if cos_manager.is_available():
                logger.info('COS服务可用，开始上传')
                image_url = cos_manager.upload_bytes(file_bytes, cos_path)
                logger.info(f'文件上传成功: {image_url}')
                
                if file_ext in ['png', 'jpg', 'jpeg']:
                    preview_url = image_url
                elif file_ext == 'pdf':
                    preview_url = cos_manager.get_preview_url(cos_path)
            else:
                logger.warning('COS服务不可用')
                image_url = f'/uploads/{unique_filename}'
        except Exception as e:
            logger.error(f'COS上传失败: {str(e)}', exc_info=True)
            image_url = f'/uploads/{unique_filename}'
        
        file_md5 = None
        try:
            import hashlib
            file_md5 = hashlib.md5(file_bytes).hexdigest()
        except Exception as e:
            logger.warning(f'计算MD5失败: {str(e)}')
        
        logger.info(f'上传完成，返回URL: {image_url}')
        
        return jsonify({
            'code': 200,
            'message': '上传成功',
            'data': {
                'image_url': image_url,
                'preview_url': preview_url,
                'file_md5': file_md5
            }
        }), 200
        
    except Exception as e:
        logger.error(f'文件上传异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': f'上传失败: {str(e)}', 'data': None}), 500

@parse_bp.route('/parse-invoice', methods=['POST'])
@jwt_required()
def parse_invoice():
    logger.info('=== 发票解析请求 ===')
    try:
        current_user_id = get_jwt_identity()
        logger.info(f'当前用户ID: {current_user_id}')
        
        if 'file' not in request.files:
            logger.warning('未上传文件')
            return jsonify({
                'code': 400,
                'message': '请上传发票文件',
                'data': None
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            logger.warning('文件名为空')
            return jsonify({
                'code': 400,
                'message': '请选择文件',
                'data': None
            }), 400
        
        allowed_extensions = {'pdf', 'png', 'jpg', 'jpeg'}
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if file_ext not in allowed_extensions:
            logger.warning(f'文件格式不支持: {file_ext}')
            return jsonify({
                'code': 400,
                'message': f'文件格式不支持，请上传 PDF、PNG、JPG 或 JPEG 格式的文件',
                'data': None
            }), 400
        
        file_bytes = file.read()
        logger.info(f'文件大小: {len(file_bytes)} bytes')
        
        unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
        cos_path = f"uploads/{unique_filename}"
        
        image_url = None
        preview_url = None
        
        if cos_manager.is_available():
            try:
                image_url = cos_manager.upload_bytes(file_bytes, cos_path)
                logger.info(f'文件上传成功: {image_url}')
                
                if file_ext in ['png', 'jpg', 'jpeg']:
                    preview_url = image_url
                elif file_ext == 'pdf':
                    preview_url = cos_manager.get_preview_url(cos_path)
            except Exception as e:
                logger.error(f'文件上传失败: {str(e)}')
                image_url = f'/uploads/{unique_filename}'
        else:
            image_url = f'/uploads/{unique_filename}'
            logger.warning('COS服务不可用，使用本地路径')
        
        file_md5 = None
        try:
            import hashlib
            file_md5 = hashlib.md5(file_bytes).hexdigest()
        except:
            pass
        
        if not invoice_parser.is_available():
            logger.warning('OCR服务不可用，仅返回文件URL')
            return jsonify({
                'code': 200,
                'message': '文件上传成功（OCR服务不可用）',
                'data': {
                    'image_url': image_url,
                    'preview_url': preview_url,
                    'file_md5': file_md5,
                    'parsed_info': None
                }
            }), 200
        
        result = invoice_parser.parse_file(file_bytes, file.filename)
        
        if result['success']:
            logger.info('发票解析成功')
            return jsonify({
                'code': 200,
                'message': '解析成功',
                'data': {
                    'image_url': image_url,
                    'preview_url': preview_url,
                    'file_md5': file_md5,
                    'parsed_info': result.get('data'),
                    'raw_text': result.get('raw_text', '')
                }
            }), 200
        else:
            logger.warning(f'发票解析失败: {result["message"]}，返回文件URL')
            return jsonify({
                'code': 200,
                'message': f'文件上传成功，但解析失败: {result["message"]}',
                'data': {
                    'image_url': image_url,
                    'preview_url': preview_url,
                    'file_md5': file_md5,
                    'parsed_info': None
                }
            }), 200
        
    except Exception as e:
        logger.error(f'发票解析异常: {str(e)}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': f'解析失败: {str(e)}',
            'data': None
        }), 500
