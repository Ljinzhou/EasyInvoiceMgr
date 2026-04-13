from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Event, PurchaseRecord, Invoice
from datetime import datetime
import pandas as pd
import os
import tempfile
import zipfile
from PyPDF2 import PdfMerger
from fpdf import FPDF
from io import BytesIO
import logging

logger = logging.getLogger(__name__)
export_bp = Blueprint('export', __name__)

@export_bp.route('/events/<int:event_id>/export', methods=['GET'])
@jwt_required()
def export_event_data(event_id):
    logger.info(f'=== 导出赛事数据请求: event_id={event_id} ===')
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({'code': 401, 'message': '用户不存在', 'data': None}), 401
        
        event = Event.query.filter_by(event_id=event_id, is_deleted=False).first()
        if not event:
            return jsonify({'code': 2001, 'message': '赛事不存在', 'data': None}), 404
        
        # 获取所有购买记录和发票
        purchase_records = PurchaseRecord.query.filter_by(event_id=event_id, is_deleted=False).all()
        invoices = Invoice.query.filter_by(event_id=event_id, is_deleted=False).all()
        
        # 合并数据并按时间排序
        all_records = []
        
        # 添加购买记录
        for record in purchase_records:
            uploader = User.query.get(record.uploader_id)
            uploader_name = uploader.real_name if uploader else '未知'
            
            record_data = {
                'type': 'purchase',
                'id': f'P{record.record_id}',
                'item_name': record.item_name,
                'purchase_platform': record.purchase_platform,
                'amount': float(record.amount),
                'purchase_date': record.purchase_date.strftime('%Y-%m-%d') if record.purchase_date else '',
                'uploader': uploader_name,
                'has_invoice': record.has_invoice,
                'invoice_number': record.invoice_number or '',
                'invoice_date': record.invoice_date.strftime('%Y-%m-%d') if record.invoice_date else '',
                'total_amount': float(record.total_amount) if record.total_amount else 0,
                'status': record.status,
                'is_reimbursed': record.is_reimbursed,
                'remarks': record.remarks or '',
                'created_at': record.created_at.strftime('%Y-%m-%d %H:%M:%S') if record.created_at else ''
            }
            all_records.append(record_data)
        
        # 添加发票记录
        for invoice in invoices:
            uploader = User.query.get(invoice.uploader_id)
            uploader_name = uploader.real_name if uploader else '未知'
            
            invoice_data = {
                'type': 'invoice',
                'id': f'I{invoice.invoice_id}',
                'item_name': invoice.project_name,
                'purchase_platform': '发票上传',
                'amount': float(invoice.amount),
                'purchase_date': invoice.invoice_date.strftime('%Y-%m-%d') if invoice.invoice_date else '',
                'uploader': uploader_name,
                'has_invoice': True,
                'invoice_number': invoice.invoice_number or '',
                'invoice_date': invoice.invoice_date.strftime('%Y-%m-%d') if invoice.invoice_date else '',
                'total_amount': float(invoice.total_amount),
                'status': invoice.status,
                'is_reimbursed': invoice.is_reimbursed,
                'remarks': invoice.remarks or '',
                'created_at': invoice.created_at.strftime('%Y-%m-%d %H:%M:%S') if invoice.created_at else ''
            }
            all_records.append(invoice_data)
        
        # 按创建时间排序
        all_records.sort(key=lambda x: x['created_at'])
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. 生成Excel文件
            excel_file = os.path.join(temp_dir, f'{event.event_name}_购物信息.xlsx')
            df = pd.DataFrame(all_records)
            df.to_excel(excel_file, index=False, sheet_name='购物记录')
            
            # 2. 收集发票PDF文件
            invoice_pdfs = []
            merged_pdf = PdfMerger()
            
            # 获取上传目录路径
            uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
            
            for record in all_records:
                if record['has_invoice']:
                    # 尝试从数据库获取实际的发票文件路径
                    if record['type'] == 'purchase':
                        # 从PurchaseRecord表获取
                        purchase_record = PurchaseRecord.query.filter_by(record_id=record['id'].replace('P', ''), is_deleted=False).first()
                        if purchase_record and purchase_record.invoice_file_key:
                            # 提取文件名
                            if purchase_record.invoice_file_key.startswith('/uploads/'):
                                filename = purchase_record.invoice_file_key.replace('/uploads/', '')
                                invoice_file = os.path.join(uploads_dir, filename)
                                if os.path.exists(invoice_file):
                                    invoice_pdfs.append(invoice_file)
                                    merged_pdf.append(invoice_file)
                    elif record['type'] == 'invoice':
                        # 从Invoice表获取
                        invoice_record = Invoice.query.filter_by(invoice_id=record['id'].replace('I', ''), is_deleted=False).first()
                        if invoice_record and invoice_record.image_url:
                            # 提取文件名
                            if invoice_record.image_url.startswith('/uploads/'):
                                filename = invoice_record.image_url.replace('/uploads/', '')
                                invoice_file = os.path.join(uploads_dir, filename)
                                if os.path.exists(invoice_file):
                                    invoice_pdfs.append(invoice_file)
                                    merged_pdf.append(invoice_file)
            
            # 3. 生成合并PDF
            merged_pdf_file = os.path.join(temp_dir, f'{event.event_name}_发票汇总.pdf')
            if invoice_pdfs:
                merged_pdf.write(merged_pdf_file)
                merged_pdf.close()
            
            # 4. 打包所有发票为单独的PDF文件
            invoices_zip = os.path.join(temp_dir, f'{event.event_name}_发票单独打包.zip')
            if invoice_pdfs:
                with zipfile.ZipFile(invoices_zip, 'w') as zf:
                    for pdf_file in invoice_pdfs:
                        zf.write(pdf_file, os.path.basename(pdf_file))
            
            # 5. 生成最终压缩包
            final_zip = os.path.join(temp_dir, f'{event.event_name}_导出数据.zip')
            with zipfile.ZipFile(final_zip, 'w') as zf:
                zf.write(excel_file, os.path.basename(excel_file))
                if os.path.exists(merged_pdf_file):
                    zf.write(merged_pdf_file, os.path.basename(merged_pdf_file))
                if os.path.exists(invoices_zip):
                    zf.write(invoices_zip, os.path.basename(invoices_zip))
            
            # 6. 发送文件
            return send_file(final_zip, as_attachment=True, download_name=os.path.basename(final_zip))
            
    except Exception as e:
        logger.error(f'导出数据异常: {str(e)}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e), 'data': None}), 500
