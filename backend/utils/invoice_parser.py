import os
import io
import re
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

try:
    import fitz
    PDF_AVAILABLE = True
    logger.info('PyMuPDF库加载成功，支持PDF直接文本提取')
except ImportError:
    PDF_AVAILABLE = False
    logger.warning('PyMuPDF库未安装，PDF解析功能将不可用')

try:
    from PIL import Image
    import cv2
    import numpy as np
    from cnocr import CnOcr
    OCR_AVAILABLE = True
    logger.info('OCR库加载成功，支持图片格式识别')
except ImportError:
    OCR_AVAILABLE = False
    logger.warning('OCR库未安装，图片格式识别将不可用')

class InvoiceParser:
    def __init__(self):
        self.ocr = None
        if OCR_AVAILABLE:
            try:
                self.ocr = CnOcr()
                logger.info('OCR引擎初始化成功')
            except Exception as e:
                logger.error(f'OCR引擎初始化失败: {str(e)}')
    
    def is_available(self) -> bool:
        return PDF_AVAILABLE or (self.ocr is not None)
    
    def parse_file(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        解析发票文件（优先使用PDF直接提取，图片格式使用OCR）
        
        Args:
            file_bytes: 文件字节数据
            filename: 文件名
            
        Returns:
            dict: 解析结果
        """
        if not self.is_available():
            return {
                'success': False,
                'message': '解析服务不可用，请安装PyMuPDF或cnocr库',
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
            elif ext in ['.png', '.jpg', '.jpeg']:
                if not OCR_AVAILABLE or not self.ocr:
                    return {
                        'success': False,
                        'message': '图片格式需要安装cnocr库才能识别',
                        'data': None
                    }
                text = self._parse_image_with_ocr(file_bytes)
            else:
                return {
                    'success': False,
                    'message': f'不支持的文件格式: {ext}，仅支持PDF、PNG、JPG、JPEG',
                    'data': None
                }
            
            if not text or len(text.strip()) < 10:
                return {
                    'success': False,
                    'message': '未能从文件中提取到有效的文字内容，可能是扫描件或图片格式不正确',
                    'data': None
                }
            
            logger.info(f'文本提取完成，长度: {len(text)} 字符')
            logger.debug(f'提取的文本内容(前500字符): {text[:500]}')
            
            invoice_data = self._extract_invoice_data(text)
            
            return {
                'success': True,
                'message': '解析成功',
                'data': invoice_data,
                'raw_text': text,
                'extraction_method': 'pdf_direct' if ext == '.pdf' else 'ocr',
                'field_permissions': {
                    'readonly': ['invoice_number', 'invoice_date', 'total_amount'],
                    'editable': ['project_name', 'invoice_type']
                }
            }
            
        except Exception as e:
            logger.error(f'解析文件失败: {str(e)}', exc_info=True)
            return {
                'success': False,
                'message': f'解析失败: {str(e)}',
                'data': None
            }
    
    def _extract_pdf_text(self, pdf_bytes: bytes) -> str:
        """直接从PDF中提取文本（无需OCR）"""
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
                    
                    if OCR_AVAILABLE and self.ocr:
                        mat = fitz.Matrix(2.0, 2.0)
                        pix = page.get_pixmap(matrix=mat)
                        img_data = pix.tobytes("png")
                        image = Image.open(io.BytesIO(img_data))
                        ocr_text = self._ocr_image(image)
                        if ocr_text:
                            all_text.append(ocr_text)
                            logger.info(f'第{page_num + 1}页通过OCR补充识别成功')
            
            pdf_document.close()
            
            full_text = '\n\n'.join(all_text)
            logger.info(f'PDF文本提取完成，总长度: {len(full_text)} 字符')
            return full_text
            
        except Exception as e:
            logger.error(f'PDF文本提取失败: {str(e)}', exc_info=True)
            raise
    
    def _parse_image_with_ocr(self, image_bytes: bytes) -> str:
        """使用OCR识别图片中的文字"""
        try:
            image = Image.open(io.BytesIO(image_bytes))
            return self._ocr_image(image)
        except Exception as e:
            logger.error(f'图片OCR识别失败: {str(e)}', exc_info=True)
            raise
    
    def _ocr_image(self, image: Image.Image) -> str:
        """对图片进行OCR识别"""
        try:
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            img_array = np.array(image)
            
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            result = self.ocr.ocr(binary)
            
            if result is None or len(result) == 0:
                return ''
            
            text_lines = []
            for line in result:
                if isinstance(line, dict) and 'text' in line:
                    text_lines.append(line['text'])
                elif isinstance(line, (list, tuple)) and len(line) > 0:
                    if isinstance(line[0], dict) and 'text' in line[0]:
                        text_lines.append(line[0]['text'])
                    elif isinstance(line[0], (list, tuple)) and len(line[0]) > 1:
                        text_lines.append(str(line[0][1]))
            
            return '\n'.join(text_lines)
            
        except Exception as e:
            logger.error(f'OCR识别失败: {str(e)}', exc_info=True)
            return ''
    
    def _preprocess_text(self, text: str) -> str:
        """
        预处理PDF提取的文本，处理换行和空格问题
        
        针对电子发票PDF表格格式进行优化：
        - 合并分散的单个汉字（如"购\n买\n方" → "购买方"）
        - 保留 ¥ 符号和数字的关联性
        - 清理多余空白字符
        """
        lines = text.split('\n')
        processed_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            if not stripped:
                continue
            
            # 判断是否为需要合并的短行（单个汉字或标点）
            # 但保留：数字、¥符号、%、*号等特殊标记
            should_merge = (
                len(stripped) <= 3 
                and not stripped.replace('*', '').replace('¥', '').replace('%', '').replace('.', '').isdigit()
                and not any(c in stripped for c in ['¥', '%', '*', '.', '圆', '整'])
            )
            
            if should_merge:
                processed_lines.append(stripped + ' ')  # 短行后面加空格准备连接
            else:
                processed_lines.append(stripped)     # 有意义的内容保持原样
        
        result = ''.join(processed_lines)
        
        # 规范化空白字符
        result = re.sub(r'[ \t]+', ' ', result)
        result = re.sub(r'\n\s*\n+', '\n', result)  # 多个换行合并为一个
        
        return result
    
    def _extract_invoice_data(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取发票数据
        
        针对真实PDF发票格式优化：
        - 支持字段名和值分散在不同行的情况
        - 支持 ¥ 符号与金额分离的情况
        - 支持表格型布局的数据提取
        """
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
        
        # 定义增强的正则表达式模式（针对PDF表格格式）
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
                r'¥[\s\n\r]*([\d,]+\.\d{2})[\s\n\r]+\d+%',  # ¥金额 后跟税率%
                r'¥([\d,]+\.\d{2})(?:\s|$)'              # 行尾的¥金额
            ],
            'tax_amount': [
                r'税额[：:\s]*[\n\r]*￥?\s*([\d,]+\.?\d*)',
                r'增值税额[：:\s]*[\n\r]*￥?\s*([\d,]+\.?\d*)',
                r'[\s\n\r]([\d,]+\.\d{2})[\s\n\r]*(?:贰|壹|叁|肆|伍|陆|柒|捌|玖|拾|佰)'  # 数字后跟大写汉字
            ],
            'total_amount': [
                r'[（(]小写[)）][\s\n\r:：]*¥?([\d,]+\.\d{2})',      # （小写）后面的数字 ⭐最准确
                r'[（(]小写[)）][\s\n\r:：]*[￥¥]?([\d,]+\.\d+)',   # 备用
                r'价税合计[（(]大写[)）][：:\s]*[\n\r]*[￥¥]?\s*([\d,]+\.?\d*)',
                r'价税合计[：:\s]*[\n\r]*￥?\s*([\d,]+\.?\d*)',
                r'[圆角分整][\s\n\r]*¥?([\d,]+\.\d{2})',           # 大写金额后的数字
                r'^¥([\d,]+\.\d{2})$'                              # 独立行的¥金额
            ],
            'project_name': [
                r'\*([^\n\r*]{2,50})\*',        # ⭐ 优先匹配 *项目名* 格式（带捕获组）
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
        
        # 智能回退机制
        if data['total_amount'] == 0 and data['amount'] > 0:
            data['total_amount'] = data['amount']
            logger.info(f'使用金额作为价税合计: {data["amount"]}')
        
        extraction_quality = self._assess_extraction_quality(data)
        logger.info(f'数据提取质量评估: {extraction_quality}')
        
        return data
    
    def _assess_extraction_quality(self, data: Dict[str, Any]) -> str:
        """评估数据提取质量"""
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
        """解析金额字符串"""
        try:
            cleaned = amount_str.replace(',', '').replace('￥', '').replace('¥', '').replace(' ', '')
            cleaned = re.sub(r'[^\d.]', '', cleaned)
            value = float(cleaned) if cleaned else 0
            return round(value, 2)
        except:
            return 0.0
    
    def _parse_date(self, date_str: str) -> str:
        """解析日期字符串，返回YYYY-MM-DD格式"""
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
