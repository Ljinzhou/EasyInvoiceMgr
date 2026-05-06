from flask import Blueprint, request, jsonify, make_response
from flask_cors import cross_origin
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.invoice_parser import invoice_parser
from utils.cos_manager import cos_manager
from utils.glm_vision_service import GLMVisionService
import logging
import uuid
import os
import hashlib
import io

logger = logging.getLogger(__name__)
parse_bp = Blueprint('parse', __name__)


class PDFConverter:
    """PDF转JPG服务端转换器（需安装PyMuPDF或其他渲染库）"""

    @staticmethod
    def is_pdf_available():
        """检查PDF渲染库是否可用（PyPDF2不支持渲染，需要额外安装fitz或pdf2image）"""
        try:
            import fitz
            return True
        except ImportError:
            try:
                from pdf2image import convert_from_bytes
                return True
            except ImportError:
                return False

    @staticmethod
    def convert_pdf_to_jpg(pdf_bytes: bytes, dpi: float = 2.0) -> tuple:
        """
        将PDF转换为JPG图片

        Args:
            pdf_bytes: PDF文件字节流
            dpi: 分辨率倍数，默认2.0表示双倍分辨率

        Returns:
            tuple: (jpg_bytes, width, height, page_count) 或 (None, None, None, 0) 失败时
        """
        try:
            import fitz
            from PIL import Image

            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            page_count = len(pdf_document)

            if page_count == 0:
                logger.warning('PDF文件没有页面')
                pdf_document.close()
                return None, None, None, 0

            page = pdf_document[0]
            mat = fitz.Matrix(dpi, dpi)
            pix = page.get_pixmap(matrix=mat)

            img_buffer = io.BytesIO()

            try:
                pix.pil_save(img_buffer, format='JPEG', quality=95)
            except AttributeError:
                img_data = pix.tobytes('jpeg', jpeg_quality=95)
                img_buffer.write(img_data)

            jpg_bytes = img_buffer.getvalue()

            width, height = pix.width, pix.height
            pdf_document.close()

            logger.info(f'PDF转JPG成功: 尺寸={width}x{height}, 页数={page_count}, 大小={len(jpg_bytes)} bytes')
            return jpg_bytes, width, height, page_count

        except ImportError:
            logger.error('PDF渲染库未安装，无法转换PDF为图片')
            return None, None, None, 0
        except Exception as e:
            logger.error(f'PDF转JPG失败: {str(e)}', exc_info=True)
            return None, None, None, 0


class InvoiceUploadService:
    """发票上传服务"""
    
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
    
    @staticmethod
    def validate_file(file) -> dict:
        """
        验证上传的文件
        
        Returns:
            dict: {'valid': bool, 'error': str, 'ext': str, 'bytes': bytes}
        """
        if not file:
            return {'valid': False, 'error': '请上传发票文件'}
        
        if file.filename == '':
            return {'valid': False, 'error': '请选择文件'}
        
        if '.' not in file.filename:
            return {'valid': False, 'error': '文件名需要包含扩展名'}
        
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        if file_ext not in InvoiceUploadService.ALLOWED_EXTENSIONS:
            return {'valid': False, 'error': f'文件格式不支持，请上传 PDF、PNG、JPG 或 JPEG 格式的文件'}
        
        try:
            file_bytes = file.read()
        except Exception as e:
            return {'valid': False, 'error': f'读取文件失败: {str(e)}'}
        
        return {
            'valid': True,
            'ext': file_ext,
            'bytes': file_bytes,
            'original_filename': file.filename
        }
    
    @staticmethod
    def check_duplicate(md5: str) -> dict:
        """检查文件是否重复"""
        from models import PurchaseRecord
        
        existing = PurchaseRecord.query.filter_by(
            invoice_md5=md5,
            is_deleted=False
        ).first()
        
        if existing:
            return {
                'duplicate': True,
                'uploader': existing.uploader.real_name if existing.uploader else '未知用户',
                'upload_time': existing.created_at.strftime('%Y-%m-%d %H:%M') if existing.created_at else '未知时间'
            }
        return {'duplicate': False}
    
    @staticmethod
    def upload_to_storage(file_bytes: bytes, file_key: str, content_type: str = None) -> bool:
        """上传文件到对象存储"""
        if cos_manager.is_available():
            try:
                extra_args = {}
                if content_type:
                    extra_args['ContentType'] = content_type
                
                cos_manager.client.put_object(
                    Bucket=cos_manager.bucket,
                    Body=file_bytes,
                    Key=file_key,
                    EnableMD5=False,
                    **extra_args
                )
                logger.info(f'文件上传到COS成功: {file_key}')
                return True
            except Exception as e:
                logger.error(f'COS上传失败: {str(e)}', exc_info=True)
                return False
        else:
            logger.warning('COS服务不可用，无法上传')
            return False
    
    @staticmethod
    def save_to_local(file_bytes: bytes, filename: str, uploads_dir: str) -> bool:
        """保存文件到本地存储"""
        try:
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir)
            
            local_path = os.path.join(uploads_dir, filename)
            with open(local_path, 'wb') as f:
                f.write(file_bytes)
            
            logger.info(f'文件保存到本地成功: {local_path}')
            return True
        except Exception as e:
            logger.error(f'本地保存失败: {str(e)}', exc_info=True)
            return False


