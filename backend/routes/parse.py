from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.invoice_parser import invoice_parser
import logging

logger = logging.getLogger(__name__)
parse_bp = Blueprint('parse', __name__)

@parse_bp.route('/parse-invoice', methods=['POST'])
@jwt_required()
def parse_invoice():
    logger.info('=== 发票解析请求 ===')
    try:
        current_user_id = get_jwt_identity()
        logger.info(f'当前用户ID: {current_user_id}')
        
        if not invoice_parser.is_available():
            logger.warning('OCR服务不可用')
            return jsonify({
                'code': 503,
                'message': 'OCR服务不可用，请安装cnocr库: pip install cnocr',
                'data': None
            }), 503
        
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
        
        result = invoice_parser.parse_file(file_bytes, file.filename)
        
        if result['success']:
            logger.info('发票解析成功')
            return jsonify({
                'code': 200,
                'message': '解析成功',
                'data': result['data'],
                'raw_text': result.get('raw_text', '')
            }), 200
        else:
            logger.warning(f'发票解析失败: {result["message"]}')
            return jsonify({
                'code': 400,
                'message': result['message'],
                'data': None
            }), 400
        
    except Exception as e:
        logger.error(f'发票解析异常: {str(e)}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': f'解析失败: {str(e)}',
            'data': None
        }), 500
