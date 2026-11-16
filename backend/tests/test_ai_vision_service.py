"""AI 视觉服务协议测试：请求地址、模型名与图片 data URL 组装。"""
import pytest

from models import SystemConfig, db

pytest.importorskip('requests')

import utils.ai_vision_service as avs
from utils.ai_config import resolve_ai_api_key, resolve_ai_model

PNG_BYTES = b'\x89PNG\r\n\x1a\n' + b'\x00' * 32

_MODEL_REPLY = (
    '{"invoice_number":"12345678","invoice_date":"2026-01-02","total_amount":88.5,'
    '"project_name":"办公用品","invoice_type":"办公","invoice_tax_number":"91110000123456789X"}'
)


class _FakeResponse:
    status_code = 200
    text = ''

    @staticmethod
    def json():
        return {'choices': [{'message': {'content': _MODEL_REPLY}}]}


def _set(key, value, encrypted=False):
    from utils.crypto_utils import encrypt_value

    stored = encrypt_value(value) if encrypted else value
    row = SystemConfig.query.filter_by(config_key=key).first()
    if row:
        row.config_value = stored
        row.is_encrypted = encrypted
    else:
        db.session.add(SystemConfig(
            config_key=key, config_value=stored, is_encrypted=encrypted, description='',
        ))
    db.session.commit()


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for name in ('AI_PROVIDER', 'AI_MODEL', 'AI_API_URL',
                 'DEEPSEEK_API_KEY', 'SILICONFLOW_API_KEY', 'SILICONFLOW_APIKEY'):
        monkeypatch.delenv(name, raising=False)


def _capture(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured['url'] = url
        captured['headers'] = headers
        captured['payload'] = json
        captured['timeout'] = timeout
        return _FakeResponse()

    monkeypatch.setattr(avs.requests_lib, 'post', fake_post)
    return captured


def test_deepseek_is_the_default_provider(app, monkeypatch):
    _set('ai_api_key', 'sk-deepseek-test', encrypted=True)
    captured = _capture(monkeypatch)

    result = avs.AIVisionService().extract_invoice_info(PNG_BYTES, 'invoice.png')

    assert result['success'] is True
    assert result['extraction_method'] == 'ai_vision'
    assert resolve_ai_model() == 'deepseek-flash'
    assert captured['url'] == 'https://api.deepseek.com/chat/completions'
    assert captured['payload']['model'] == 'deepseek-flash'
    assert captured['headers']['Authorization'] == 'Bearer sk-deepseek-test'

    content = captured['payload']['messages'][0]['content']
    assert content[0]['type'] == 'image_url'
    assert content[0]['image_url']['url'].startswith('data:image/png;base64,')
    assert content[1]['type'] == 'text' and '发票' in content[1]['text']
    assert captured['payload']['max_tokens'] >= 1024


def test_siliconflow_uses_its_own_endpoint_and_key(app, monkeypatch):
    _set('ai_provider', 'siliconflow')
    _set('ai_model', 'zai-org/GLM-5.3-Flash')
    _set('ai_api_url', 'https://api.siliconflow.cn/v1/chat/completions')
    _set('ai_api_key_siliconflow', 'sk-siliconflow-test', encrypted=True)
    captured = _capture(monkeypatch)

    result = avs.AIVisionService().extract_invoice_info(PNG_BYTES, 'invoice.png')

    assert result['success'] is True
    assert resolve_ai_api_key() == 'sk-siliconflow-test'
    assert captured['url'] == 'https://api.siliconflow.cn/v1/chat/completions'
    assert captured['payload']['model'] == 'zai-org/GLM-5.3-Flash'
    assert captured['headers']['Authorization'] == 'Bearer sk-siliconflow-test'


def test_pdf_bytes_are_rejected_before_request(app, monkeypatch):
    _set('ai_api_key', 'sk-deepseek-test', encrypted=True)
    captured = _capture(monkeypatch)

    result = avs.AIVisionService().extract_invoice_info(b'%PDF-1.4 fake', 'invoice.pdf')

    assert result['success'] is False
    assert 'PDF' in result['message']
    assert captured == {}