@parse_bp.route('/upload-file', methods=['POST', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000', 'http://localhost:3001', 'http://127.0.0.1:3000', 'http://127.0.0.1:3001'], supports_credentials=True)
def upload_file():
    if request.method == 'OPTIONS':
        response = make_response()
        origin = request.headers.get('Origin', 'http://localhost:3001')
        response.headers.add('Access-Control-Allow-Origin', origin)
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
    
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传文件', 'data': None}), 400
    
    file = request.files['file']
    validation = InvoiceUploadService.validate_file(file)
    
    if not validation['valid']:
        return jsonify({'code': 400, 'message': validation['error'], 'data': None}), 400
    
    file_bytes = validation['bytes']
    file_ext = validation['ext']
    original_filename = validation['original_filename']
    
    logger.info(f'收到文件: {original_filename}, 大小: {len(file_bytes)} bytes, 格式: {file_ext}')
    
    unique_id = uuid.uuid4().hex
    file_key = f"invoices/{unique_id}.{file_ext}"
    
    content_type_map = {
        'pdf': 'application/pdf',
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg'
    }
    
    if cos_manager.is_available():
        success = InvoiceUploadService.upload_to_storage(
            file_bytes, 
            file_key, 
            content_type_map.get(file_ext)
        )
        if not success:
            return jsonify({'code': 500, 'message': '文件上传失败', 'data': None}), 500
    else:
        uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
        local_filename = f"{unique_id}.{file_ext}"
        if not InvoiceUploadService.save_to_local(file_bytes, local_filename, uploads_dir):
            return jsonify({'code': 500, 'message': '文件保存失败', 'data': None}), 500
        file_key = f"/uploads/{local_filename}"
    
    file_md5 = hashlib.md5(file_bytes).hexdigest()
    
    preview_url = None
    if cos_manager.is_available() and file_key.startswith('invoices/'):
        preview_url = cos_manager.get_presigned_url(file_key, expires=3600 * 24)
    elif file_key.startswith('/uploads/'):
        preview_url = file_key
    
    return jsonify({
        'code': 200,
        'message': '上传成功',
        'data': {
            'image_url': preview_url,
            'file_key': file_key,
            'preview_url': preview_url,
            'file_md5': file_md5,
            'original_filename': original_filename,
            'file_type': file_ext
        }
    }), 200


@parse_bp.route('/parse-image', methods=['POST'])
@jwt_required()
def parse_image():
    """
    仅对图片进行AI解析，不上传到COS。
    用于客户端已将PDF转为图片后，直接发送图片进行解析。
    """
    logger.info('=== 图片AI解析请求（不上传） ===')
    try:
        if 'file' not in request.files:
            return jsonify({'code': 400, 'message': '请上传图片文件', 'data': None}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'code': 400, 'message': '请选择文件', 'data': None}), 400

        file_bytes = file.read()
        if not file_bytes:
            return jsonify({'code': 400, 'message': '文件为空', 'data': None}), 400

        mime_type = GLMVisionService._detect_mime_type(file_bytes, file.filename)
        if mime_type == 'application/pdf':
            return jsonify({'code': 400, 'message': '请上传图片文件，不支持PDF', 'data': None}), 400

        logger.info(f'收到图片: {file.filename}, 格式: {mime_type}, 大小: {len(file_bytes)} bytes')

        parsed_info = None
        if invoice_parser.is_available():
            result = invoice_parser.parse_file(file_bytes, file.filename)
            if result.get('success'):
                raw = result.get('data', {})
                parsed_info = {
                    'item_name': raw.get('project_name', '') or raw.get('item_name', ''),
                    'invoice_number': raw.get('invoice_number', ''),
                    'amount': raw.get('total_amount', 0) or raw.get('amount', 0),
                    'date': raw.get('invoice_date', '')
                }
                logger.info(f'AI解析成功: {parsed_info}')
            else:
                logger.warning(f'AI解析失败: {result.get("message")}')

        return jsonify({
            'code': 200,
            'message': '解析完成' if parsed_info else 'AI解析服务不可用',
            'data': {
                'parsed_info': parsed_info,
                'filename': file.filename
            }
        }), 200

    except Exception as e:
        logger.error(f'图片解析失败: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


@parse_bp.route('/parse-invoice', methods=['POST'])
@jwt_required()
def parse_invoice():
    logger.info('=== 发票解析请求 ===')
    
    try:
        current_user_id = get_jwt_identity()
        logger.info(f'当前用户ID: {current_user_id}')
    except Exception as e:
        logger.warning(f'JWT验证失败: {str(e)}')
        return jsonify({'code': 401, 'message': '请先登录', 'data': None}), 401
    
    try:
        if 'file' not in request.files:
            return jsonify({'code': 400, 'message': '请上传发票文件', 'data': None}), 400
        
        file = request.files['file']
        validation = InvoiceUploadService.validate_file(file)
        
        if not validation['valid']:
            return jsonify({'code': 400, 'message': validation['error'], 'data': None}), 400
        
        file_bytes = validation['bytes']
        file_ext = validation['ext']
        original_filename = validation['original_filename']
        
        logger.info(f'文件: {original_filename}, 大小: {len(file_bytes)} bytes, 格式: {file_ext}')
        
        original_md5 = hashlib.md5(file_bytes).hexdigest()
        
        duplicate_check = InvoiceUploadService.check_duplicate(original_md5)
        if duplicate_check['duplicate']:
            logger.warning(f'检测到重复发票文件，MD5: {original_md5}')
            return jsonify({
                'code': 409,
                'message': f'该发票文件已存在（由{duplicate_check["uploader"]}于{duplicate_check["upload_time"]}上传）',
                'data': {
                    'duplicate': True,
                    'original_uploader': duplicate_check['uploader'],
                    'upload_time': duplicate_check['upload_time']
                }
            }), 409
        
        unique_id = uuid.uuid4().hex
        
        is_pdf = file_ext == 'pdf'
        jpg_bytes = None
        pdf_page_count = 0

        # 接收客户端传来的预览图（可选）
        client_preview_bytes = None
        if 'preview_file' in request.files:
            try:
                client_preview_bytes = request.files['preview_file'].read()
                logger.info(f'收到客户端预览图: {len(client_preview_bytes)} bytes')
            except Exception as e:
                logger.warning(f'读取客户端预览图失败: {e}')

        if is_pdf:
            logger.info('检测到PDF文件，尝试服务端渲染转换...')
            jpg_bytes, jpg_width, jpg_height, pdf_page_count = PDFConverter.convert_pdf_to_jpg(file_bytes)

            # 服务端转换失败时，使用客户端传来的预览图
            if jpg_bytes is None and client_preview_bytes:
                jpg_bytes = client_preview_bytes
                logger.info('使用客户端提供的预览图作为PDF预览')

            if jpg_bytes is None:
                logger.warning('PDF渲染转换失败（渲染库不可用且无客户端预览图）')
        
        invoice_file_key = f"invoices/{unique_id}.{file_ext}"
        preview_file_key = None
        
        content_type_map = {
            'pdf': 'application/pdf',
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg'
        }
        
        if cos_manager.is_available():
            upload_success = InvoiceUploadService.upload_to_storage(
                file_bytes,
                invoice_file_key,
                content_type_map.get(file_ext)
            )
            
            if not upload_success:
                return jsonify({
                    'code': 500,
                    'message': '发票文件上传失败',
                    'data': None
                }), 500
            
            if is_pdf and jpg_bytes:
                preview_file_key = f"invoices/{unique_id}_preview.jpg"
                preview_success = InvoiceUploadService.upload_to_storage(
                    jpg_bytes,
                    preview_file_key,
                    'image/jpeg'
                )
                
                if not preview_success:
                    logger.warning('预览图上传失败，将使用原始PDF')
                    preview_file_key = None
            
            logger.info(f'文件上传成功: 原始文件={invoice_file_key}, 预览图={preview_file_key}')
        else:
            uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
            
            local_filename = f"{unique_id}.{file_ext}"
            if not InvoiceUploadService.save_to_local(file_bytes, local_filename, uploads_dir):
                return jsonify({'code': 500, 'message': '文件保存失败', 'data': None}), 500
            
            invoice_file_key = f"/uploads/{local_filename}"
            
            if is_pdf and jpg_bytes:
                preview_filename = f"{unique_id}_preview.jpg"
                if InvoiceUploadService.save_to_local(jpg_bytes, preview_filename, uploads_dir):
                    preview_file_key = f"/uploads/{preview_filename}"
            
            logger.info(f'本地存储: 原始文件={invoice_file_key}, 预览图={preview_file_key}')
        
        # 确定用于AI解析的图片字节：PDF必须先转为图片，否则跳过AI解析
        if is_pdf and not jpg_bytes:
            image_bytes_for_ai = None
            logger.warning('PDF转图片失败，跳过AI解析（视觉模型不支持原始PDF）')
        elif is_pdf and jpg_bytes:
            image_bytes_for_ai = jpg_bytes
        else:
            image_bytes_for_ai = file_bytes

        parsed_info = None
        if image_bytes_for_ai and invoice_parser.is_available():
            logger.info('开始调用AI模型解析发票...')

            ai_filename = f'{unique_id}.jpg' if is_pdf else original_filename
            result = invoice_parser.parse_file(image_bytes_for_ai, ai_filename)
            
            if result.get('success'):
                logger.info('AI发票解析成功')
                parsed_info = result.get('data')
                
                if parsed_info:
                    parsed_info = {
                        'item_name': parsed_info.get('project_name', '') or parsed_info.get('item_name', ''),
                        'invoice_number': parsed_info.get('invoice_number', ''),
                        'amount': parsed_info.get('total_amount', 0) or parsed_info.get('amount', 0),
                        'date': parsed_info.get('invoice_date', '')
                    }
                    logger.info(f'解析结果: {parsed_info}')
            else:
                logger.warning(f'AI解析失败: {result.get("message")}')
        else:
            logger.warning('AI解析服务不可用')
        
        preview_url = None
        file_url = None
        
        if cos_manager.is_available():
            if invoice_file_key.startswith('invoices/'):
                file_url = cos_manager.get_presigned_url(invoice_file_key, expires=3600 * 24)
            if preview_file_key and preview_file_key.startswith('invoices/'):
                preview_url = cos_manager.get_presigned_url(preview_file_key, expires=3600 * 24)
            elif not preview_file_key and invoice_file_key.startswith('invoices/'):
                preview_url = file_url
        else:
            file_url = invoice_file_key
            preview_url = preview_file_key or invoice_file_key
        
        return jsonify({
            'code': 200,
            'message': '解析完成' if parsed_info else '文件上传成功',
            'data': {
                'file_key': invoice_file_key,
                'preview_key': preview_file_key,
                'file_url': file_url,
                'preview_url': preview_url,
                'original_filename': original_filename,
                'file_type': file_ext,
                'is_pdf': is_pdf,
                'pdf_page_count': pdf_page_count,
                'file_md5': original_md5,
                'parsed_info': parsed_info,
                'extraction_method': 'glm_vision' if parsed_info else None
            }
        }), 200
    
    except Exception as e:
        logger.error(f'发票解析请求处理失败: {str(e)}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': f'服务器处理请求时发生错误: {str(e)}',
            'data': None
        }), 500


@parse_bp.route('/invoices/<path:file_key>/preview', methods=['GET'])
@jwt_required()
def get_invoice_preview_url(file_key):
    """获取发票预览图片的临时访问URL"""
    logger.info(f'=== 获取发票预览URL: {file_key} ===')
    
    try:
        current_user_id = get_jwt_identity()
        
        if cos_manager.is_available():
            preview_url = cos_manager.get_presigned_url(file_key, expires=3600)
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': {'preview_url': preview_url}
            }), 200
        else:
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': {'preview_url': f'/uploads/{file_key}'}
            }), 200
    except Exception as e:
        logger.error(f'获取预览URL失败: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500


@parse_bp.route('/invoices/<path:file_key>/download', methods=['GET'])
@jwt_required()
def download_invoice_file(file_key):
    """下载原始发票文件（PDF）"""
    logger.info(f'=== 下载发票文件: {file_key} ===')
    
    try:
        current_user_id = get_jwt_identity()
        
        if cos_manager.is_available():
            file_bytes = cos_manager.download_file(file_key)
            
            from flask import Response
            content_type = 'application/pdf' if file_key.endswith('.pdf') else 'image/jpeg'
            
            return Response(
                file_bytes,
                mimetype=content_type,
                headers={
                    'Content-Disposition': f'attachment; filename="{file_key.split("/")[-1]}"'
                }
            )
        else:
            uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
            filename = file_key.replace('uploads/', '')
            file_path = os.path.join(uploads_dir, filename)
            
            if not os.path.exists(file_path):
                return jsonify({'code': 404, 'message': '文件不存在', 'data': None}), 404
            
            from flask import send_file
            return send_file(file_path, as_attachment=True)
    except Exception as e:
        logger.error(f'下载发票文件失败: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500
