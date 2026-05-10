import os
import base64
import re
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

try:
    import requests as requests_lib
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning('requests库未安装，GLM视觉模型功能将不可用')


def _get_db_config_value(key: str) -> str | None:
    """Read a config value from the database (SystemConfig table)."""
    try:
        from models import SystemConfig
        from utils.crypto_utils import decrypt_value
        record = SystemConfig.query.filter_by(config_key=key).first()
        if record and record.config_value:
            if record.is_encrypted:
                return decrypt_value(record.config_value)
            return record.config_value
        return None
    except Exception as e:
        logger.debug(f'Failed to read config from DB: {e}')
        return None


def resolve_ai_model() -> str:
    """Resolve AI model name. DB config takes priority over env vars."""
    return _get_db_config_value('ai_model') or os.environ.get('GLM_MODEL', 'GLM-4V-Flash')


def resolve_ai_api_key() -> str | None:
    """Resolve AI API key. DB config takes priority over env vars."""
    return _get_db_config_value('ai_api_key') or os.environ.get('GLM_API_KEY')


def resolve_ai_api_url() -> str:
    """Resolve AI API URL. DB config takes priority over env vars."""
    return _get_db_config_value('ai_api_url') or os.environ.get('GLM_API_URL', 'https://open.bigmodel.cn/api/paas/v4/chat/completions')


