"""PDF 转图片工具。

原先 PDFConverter 寄居在 routes/parse.py，导致 routes/purchase_records.py
必须跨层 import 路由模块。现下沉为独立工具，路由层之间不再有横向依赖。
"""

import logging

logger = logging.getLogger(__name__)


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
