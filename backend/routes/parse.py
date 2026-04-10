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
        logger.info(f'文件大小: {len(file_bytes)} bytes, 格式: {file_ext}')
        
        # 计算原始文件的MD5值（用于重复检测）
        import hashlib
        original_md5 = hashlib.md5(file_bytes).hexdigest()
        
        # 检查是否存在相同MD5的文件（防止重复上传）
        from models import PurchaseRecord, Voucher
        existing_record = PurchaseRecord.query.filter_by(
            invoice_md5=original_md5,
            is_deleted=False
        ).first()
        
        if existing_record:
            logger.warning(f'检测到重复发票文件，MD5: {original_md5}')
            return jsonify({
                'code': 409,
                'message': f'该发票文件已存在（由{existing_record.uploader.real_name if existing_record.uploader else "未知用户"}于{existing_record.created_at.strftime("%Y-%m-%d %H:%M")}上传）',
                'data': {
                    'duplicate': True,
                    'original_uploader': existing_record.uploader.real_name if existing_record.uploader else None,
                    'upload_time': existing_record.created_at.isoformat() if existing_record.created_at else None
                }
            }), 409
        
        # 处理PDF转图片逻辑
        image_bytes_for_ai = file_bytes
        preview_image_bytes = file_bytes
        converted_from_pdf = False
        
        if file_ext == 'pdf':
            logger.info('检测到PDF文件，开始转换为图片...')
            try:
                import fitz
                import io
                
                pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
                
                if len(pdf_document) > 0:
                    page = pdf_document[0]
                    
                    # 设置高分辨率以保证GLM识别质量
                    mat = fitz.Matrix(2.0, 2.0)
                    pix = page.get_pixmap(matrix=mat)
                    
                    # 转换为PNG格式的图片字节
                    img_buffer = io.BytesIO()
                    pix.save(img_buffer, format='PNG')
                    image_bytes_for_ai = img_buffer.getvalue()
                    preview_image_bytes = img_buffer.getvalue()
                    
                    converted_from_pdf = True
                    logger.info(f'PDF成功转换为图片，尺寸: {pix.width}x{pix.height}, 大小: {len(image_bytes_for_ai)} bytes')
                    
                    # 更新文件扩展名为png用于存储
                    file_ext = 'png'
                    
                pdf_document.close()
                
            except ImportError:
                logger.warning('PyMuPDF库未安装，PDF将直接处理')
            except Exception as e:
                logger.error(f'PDF转图片失败: {str(e)}，将继续使用原始文件')
        
        unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
        cos_path = f"uploads/{unique_filename}"
        
        image_url = None
        preview_url = None
        
        # 上传原始文件或转换后的图片到COS
        upload_bytes = preview_image_bytes if converted_from_pdf else file_bytes
        
        if cos_manager.is_available():
            try:
                image_url = cos_manager.upload_bytes(upload_bytes, cos_path)
                logger.info(f'文件上传成功: {image_url}')
                
                # 如果是图片格式，直接作为预览URL
                if file_ext in ['png', 'jpg', 'jpeg']:
                    preview_url = image_url
                elif converted_from_pdf:
                    # PDF已转换为图片，使用同一个URL
                    preview_url = image_url
                    
            except Exception as e:
                logger.error(f'COS上传失败: {str(e)}')
                # 保存到本地
                import os
                local_uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
                if not os.path.exists(local_uploads_dir):
                    os.makedirs(local_uploads_dir)
                
                local_file_path = os.path.join(local_uploads_dir, unique_filename)
                with open(local_file_path, 'wb') as f:
                    f.write(upload_bytes)
                
                # 验证文件保存
                saved_size = os.path.getsize(local_file_path) if os.path.exists(local_file_path) else 0
                logger.info(f'💾 COS上传失败，已回退到本地存储: {local_file_path}')
                logger.info(f'📊 本地文件大小: {saved_size} bytes')
                
                image_url = f'/uploads/{unique_filename}'
                preview_url = image_url if converted_from_pdf else None
        else:
            # COS不可用，直接保存到本地
            import os
            local_uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
            if not os.path.exists(local_uploads_dir):
                os.makedirs(local_uploads_dir)
            
            local_file_path = os.path.join(local_uploads_dir, unique_filename)
            with open(local_file_path, 'wb') as f:
                f.write(upload_bytes)
            
            # 验证文件是否保存成功
            saved_size = os.path.getsize(local_file_path) if os.path.exists(local_file_path) else 0
            logger.info(f'💾 文件已保存到本地: {local_file_path}')
            logger.info(f'📊 文件大小: {saved_size} bytes (原始: {len(upload_bytes)} bytes)')
            
            image_url = f'/uploads/{unique_filename}'
            preview_url = image_url if converted_from_pdf else None
            logger.info(f'🔗 生成的访问URL: {image_url}')
            logger.warning(f'COS服务不可用，使用本地存储模式')
        
        # 计算最终上传文件的MD5
        file_md5 = hashlib.md5(upload_bytes).hexdigest() if upload_bytes else original_md5
        
        # 调用GLM-4.6V-Flash视觉推理模型进行发票信息提取
        parsed_info = None
        
        if invoice_parser.is_available():
            logger.info('开始调用AI模型解析发票...')
            
            # 使用转换后的图片进行AI识别（如果是PDF的话）
            result = invoice_parser.parse_file(image_bytes_for_ai, f'{unique_filename}.png' if converted_from_pdf else file.filename)
            
            if result.get('success'):
                logger.info('✅ AI发票解析成功')
                parsed_info = result.get('data')
                
                # 确保返回的字段符合前端需求（仅包含：商品名称、发票号码、金额、开票时间）
                if parsed_info:
                    parsed_info = {
                        'item_name': parsed_info.get('project_name', '') or parsed_info.get('item_name', ''),
                        'invoice_number': parsed_info.get('invoice_number', ''),
                        'amount': parsed_info.get('total_amount', 0) or parsed_info.get('amount', 0),
                        'date': parsed_info.get('invoice_date', '')
                    }
                    logger.info(f'标准化解析结果: {parsed_info}')
            else:
                logger.warning(f'⚠️ AI解析失败: {result.get("message")}')
        else:
            logger.warning('AI解析服务不可用，仅返回文件URL')
        
        return jsonify({
            'code': 200,
            'message': '解析完成' if parsed_info else '文件上传成功（AI解析不可用）',
            'data': {
                'image_url': image_url,
                'preview_url': preview_url,
                'file_md5': file_md5,
                'original_file_md5': original_md5,
                'converted_from_pdf': converted_from_pdf,
                'parsed_info': parsed_info,
                'extraction_method': 'glm_vision' if parsed_info else None
            }
        }), 200
        
    except Exception as e:
        logger.error(f'发票解析异常: {str(e)}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': f'解析失败: {str(e)}',
            'data': None
        }), 500