class GLMVisionService:
    def __init__(self, api_key: str = None):
        self.api_key = api_key

    def _resolve_api_key(self) -> str | None:
        """Resolve API key: explicit > DB config > env var."""
        return self.api_key or resolve_ai_api_key()

    def is_available(self) -> bool:
        return REQUESTS_AVAILABLE and bool(self._resolve_api_key())

    @staticmethod
    def _detect_mime_type(image_bytes: bytes, filename: str = '') -> str:
        """从文件头魔数或文件名推断MIME类型"""
        if image_bytes[:3] == b'\xff\xd8\xff':
            return 'image/jpeg'
        if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
            return 'image/png'
        if image_bytes[:4] == b'GIF8':
            return 'image/gif'
        if image_bytes[:2] == b'BM':
            return 'image/bmp'
        if image_bytes[:4] == b'%PDF':
            return 'application/pdf'
        lower = filename.lower()
        if lower.endswith('.png'):
            return 'image/png'
        if lower.endswith(('.jpg', '.jpeg')):
            return 'image/jpeg'
        if lower.endswith('.gif'):
            return 'image/gif'
        if lower.endswith('.bmp'):
            return 'image/bmp'
        if lower.endswith('.pdf'):
            return 'application/pdf'
        return 'image/jpeg'

    def extract_invoice_info(self, image_bytes: bytes, filename: str = '') -> Dict[str, Any]:
        """Use the GLM vision model to extract invoice info from an image."""
        if not self.is_available():
            return {
                'success': False,
                'message': 'GLM视觉模型服务不可用',
                'data': None
            }

        api_key = self._resolve_api_key()
        api_url = resolve_ai_api_url()
        model = resolve_ai_model()

        try:
            mime_type = self._detect_mime_type(image_bytes, filename)
            logger.info(f'检测到图片格式: {mime_type}, 文件: {filename}, 大小: {len(image_bytes)} bytes')

            if mime_type == 'application/pdf':
                return {
                    'success': False,
                    'message': 'GLM视觉模型不支持原始PDF，请先转换为图片',
                    'data': None
                }

            base64_image = base64.b64encode(image_bytes).decode('utf-8')

            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}"
                                }
                            },
                            {
                                "type": "text",
                                "text": self._build_prompt()
                            }
                        ]
                    }
                ],
                "max_tokens": 1024
            }

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            logger.info(f'发送请求到{model}视觉模型...')

            response = requests_lib.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f'GLM API请求失败: {response.status_code}, {response.text}')
                return {
                    'success': False,
                    'message': f'GLM API请求失败: HTTP {response.status_code}',
                    'data': None
                }

            result = response.json()

            if 'choices' not in result or len(result['choices']) == 0:
                logger.error(f'GLM API返回异常: {result}')
                return {
                    'success': False,
                    'message': 'GLM API返回数据异常',
                    'data': None
                }

            content = result['choices'][0].get('message', {}).get('content', '')
            logger.info(f'{model}返回内容: {content[:500]}')

            return self._parse_response(content, model)

        except json.JSONDecodeError as e:
            logger.error(f'GLM返回的JSON解析失败: {str(e)}')
            return {
                'success': False,
                'message': f'GLM返回数据格式错误: {str(e)}',
                'data': None
            }
        except requests_lib.exceptions.Timeout:
            logger.error('GLM API请求超时')
            return {
                'success': False,
                'message': 'GLM视觉模型响应超时，请稍后重试',
                'data': None
            }
        except Exception as e:
            logger.error(f'GLM视觉模型调用失败: {str(e)}', exc_info=True)
            return {
                'success': False,
                'message': f'GLM视觉模型调用失败: {str(e)}',
                'data': None
            }

    def _build_prompt(self) -> str:
        """构建发票信息提取的提示词"""
        return """你是一个专业的发票信息提取助手。请仔细识别这张发票图片，并提取以下关键信息：

1. **发票号码**（invoice_number）：发票上的唯一编号，通常是8-20位数字
2. **开票日期**（invoice_date）：发票开具日期，格式为YYYY-MM-DD
3. **价税合计/总金额**（total_amount）：发票的总金额，只返回数字
4. **商品名称**（project_name）：发票上的商品或服务名称（即货物或应税劳务、服务名称）
5. **发票类型**（invoice_type）：如餐饮、交通、住宿、办公用品等

请严格按照以下JSON格式返回结果，不要添加任何其他文字：
```json
{
  "invoice_number": "发票号码或空字符串",
  "invoice_date": "YYYY-MM-DD格式日期或空字符串",
  "total_amount": 数字金额或0,
  "project_name": "项目名称或空字符串",
  "invoice_type": "发票类型或空字符串"
}
```

注意：
- 如果某个字段无法识别，请返回空字符串或0
- 金额字段必须返回纯数字，不要包含¥符号或其他字符
- 日期必须是YYYY-MM-DD格式"""

    def _parse_response(self, content: str, model: str = '') -> Dict[str, Any]:
        """解析GLM模型的响应内容"""
        json_match = re.search(r'\{[^{}]+\}', content, re.DOTALL)

        if not json_match:
            logger.warning(f'无法从GLM响应中解析JSON: {content}')
            return {
                'success': False,
                'message': '无法解析GLM返回的数据格式',
                'data': None
            }

        try:
            extracted_data = json.loads(json_match.group())

            invoice_data = {
                'invoice_number': extracted_data.get('invoice_number', ''),
                'invoice_date': extracted_data.get('invoice_date', ''),
                'amount': float(extracted_data.get('total_amount', 0)),
                'total_amount': float(extracted_data.get('total_amount', 0)),
                'project_name': extracted_data.get('project_name', ''),
                'invoice_type': extracted_data.get('invoice_type', '')
            }

            logger.info(f'{model}提取成功: {invoice_data}')

            return {
                'success': True,
                'message': f'{model}解析成功',
                'data': invoice_data,
                'raw_text': content,
                'extraction_method': 'glm_vision',
                'field_permissions': {
                    'readonly': ['invoice_number', 'invoice_date', 'total_amount'],
                    'editable': ['project_name', 'invoice_type']
                }
            }

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f'解析提取数据失败: {str(e)}')
            return {
                'success': False,
                'message': f'解析提取数据失败: {str(e)}',
                'data': None
            }

    def chat_with_image(self, image_bytes: bytes, question: str, model: str = None) -> Dict[str, Any]:
        """Send an image and question to the GLM vision model."""
        if not self.is_available():
            return {
                'success': False,
                'message': 'GLM视觉模型服务不可用',
                'content': None
            }

        api_key = self._resolve_api_key()
        api_url = resolve_ai_api_url()
        resolved_model = model or resolve_ai_model()

        try:
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            mime_type = self._detect_mime_type(image_bytes)

            payload = {
                "model": resolved_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}"
                                }
                            },
                            {
                                "type": "text",
                                "text": question
                            }
                        ]
                    }
                ],
                "max_tokens": 2048
            }

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            logger.info(f'发送请求到{resolved_model}视觉模型...')

            response = requests_lib.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code != 200:
                return {
                    'success': False,
                    'message': f'API请求失败: HTTP {response.status_code}',
                    'content': None
                }

            result = response.json()

            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0].get('message', {}).get('content', '')
                return {
                    'success': True,
                    'message': '成功',
                    'content': content
                }

            return {
                'success': False,
                'message': 'API返回数据异常',
                'content': None
            }

        except Exception as e:
            logger.error(f'GLM视觉模型调用失败: {str(e)}', exc_info=True)
            return {
                'success': False,
                'message': f'调用失败: {str(e)}',
                'content': None
            }


glm_vision_service = GLMVisionService()
