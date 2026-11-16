"""AI 视觉配置回归测试：双服务商预设、旧智谱配置迁移。"""
import pytest

from models import SystemConfig, db
from utils import ai_config
from utils.ai_config import (
    AI_PROVIDER_PRESETS,
    available_providers,
    infer_provider,
    migrate_legacy_ai_config,
    resolve_ai_api_key,
    resolve_ai_api_url,
    resolve_ai_model,
    resolve_ai_provider,
)


def _set(key, value, encrypted=False):
    from utils.crypto_utils import encrypt_value

    row = SystemConfig.query.filter_by(config_key=key).first()
    stored = encrypt_value(value) if encrypted else value
    if row:
        row.config_value = stored
        row.is_encrypted = encrypted
    else:
        db.session.add(SystemConfig(
            config_key=key, config_value=stored, is_encrypted=encrypted, description='',
        ))
    db.session.commit()


def _get(key):
    return SystemConfig.query.filter_by(config_key=key).first()


@pytest.fixture(autouse=True)
def _clear_ai_env(monkeypatch):
    for name in ('AI_PROVIDER', 'AI_MODEL', 'AI_API_URL',
                 'DEEPSEEK_API_KEY', 'SILICONFLOW_API_KEY',
                 'SILICONFLOW_APIKEY', 'GLM_API_KEY', 'ZHIPU_API_KEY'):
        monkeypatch.delenv(name, raising=False)


def test_presets_only_contain_deepseek_and_siliconflow():
    assert set(AI_PROVIDER_PRESETS) == {'deepseek', 'siliconflow'}
    names = {item['value'] for item in available_providers()}
    assert names == {'deepseek', 'siliconflow'}
    assert AI_PROVIDER_PRESETS['deepseek']['default_model'] == 'deepseek-flash'
    assert AI_PROVIDER_PRESETS['siliconflow']['default_model'] == 'zai-org/GLM-5.3-Flash'


def test_infer_provider_ignores_retired_glm_endpoint():
    assert infer_provider('https://api.deepseek.com/chat/completions', 'deepseek-flash') == 'deepseek'
    assert infer_provider('https://api.siliconflow.cn/v1/chat/completions', '') == 'siliconflow'
    assert infer_provider('', 'zai-org/GLM-5.3-Flash') == 'siliconflow'
    # 已下线的智谱地址 / 模型不再映射到任何服务商
    assert infer_provider('https://open.bigmodel.cn/api/paas/v4/chat/completions', '') == 'deepseek'
    assert infer_provider('', 'GLM-4-Flash-250414') == 'deepseek'


def test_resolvers_ignore_leftover_glm_values(app):
    _set('ai_provider', 'glm')
    _set('ai_model', 'GLM-4-Flash-250414')
    _set('ai_api_url', 'https://open.bigmodel.cn/api/paas/v4/chat/completions')

    assert resolve_ai_provider() == 'deepseek'
    assert resolve_ai_model() == 'deepseek-flash'
    assert resolve_ai_api_url() == 'https://api.deepseek.com/chat/completions'


def test_migrate_legacy_glm_config(app):
    _set('ai_model', 'GLM-4-Flash-250414')
    _set('ai_api_url', 'https://open.bigmodel.cn/api/paas/v4/chat/completions')
    _set('ai_api_key', '0123456789abcdef.zyxwvutsrqponmlk', encrypted=True)
    _set('ai_api_key_glm', '0123456789abcdef.zyxwvutsrqponmlk', encrypted=True)

    migrate_legacy_ai_config()
    db.session.expire_all()

    assert _get('ai_provider').config_value == 'deepseek'
    assert _get('ai_model').config_value == 'deepseek-flash'
    assert _get('ai_api_url').config_value == 'https://api.deepseek.com/chat/completions'
    # 智谱专用 Key 行被删除，通用 Key 被清空
    assert _get('ai_api_key_glm') is None
    assert not (_get('ai_api_key').config_value or '')
    assert resolve_ai_api_key() is None

    # 幂等：再跑一次不会改动已迁移的配置
    migrate_legacy_ai_config()
    db.session.expire_all()
    assert _get('ai_provider').config_value == 'deepseek'
    assert _get('ai_model').config_value == 'deepseek-flash'


def test_migrate_keeps_existing_sk_key(app):
    _set('ai_model', 'GLM-4V-Flash')
    _set('ai_api_url', 'https://open.bigmodel.cn/api/paas/v4/chat/completions')
    _set('ai_api_key', 'sk-existing-deepseek-key', encrypted=True)

    migrate_legacy_ai_config()
    db.session.expire_all()

    assert resolve_ai_api_key() == 'sk-existing-deepseek-key'


def test_migrate_preserves_siliconflow_config(app):
    _set('ai_provider', 'siliconflow')
    _set('ai_model', 'zai-org/GLM-5.3-Flash')
    _set('ai_api_url', 'https://api.siliconflow.cn/v1/chat/completions')

    migrate_legacy_ai_config()
    db.session.expire_all()

    assert _get('ai_provider').config_value == 'siliconflow'
    assert _get('ai_model').config_value == 'zai-org/GLM-5.3-Flash'
    assert resolve_ai_provider() == 'siliconflow'
    assert resolve_ai_model() == 'zai-org/GLM-5.3-Flash'
    assert resolve_ai_api_url() == 'https://api.siliconflow.cn/v1/chat/completions'
