import os
import io
import re
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

try:
    from utils.glm_vision_service import glm_vision_service
    GLM_AVAILABLE = glm_vision_service.is_available()
    logger.info('GLM视觉模型服务加载成功')
except ImportError:
    GLM_AVAILABLE = False
    logger.warning('GLM视觉模型服务未加载')

try:
    import fitz
    PDF_AVAILABLE = True
    logger.info('PyMuPDF库加载成功，支持PDF直接文本提取')
except ImportError:
    PDF_AVAILABLE = False
    logger.warning('PyMuPDF库未安装，PDF解析功能将不可用')

class InvoiceParser:
    def __init__(self):
        pass
    
    def is_available(self) -> bool:
        return PDF_AVAILABLE or GLM_AVAILABLE
    
    def parse_file(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        if not self.is_available():
            return {
                'success': False,
                'message': '解析服务不可用，请安装PyMuPDF库',
                'data': None
            }
        
        try:
            ext = os.path.splitext(filename)[1].lower()
            logger.info(f'开始解析文件: {filename}, 格式: {ext}')
            
            if ext == '.pdf':
                if not PDF_AVAILABLE:
                    return {
                        'success': False,
                        'message': 'PDF解析功能不可用，请安装PyMuPDF库',
                        'data': None
                    }
                text = self._extract_pdf_text(file_bytes)
                
                if not text or len(text.strip()) < 10:
                    return {
                        'success': False,
                        'message': '未能从PDF中提取到有效的文字内容',
                        'data': None
                    }
                
                invoice_data = self._extract_invoice_data(text)
                
                return {
                    'success': True,
                    'message': '解析成功',
                    'data': invoice_data,
                    'raw_text': text,
                    'extraction_method': 'pdf_direct',
                    'field_permissions': {
                        'readonly': ['invoice_number', 'invoice_date', 'total_amount'],
                        'editable': ['project_name', 'invoice_type']
                    }
                }
                
            elif ext in ['.png', '.jpg', '.jpeg']:
                if GLM_AVAILABLE:
                    logger.info('使用GLM-4.6V-Flash视觉模型识别图片发票')
                    result = glm_vision_service.extract_invoice_info(file_bytes, filename)
                    if result.get('success'):
                        return result
                    else:
                        logger.warning(f'GLM视觉模型提取失败: {result.get("message")}')
                        return result
                
                return {
                    'success': False,
                    'message': '图片格式需要GLM视觉模型服务才能识别',
                    'data': None
                }
            else:
                return {
                    'success': False,
                    'message': f'不支持的文件格式: {ext}，仅支持PDF、PNG、JPG、JPEG',
                    'data': None
                }
            
        except Exception as e:
            logger.error(f'解析文件失败: {str(e)}', exc_info=True)
            return {
                'success': False,
                'message': f'解析失败: {str(e)}',
                'data': None
            }
    
    def _extract_pdf_text(self, pdf_bytes: bytes) -> str:
        try:
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            total_pages = len(pdf_document)
            logger.info(f'PDF打开成功，共{total_pages}页')
            
            all_text = []
            for page_num in range(total_pages):
                page = pdf_document[page_num]
                text = page.get_text("text")
                
                if text and text.strip():
                    all_text.append(text.strip())
                    logger.debug(f'第{page_num + 1}页提取文本长度: {len(text)}')
                else:
                    logger.warning(f'第{page_num + 1}页未能提取到文本，可能为扫描版PDF')
            
            pdf_document.close()
            
            full_text = '\n\n'.join(all_text)
            logger.info(f'PDF文本提取完成，总长度: {len(full_text)} 字符')
            return full_text
            
        except Exception as e:
            logger.error(f'PDF文本提取失败: {str(e)}', exc_info=True)
            raise
    
    def _preprocess_text(self, text: str) -> str:
        lines = text.split('\n')
        processed_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            if not stripped:
                continue
            
            should_merge = (
                len(stripped) <= 3 
                and not stripped.replace('*', '').replace('¥', '').replace('%', '').replace('.', '').isdigit()
                and not any(c in stripped for c in ['¥', '%', '*', '.', '圆', '整'])
            )
            
            if should_merge:
                processed_lines.append(stripped + ' ')
            else:
                processed_lines.append(stripped)
        
        result = ''.join(processed_lines)
        result = re.sub(r'[ \t]+', ' ', result)
        result = re.sub(r'\n\s*\n+', '\n', result)
        
        return result
    
    def _extract_invoice_data(self, text: str) -> Dict[str, Any]:
        data = {
            'invoice_number': '',
            'invoice_date': '',
            'amount': 0.0,
            'tax_amount': 0.0,
            'total_amount': 0.0,
            'project_name': '',
            'remarks': ''
        }
        
        logger.debug(f'原始文本(前500字符): {text[:500]}')
        
        cleaned_text = self._preprocess_text(text)
        logger.debug(f'清洗后的文本(前500字符): {cleaned_text[:500]}')
        
        patterns = {
            'invoice_number': [
                r'发票号码[：:\s]*[\n\r]*([0-9]{8,20})',
                r'号码[：:\s]*[\n\r]*([0-9]{8,20})',
                r'(?:^|\n)([0-9]{10,20})[\n\r]*(?=\d{4}年|开票日期)',
                r'([0-9]{8,20})'
            ],
            'invoice_date': [
                r'开票日期[：:\s]*[\n\r]*(\d{4}年\d{1,2}月\d{1,2}日)',
                r'开票日期[：:\s]*[\n\r]*(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
                r'日期[：:\s]*[\n\r]*(\d{4}年\d{1,2}月\d{1,2}日)',
                r'(\d{4}年\d{1,2}月\d{1,2}日)'
            ],
            'amount': [
                r'(?:合计)?金额[（(]不含税[)）][：:\s]*[\n\r]*￥?\s*([\d,]+\.?\d*)',
                r'不含税金额[：:\s]*[\n\r]*￥?\s*([\d,]+\.?\d*)',
                r'金额[：:\s]*[\n\r]*￥?\s*([\d,]+\.?\d*)',
                r'¥[\s\n\r]*([\d,]+\.\d{2})[\s\n\r]+\d+%',
                r'¥([\d,]+\.\d{2})(?:\s|$)'
            ],
            'tax_amount': [
                r'税额[：:\s]*[\n\r]*￥?\s*([\d,]+\.?\d*)',
                r'增值税额[：:\s]*[\n\r]*￥?\s*([\d,]+\.?\d*)',
                r'[\s\n\r]([\d,]+\.\d{2})[\s\n\r]*(?:贰|壹|叁|肆|伍|陆|柒|捌|玖|拾|佰)'
            ],
            'total_amount': [
                r'[（(]小写[)）][\s\n\r:：]*¥?([\d,]+\.\d{2})',
                r'[（(]小写[)）][\s\n\r:：]*[￥¥]?([\d,]+\.\d+)',
                r'价税合计[（(]大写[)）][：:\s]*[\n\r]*[￥¥]?\s*([\d,]+\.?\d*)',
                r'价税合计[：:\s]*[\n\r]*￥?\s*([\d,]+\.?\d*)',
                r'[圆角分整][\s\n\r]*¥?([\d,]+\.\d{2})',
                r'^¥([\d,]+\.\d{2})$'
            ],
            'project_name': [
                r'\*([^\n\r*]{2,50})\*',
                r'货物或应税劳务[、,]?服务名称[：:\s]*[\n\r]*([^\n\r\s]{2,50})',
                r'服务名称[：:\s]*[\n\r]*([^\n\r\s]{2,50})',
                r'商品名称[：:\s]*[\n\r]*([^\n\r\s]{2,50})'
            ]
        }
        
        for field, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, cleaned_text, re.IGNORECASE | re.MULTILINE)
                if match:
                    value = match.group(1).strip()
                    value = re.sub(r'[\n\r\s]+', '', value)
                    
                    if field in ['amount', 'tax_amount', 'total_amount']:
                        parsed_value = self._parse_amount(value)
                        if parsed_value > 0:
                            data[field] = parsed_value
                            logger.info(f'✅ 成功提取 {field}: {parsed_value}')
                            break
                    elif field == 'invoice_date':
                        parsed_date = self._parse_date(value)
                        if parsed_date:
                            data[field] = parsed_date
                            logger.info(f'✅ 成功提取 {field}: {parsed_date}')
                            break
                    else:
                        if value and len(value) >= 2:
                            data[field] = value
                            logger.info(f'✅ 成功提取 {field}: {value}')
                            break
        
        if data['total_amount'] == 0 and data['amount'] > 0:
            data['total_amount'] = data['amount']
            logger.info(f'使用金额作为价税合计: {data["amount"]}')
        
        extraction_quality = self._assess_extraction_quality(data)
        logger.info(f'数据提取质量评估: {extraction_quality}')
        
        return data
    
    def _assess_extraction_quality(self, data: Dict[str, Any]) -> str:
        required_fields = ['invoice_number', 'invoice_date', 'total_amount']
        extracted_count = sum(1 for field in required_fields if data.get(field))
        
        if extracted_count == 3:
            return 'excellent'
        elif extracted_count >= 2:
            return 'good'
        elif extracted_count >= 1:
            return 'partial'
        else:
            return 'poor'
    
    def _parse_amount(self, amount_str: str) -> float:
        try:
            cleaned = amount_str.replace(',', '').replace('￥', '').replace('¥', '').replace(' ', '')
            cleaned = re.sub(r'[^\d.]', '', cleaned)
            value = float(cleaned) if cleaned else 0
            return round(value, 2)
        except:
            return 0.0
    
    def _parse_date(self, date_str: str) -> str:
        try:
            normalized = date_str.replace('年', '-').replace('月', '-').replace('日', '')
            normalized = normalized.replace('/', '-')
            
            parts = re.findall(r'\d+', normalized)
            if len(parts) >= 3:
                year = parts[0]
                month = parts[1].zfill(2)
                day = parts[2].zfill(2)
                
                if 2000 <= int(year) <= 2030 and 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
                    return f'{year}-{month}-{day}'
            
            return ''
        except:
            return ''

invoice_parser = InvoiceParser()